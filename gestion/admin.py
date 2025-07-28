
from django.contrib import admin
from django.urls import reverse, path
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from django.template.loader import render_to_string
from io import BytesIO
from weasyprint import HTML
import datetime
from django.db import models
from django.utils.timezone import now
from django.shortcuts import redirect
from django.contrib import messages
from .models import PlanLivraisonPrincipal, EtapeLivraison



from .models import (
    Commande, Produit, Ingredient, ProduitIngredient,
    CommandeProduit, Client, Facture,
    CommandeModele, CommandeModeleProduit, PaiementClient, CompteClient, Jour, FactureCloturee,
    Fournisseur, FactureFournisseur, PaiementFournisseur, CompteFournisseur, FactureFournisseurCloturee,
    ClientAdminProxy, CompteClientAdminProxy, PaiementClientAdminProxy, FactureAdminProxy, FactureClotureeAdminProxy,
    FournisseurAdminProxy, CompteFournisseurAdminProxy, PaiementFournisseurAdminProxy, FactureFournisseurAdminProxy, FactureFournisseurClotureeAdminProxy,
    CommandeAdminProxy, CommandeModeleAdminProxy, CommandeProduitAdminProxy, CommandeModeleProduitAdminProxy,
    ProduitAdminProxy, IngredientAdminProxy
)

def generer_factures_pdf_fusionne(modeladmin, request, queryset):
    html_complet = ""

    for commande in queryset:
        facture = commande.facture or commande.update_facture()
        if not facture:
            continue

        html = render_to_string("facture_template.html", {
            "commande": commande,
            "facture": facture,
            "date_affichee": commande.date_livraison
        })
        html_complet += f"<div style='page-break-after: always'>{html}</div>"

    pdf_fusionne = HTML(string=html_complet).write_pdf()

    response = HttpResponse(pdf_fusionne, content_type="application/pdf")
    response["Content-Disposition"] = "attachment; filename=commandes_fusionnees.pdf"
    return response

class GestionAdminSite(admin.AdminSite):
    site_header = "Administration de Gestion"
    site_title = "Gestion"
    index_title = "Accueil de Gestion"

admin_site = GestionAdminSite(name='gestion_admin')

# =============================
# Filtres personnalisés
# =============================
class DateLivraisonJourFilter(admin.SimpleListFilter):
    title = _('Date de livraison rapide')
    parameter_name = 'date_livraison_exacte'

    def lookups(self, request, model_admin):
        return [
            ('today', _('Aujourd’hui')),
            ('yesterday', _('Hier')),
            ('tomorrow', _('Demain')),
        ]

    def queryset(self, request, queryset):
        today = datetime.date.today()
        if self.value() == 'today':
            return queryset.filter(date_livraison=today)
        elif self.value() == 'yesterday':
            return queryset.filter(date_livraison=today - datetime.timedelta(days=1))
        elif self.value() == 'tomorrow':
            return queryset.filter(date_livraison=today + datetime.timedelta(days=1))
        return queryset

# =============================
# Inlines réutilisables
# =============================
class CommandeProduitInline(admin.TabularInline):
    model = CommandeProduit
    extra = 1
    fields = ['produit', 'quantite', 'prix_unitaire']

class CommandeInline(admin.TabularInline):
    model = Commande
    extra = 0
    show_change_link = False  # inutile ici, on gère le lien manuellement

    readonly_fields = ['commande_link', 'date_livraison', 'total']
    fields = ['commande_link', 'date_livraison', 'total', 'statut', 'is_speciale']

    def commande_link(self, obj):
        if obj.pk:
            url = reverse("admin:gestion_commandeadminproxy_change", args=[obj.pk])
            return format_html('<a href="{}">Commande #{}</a>', url, obj.pk)
        return "-"
    commande_link.short_description = "Commande"


