from django.contrib import admin
from django.urls import reverse, path
from django.utils.html import format_html
from django.utils.translation import gettext_lazy as _
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from .models import (
    Commande, Produit, Ingredient, ProduitIngredient,
    CommandeProduit, Client, Facture,
    CommandeModele, CommandeModeleProduit, PaiementClient, CompteClient, Jour, FactureCloturee
)
import datetime
from django.db import models
from django.utils.timezone import now
from django.shortcuts import redirect
from django.contrib import messages

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

class CommandeProduitInline(admin.TabularInline):
    model = CommandeProduit
    extra = 1
    fields = ['produit', 'quantite']

class CommandeInline(admin.TabularInline):
    model = Commande
    extra = 0
    fields = ['date_livraison', 'total', 'statut', 'is_speciale']
    readonly_fields = ['total']
    show_change_link = True

class PaiementInline(admin.TabularInline):
    model = PaiementClient
    extra = 1
    fields = ['date_paiement', 'montant', 'mode_paiement', 'commentaire']

@admin.register(CompteClient)
class CompteClientAdmin(admin.ModelAdmin):
    list_display = ('nom', 'email', 'telephone', 'solde', 'frequence_paiement', 'export_link')
    search_fields = ('nom', 'email')
    list_filter = ('frequence_paiement',)
    inlines = [CommandeInline, PaiementInline]

    def get_urls(self):
        from django.urls import path
        urls = super().get_urls()
        custom_urls = [
            path('<int:client_id>/export/', self.admin_site.admin_view(self.export_releve), name='compteclient_export'),
            path('resumes/', self.admin_site.admin_view(self.export_resume_clients), name='compteclient_resume'),
            path('<int:client_id>/cloturer/', self.admin_site.admin_view(self.cloturer_compte), name='gestion_compteclient_cloturer'),
        ]
        return custom_urls + urls

    def export_link(self, obj):
        url = reverse('admin:compteclient_export', args=[obj.pk])
        return format_html('<a class="button" href="{}">\U0001f4c4 Exporter relevé</a>', url)
    export_link.short_description = "Relevé PDF"

    def export_releve(self, request, client_id):
        client = CompteClient.objects.get(pk=client_id)
        commandes = client.commandes.all()
        paiements = client.paiements.all()
        total_commandes = sum(c.total for c in commandes)
        total_paye = sum(p.montant for p in paiements)
        reste = total_commandes - total_paye

        html = render_to_string("releve_client.html", {
            'client': client,
            'commandes': commandes,
            'paiements': paiements,
            'total_commandes': total_commandes,
            'total_paye': total_paye,
            'reste': reste,
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
            '<a class="button" style="margin:1em;" href="{}">\U0001f4ca Résumé général</a>', url
        )
        return super().changelist_view(request, extra_context=extra_context)
    
    def cloturer_link(self, obj):
        url = reverse('admin:gestion_compteclient_cloturer', args=[obj.pk])
        return format_html('<a class="button" href="{}">📄 Clôturer le compte</a>', url)
    cloturer_link.short_description = "Clôturer le compte"

    # Ajoute 'cloturer_link' dans list_display
    list_display = ('nom', 'email', 'telephone', 'solde', 'frequence_paiement', 'export_link', 'cloturer_link')

    def cloturer_compte(self, request, client_id):
        client = CompteClient.objects.get(pk=client_id)

        if client.solde != 0:
            messages.error(request, "Le solde du client doit être à zéro pour clôturer.")
            return redirect(f'../../{client_id}/change/')

        commandes = client.commandes.all()
        paiements_qs = client.paiements.all()

        total_commandes = sum(c.total for c in commandes)
        total_paiements = sum(p.montant for p in paiements_qs)

    # Archiver les données
        produits = []
        for commande in commandes:
            for cp in commande.commande_produits.all():
                produits.append({
                    'commande_id': commande.id,
                    'produit': cp.produit.nom,
                    'quantite': cp.quantite,
                    'prix_unitaire': cp.produit.prix,
                    'total_ligne': cp.quantite * cp.produit.prix,
                    'date_livraison': commande.date_livraison.isoformat()
                })

        paiements_archives = [{
            'montant': p.montant,
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


@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ['id', 'date_commande', 'client', 'total', 'statut', 'is_speciale', 'generate_facture_button']
    inlines = [CommandeProduitInline]
    list_filter = [
        DateLivraisonJourFilter,
        'statut',
        'date_commande',
        'is_speciale'
    ]
    search_fields = ['client__nom', 'id']

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
            response['Content-Disposition'] = f'inline; filename=\"facture_{facture.id}.pdf\"'
            return response

@admin.register(Produit)
class ProduitAdmin(admin.ModelAdmin):
    list_display = ['nom', 'prix']
    search_fields = ['nom']

@admin.register(Ingredient)
class IngredientAdmin(admin.ModelAdmin):
    list_display = ['nom', 'quantite_stock', 'unite', 'seuil_minimum']
    search_fields = ['nom']

@admin.register(ProduitIngredient)
class ProduitIngredientAdmin(admin.ModelAdmin):
    list_display = ['produit', 'ingredient', 'quantite']
    list_filter = ['produit', 'ingredient']
    search_fields = ['produit__nom', 'ingredient__nom']

@admin.register(Client)
class ClientAdmin(admin.ModelAdmin):
    list_display = ('nom', 'email', 'telephone', 'adresse', 'solde', 'frequence_paiement')
    search_fields = ('nom', 'email')
    list_filter = ('nom', 'frequence_paiement')

@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = ['id', 'commande', 'date_facture', 'montant_total']
    search_fields = ['commande__id', 'id']

@admin.register(PaiementClient)
class PaiementClientAdmin(admin.ModelAdmin):
    list_display = ['client', 'montant', 'date_paiement', 'mode_paiement']
    list_filter = ['client', 'date_paiement', 'mode_paiement']
    search_fields = ['client__nom']

    def save_model(self, request, obj, form, change):
        super().save_model(request, obj, form, change)
        if obj.client:
            obj.client.recalculer_solde()

class CommandeModeleProduitInline(admin.TabularInline):
    model = CommandeModeleProduit
    extra = 1
    fields = ['produit', 'quantite']

@admin.register(CommandeModele)
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
            links.append(f'<a class="button" href="{reverse("admin:gestion_commandemodele_change", args=(previous.pk,))}">← Précédent</a>')
        links.append(f'<a class="button" href="{reverse("admin:gestion_commandemodele_changelist")}">Retour à la liste</a>')
        if next:
            links.append(f'<a class="button" href="{reverse("admin:gestion_commandemodele_change", args=(next.pk,))}">Suivant →</a>')

        extra_context = extra_context or {}
        extra_context['navigation_links'] = format_html(
            '<div style="display:flex; justify-content:center; gap: 1em; margin: 1em 0;">{}</div>',
            format_html(' '.join(links))
        )

        return super().change_view(request, object_id, form_url, extra_context=extra_context)

@admin.register(Jour)
class JourAdmin(admin.ModelAdmin):
    list_display = ['code']

@admin.register(FactureCloturee)
class FactureClotureeAdmin(admin.ModelAdmin):
    list_display = ['client', 'date_facture', 'montant_total_commandes', 'montant_total_paye', 'download_pdf_button']
    list_filter = ['date_facture']
    search_fields = ['client__nom']
    readonly_fields = ['client', 'date_facture', 'montant_total_commandes', 'montant_total_paye', 'commentaire']

    def get_urls(self):
        urls = super().get_urls()
        custom_urls = [
            path('<int:facture_id>/download/', self.admin_site.admin_view(self.download_pdf), name='facturecloturee_download'),
        ]
        return custom_urls + urls

    def download_pdf_button(self, obj):
        url = reverse('admin:facturecloturee_download', args=[obj.pk])
        return format_html('<a class="button" href="{}">📄 Télécharger PDF</a>', url)
    download_pdf_button.short_description = "Télécharger PDF"

    def download_pdf(self, request, facture_id):
        facture = FactureCloturee.objects.get(pk=facture_id)
        pdf_path = facture.generer_pdf()

        with open(pdf_path, 'rb') as f:
            response = HttpResponse(f.read(), content_type='application/pdf')
            response['Content-Disposition'] = f'inline; filename=\"facture_cloturee_{facture.id}.pdf\"'
            return response