class PaiementInline(admin.TabularInline):
    model = PaiementClient
    extra = 1
    fields = ['date_paiement', 'montant', 'mode_paiement', 'commentaire']

class CommandeModeleProduitInline(admin.TabularInline):
    model = CommandeModeleProduit
    extra = 1
    fields = ['produit', 'quantite']

class PaiementFournisseurInline(admin.TabularInline):
    model = PaiementFournisseur
    fk_name = 'fournisseur'
    extra = 1
    fields = ['facture', 'montant', 'date_paiement', 'mode_paiement']

    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('facture__fournisseur')

    def has_change_permission(self, request, obj=None):
        return False

    def has_add_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

class FactureFournisseurInline(admin.TabularInline):
    model = FactureFournisseur
    extra = 1
    fields = ['date_facture', 'montant_total', 'description', 'statut']

# =============================
# SECTION CLIENTS : CompteClientAdminProxy
# =============================
@admin.register(CompteClientAdminProxy, site=admin_site)
class CompteClientAdmin(admin.ModelAdmin):
    list_display = ('nom', 'email', 'telephone', 'solde', 'frequence_paiement', 'export_link', 'cloturer_link')
    search_fields = ('nom', 'email')
    list_filter = ('frequence_paiement',)
    inlines = [CommandeInline, PaiementInline]

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:client_id>/export/', self.admin_site.admin_view(self.export_releve), name='compteclient_export'),
            path('resumes/', self.admin_site.admin_view(self.export_resume_clients), name='compteclient_resume'),
            path('<int:client_id>/cloturer/', self.admin_site.admin_view(self.cloturer_compte), name='gestion_compteclient_cloturer'),
        ]
        return custom_urls + urls

    def export_link(self, obj):
        url = reverse('admin:compteclient_export', args=[obj.pk])
        return format_html('<a class="button" href="{}">📄 Exporter relevé</a>', url)
    export_link.short_description = "Relevé PDF"

    def cloturer_link(self, obj):
        url = reverse('admin:gestion_compteclient_cloturer', args=[obj.pk])
        return format_html('<a class="button" href="{}">🧾 Clôturer le compte</a>', url)
    cloturer_link.short_description = "Clôturer"

    def export_releve(self, request, client_id):
        client = CompteClient.objects.get(pk=client_id)
        commandes = client.commandes.all()
        paiements = client.paiements.all()
        total_commandes = sum(c.total for c in commandes)
        total_paye = sum(p.montant for p in paiements)
        reste = total_commandes - total_paye

        # ✅ On ajoute ici
        lignes_produits = client.get_lignes_regroupees()

        html = render_to_string("releve_client.html", {
            'client': client,
            'commandes': commandes,
            'paiements': paiements,
            'total_commandes': total_commandes,
            'total_paye': total_paye,
            'reste': reste,
            'lignes_produits': lignes_produits,
            'date_generation': datetime.date.today()
        })

        pdf = HTML(string=html).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=releve_{client.nom}.pdf'
        return response


    def export_resume_clients(self, request):
        positifs = CompteClient.objects.filter(solde__gt=0)
        negatifs = CompteClient.objects.filter(solde__lt=0)

        html = render_to_string("resumes_comptes.html", {
            'positifs': positifs,
            'negatifs': negatifs,
            'date_generation': datetime.date.today()
        })
        pdf = HTML(string=html).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=resume_comptes_{datetime.date.today()}.pdf'
        return response

    def changelist_view(self, request, extra_context=None):
        if not extra_context:
            extra_context = {}
        url = reverse("admin:compteclient_resume")
        extra_context['additional_button'] = format_html(
            '<a class="button" style="margin:1em;" href="{}">📊 Résumé général</a>', url
        )
        return super().changelist_view(request, extra_context=extra_context)

    def cloturer_compte(self, request, client_id):
        client = CompteClient.objects.get(pk=client_id)

        if client.solde != 0:
            messages.error(request, "Le solde du client doit être à zéro pour clôturer.")
            return redirect(f'../../{client_id}/change/')

        commandes = client.commandes.all()
        paiements_qs = client.paiements.all()

        total_commandes = sum(c.total for c in commandes)
        total_paiements = sum(p.montant for p in paiements_qs)

        produits = []
        for commande in commandes:
            for cp in commande.commande_produits.all():
                produits.append({
                    'commande_id': commande.id,
                    'produit': cp.produit.nom,
                    'quantite': cp.quantite,
                    'prix_unitaire': float(cp.produit.prix),
                    'total_ligne': float(cp.quantite * cp.produit.prix),
                    'date_livraison': commande.date_livraison.isoformat()
                })

        paiements_archives = [{
            'montant': float(p.montant),
            'date': p.date_paiement.isoformat(),
            'mode': p.mode_paiement
        } for p in paiements_qs]

        FactureCloturee.objects.create(
            client=client,
            montant_total_commandes=total_commandes,
            montant_total_paye=total_paiements,
            produits_json=produits,
            paiements_json=paiements_archives,
            commentaire="Facture générée automatiquement à la clôture du compte."
        )

        commandes.delete()
        paiements_qs.delete()
        client.solde = 0
        client.save(update_fields=['solde'])

        messages.success(request, "Le compte client a été clôturé et la facture enregistrée.")
        return redirect(f'../../{client_id}/change/')

@admin.register(CommandeAdminProxy, site=admin_site)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ['id', 'date_livraison', 'client','frequence_client', 'total', 'statut', 'is_speciale', 'generate_facture_button']
    actions = ['generer_resume_commandes', generer_factures_pdf_fusionne]
    inlines = [CommandeProduitInline]
    list_filter = [
        DateLivraisonJourFilter,
        'statut',
        'date_commande',
        'is_speciale',
    ]
    search_fields = ['client__nom', 'id']
    def frequence_client(self, obj):
        if obj.client:
            return obj.client.frequence_paiement
        return "-"
    frequence_client.short_description = "Fréquence"

    def generer_resume_commandes(self, request, queryset):
        if not queryset.exists():
            messages.warning(request, "Aucune commande sélectionnée.")
            return

        commandes = queryset.select_related('client').prefetch_related('commande_produits__produit')
        total_global = sum(c.total for c in commandes)

        html = render_to_string("commandes_resume.html", {
            'commandes': commandes,
            'total_global': total_global,
            'date_generation': datetime.date.today()
        })

        pdf = HTML(string=html).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=commandes_resume_selection.pdf'
        return response

    generer_resume_commandes.short_description = "📦 Générer résumé PDF des commandes sélectionnées"    



    def save_model(self, request, obj, form, change):
        obj.finaliser_commande()

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:commande_id>/generer-facture/', self.admin_site.admin_view(self.generer_facture_pdf), name='generer_facture_pdf'),
        ]
        return custom_urls + urls

    def generate_facture_button(self, obj):
        url = reverse('admin:generer_facture_pdf', args=[obj.pk])
        label = "📄 Générer / Re-générer Facture"
        return format_html('<a class="button" href="{}">{}</a>', url, label)

    def generer_facture_pdf(self, request, commande_id):
        commande = Commande.objects.get(pk=commande_id)
        facture = commande.update_facture()
        pdf_path = facture.generer_pdf()

        with open(pdf_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'attachment; filename="facture_{facture.id}.pdf"'

            return response

@admin.register(CommandeModeleAdminProxy, site=admin_site)
class CommandeModeleAdmin(admin.ModelAdmin):
    list_display = ['id', 'client', 'remarque', 'active']
    list_editable = ('active',)
    inlines = [CommandeModeleProduitInline]
    list_filter = ['active', 'client']
    search_fields = ['client__nom']

    def change_view(self, request, object_id, form_url='', extra_context=None):
        current = CommandeModele.objects.get(pk=object_id)
        previous = CommandeModele.objects.filter(pk__lt=object_id).order_by('-pk').first()
        next = CommandeModele.objects.filter(pk__gt=object_id).order_by('pk').first()

        links = []
        if previous:
            links.append(f'<a class="button" href="{reverse("admin:gestion_commandemodeleadminproxy_change", args=(previous.pk,))}">← Précédent</a>')
        links.append(f'<a class="button" href="{reverse("admin:gestion_commandemodeleadminproxy_changelist")}">Retour à la liste</a>')
        if next:
            links.append(f'<a class="button" href="{reverse("admin:gestion_commandemodeleadminproxy_change", args=(next.pk,))}">Suivant →</a>')

        extra_context = extra_context or {}
        extra_context['navigation_links'] = format_html(
            '<div style="display:flex; justify-content:center; gap: 1em; margin: 1em 0;">{}</div>',
            format_html(' '.join(links))
        )

        return super().change_view(request, object_id, form_url, extra_context=extra_context)


@admin.register(ProduitAdminProxy, site=admin_site)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prix']
    search_fields = ['nom']

@admin.register(IngredientAdminProxy, site=admin_site)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['nom', 'quantite_stock', 'unite', 'seuil_minimum']
    search_fields = ['nom']

@admin.register(FournisseurAdminProxy, site=admin_site)
class FournisseurAdmin(admin.ModelAdmin):
    list_display = ['nom', 'email', 'telephone', 'solde']
    search_fields = ['nom', 'email']
    inlines = [FactureFournisseurInline, PaiementFournisseurInline]

@admin.register(PaiementFournisseurAdminProxy, site=admin_site)
class PaiementFournisseurAdmin(admin.ModelAdmin):
    list_display = ['facture', 'montant', 'date_paiement', 'mode_paiement']
    list_filter = ['date_paiement', 'mode_paiement']
    search_fields = ['facture__fournisseur__nom']

@admin.register(FactureFournisseurAdminProxy, site=admin_site)
class FactureFournisseurAdmin(admin.ModelAdmin):
    list_display = ['id', 'fournisseur', 'date_facture', 'montant_total', 'statut']
    list_filter = ['statut', 'date_facture']
    search_fields = ['fournisseur__nom']

@admin.register(FactureClotureeAdminProxy, site=admin_site)
class FactureClotureeAdmin(admin.ModelAdmin):
    actions = ['exporter_selection_pdf']
    list_display = ['client', 'date_facture','numero', 'montant_total_commandes', 'montant_total_paye', 'export_pdf_button']
    search_fields = ['client__nom']
    list_filter = ['date_facture']
    
    fieldsets = (
        (None, {
            'fields': (
                'client',
                'date_facture',
                'numero',  # 🔹 On affiche ici
                'commentaire',
            )
        }),
        ("Détails", {
            'fields': (
            'montant_total_commandes',
            'montant_total_paye',
             )
        }),
    )


    #securiser le num de facture
    def get_readonly_fields(self, request, obj=None):
        base = ['client', 'date_facture', 'montant_total_commandes', 'montant_total_paye', 'commentaire']
        if obj and obj.numero:
            return base + ['numero']
        return base

    def export_pdf_button(self, obj):
        url = reverse('admin:facturecloturee_download', args=[obj.pk])
        return format_html('<a class="button" href="{}">📄 PDF</a>', url)
    export_pdf_button.short_description = "Télécharger"

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:facture_id>/download/', self.admin_site.admin_view(self.download_pdf), name='facturecloturee_download'),
            path('export-aujourdhui/', self.admin_site.admin_view(self.export_factures_aujourdhui), name='factures_cloturees_aujourdhui'),
        ]
        return custom_urls + urls

    def download_pdf(self, request, facture_id):
        facture = FactureCloturee.objects.get(pk=facture_id)
        pdf_path = facture.generer_pdf()
        with open(pdf_path, 'rb') as f:
            return HttpResponse(f.read(), content_type='application/pdf', headers={
                'Content-Disposition': f'attachment; filename="facture_cloturee_{facture.id}.pdf"'

            })

    def changelist_view(self, request, extra_context=None):
        extra_context = extra_context or {}
        url = reverse('admin:factures_cloturees_aujourdhui')
        extra_context['additional_button'] = format_html(
            '<a class="button" style="margin:1em;" href="{}">📅 Exporter celles d’aujourd’hui</a>', url
        )
        return super().changelist_view(request, extra_context=extra_context)

    def export_factures_aujourdhui(self, request):
        today = datetime.date.today()
        factures = FactureCloturee.objects.filter(date_facture__date=today)

        total_commandes = sum(f.montant_total_commandes for f in factures)
        total_paye = sum(f.montant_total_paye for f in factures)

        html = render_to_string("factures_cloturees_jour.html", {
            'factures': factures,
            'total_commandes': total_commandes,
            'total_paye': total_paye,
            'date': today,
        })

        pdf = HTML(string=html).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=factures_cloturees_{today}.pdf'
        return response



@admin.register(CompteFournisseurAdminProxy, site=admin_site)
class CompteFournisseurAdmin(admin.ModelAdmin):
    list_display = ('nom', 'email', 'telephone', 'solde', 'export_link', 'cloturer_link')
    search_fields = ('nom', 'email')

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:fournisseur_id>/cloturer/', self.admin_site.admin_view(self.cloturer_compte), name='gestion_comptefournisseur_cloturer'),
            path('<int:fournisseur_id>/export/', self.admin_site.admin_view(self.export_releve), name='comptefournisseur_export'),
        ]
        return custom_urls + urls

    def export_link(self, obj):
        url = reverse('admin:comptefournisseur_export', args=[obj.pk])
        return format_html('<a class="button" href="{}">📄 Relevé PDF</a>', url)
    export_link.short_description = "Relevé PDF"

    def cloturer_link(self, obj):
        url = reverse('admin:gestion_comptefournisseur_cloturer', args=[obj.pk])
        return format_html('<a class="button" href="{}">🧾 Clôturer</a>', url)
    cloturer_link.short_description = "Clôturer"

    def export_releve(self, request, fournisseur_id):
        fournisseur = Fournisseur.objects.get(pk=fournisseur_id)
        factures = fournisseur.factures.all()
        paiements = PaiementFournisseur.objects.filter(facture__fournisseur=fournisseur)
        total_factures = sum(f.montant_total for f in factures)
        total_paye = sum(p.montant for p in paiements)
        reste = total_factures - total_paye

        html = render_to_string("releve_fournisseur.html", {
            'fournisseur': fournisseur,
            'factures': factures,
            'paiements': paiements,
            'total_factures': total_factures,
            'total_paye': total_paye,
            'reste': reste,
            'date_generation': datetime.date.today()
        })
        pdf = HTML(string=html).write_pdf()
        response = HttpResponse(pdf, content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename=releve_fournisseur_{fournisseur.nom}.pdf'
        return response

    def cloturer_compte(self, request, fournisseur_id):
        fournisseur = Fournisseur.objects.get(pk=fournisseur_id)
        factures = fournisseur.factures.all()
        paiements_qs = PaiementFournisseur.objects.filter(facture__fournisseur=fournisseur)

        if fournisseur.solde != 0:
            messages.error(request, "Le solde doit être à zéro pour clôturer le compte fournisseur.")
            return redirect(f'../../{fournisseur_id}/change/')

        total_factures = sum(f.montant_total for f in factures)
        total_paiements = sum(p.montant for p in paiements_qs)

        factures_archives = [{
            'id': f.id,
            'date_facture': f.date_facture.isoformat(),
            'montant': float(f.montant_total),
            'description': f.description
        } for f in factures]

        paiements_archives = [{
            'montant': float(p.montant),
            'date': p.date_paiement.isoformat(),
            'mode': p.mode_paiement
        } for p in paiements_qs]

        FactureFournisseurCloturee.objects.create(
            fournisseur=fournisseur,
            montant_total_factures=total_factures,
            montant_total_paye=total_paiements,
            description="Clôture automatique du compte",
            factures_json=factures_archives,
            paiements_json=paiements_archives
        )

        factures.delete()
        paiements_qs.delete()
        fournisseur.solde = 0
        fournisseur.save(update_fields=['solde'])

        messages.success(request, "Le compte fournisseur a été clôturé.")
        return redirect(f'../../{fournisseur_id}/change/')

@admin.register(FactureFournisseurClotureeAdminProxy, site=admin_site)
class FactureFournisseurClotureeAdmin(admin.ModelAdmin):
    list_display = ['fournisseur', 'date_cloture', 'montant_total_factures', 'montant_total_paye', 'download_pdf_button']
    readonly_fields = ['fournisseur', 'date_cloture', 'montant_total_factures', 'montant_total_paye', 'description']
    search_fields = ['fournisseur__nom']
    list_filter = ['date_cloture']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:facture_id>/download/', self.admin_site.admin_view(self.download_pdf), name='facturefournisseurcloturee_download'),
        ]
        return custom_urls + urls

    def download_pdf_button(self, obj):
        url = reverse('admin:facturefournisseurcloturee_download', args=[obj.pk])
        return format_html('<a class="button" href="{}">📄 Télécharger PDF</a>', url)
    download_pdf_button.short_description = "PDF"

    def download_pdf(self, request, facture_id):
        facture = FactureFournisseurCloturee.objects.get(pk=facture_id)
        pdf_path = facture.generer_pdf()
        with open(pdf_path, 'rb') as f:
            return HttpResponse(f.read(), content_type='application/pdf', headers={
                'Content-Disposition': f'attachment; filename="facture_fournisseur_cloturee_{facture.id}.pdf"'

            })
        
@admin.register(FactureAdminProxy, site=admin_site)
class FactureAdmin(admin.ModelAdmin):
    list_display = ['id', 'commande', 'date_facture', 'montant_total']
    search_fields = ['commande__id', 'id']
    list_filter = ['date_facture']

@admin.register(PaiementClientAdminProxy, site=admin_site)
class PaiementClientAdmin(admin.ModelAdmin):
    list_display = ['client', 'montant', 'date_paiement', 'mode_paiement']
    list_filter = ['client', 'date_paiement', 'mode_paiement']
    search_fields = ['client__nom']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.client:
            obj.client.recalculer_solde()

@admin.register(ClientAdminProxy, site=admin_site)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('nom', 'livre_par_nous', 'solde', 'frequence_paiement', 'matricule_fiscale')
    list_editable = ('livre_par_nous',)
    search_fields = ('nom',)
    list_filter = ('frequence_paiement', 'livre_par_nous')

# @admin.register(ProduitIngredientAdmin, site=admin_site)
# class ProduitIngredientAdmin(admin.ModelAdmin):
#     list_display = ['produit', 'ingredient', 'quantite']
#     list_filter = ['produit', 'ingredient']
#     search_fields = ['produit__nom', 'ingredient__nom']

class EtapeLivraisonInline(admin.TabularInline):
    model = EtapeLivraison
    extra = 0
    fields = ['ordre', 'client', 'actif', 'groupe']
    readonly_fields = ['client']
    ordering = ['ordre']
    show_change_link = False
    can_delete = False

from .models import PlanLivraisonPrincipal

@admin.register(PlanLivraisonPrincipal, site=admin_site)
class PlanLivraisonPrincipalAdmin(admin.ModelAdmin):
    inlines = [EtapeLivraisonInline]
    list_display = ['nom']

