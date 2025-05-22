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
    CommandeModele, CommandeModeleProduit, PaiementClient, CompteClient, Jour
)
import datetime
from django.db import models

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
        urls = super().get_urls()
        custom_urls = [
            path('<int:client_id>/export/', self.admin_site.admin_view(self.export_releve), name='compteclient_export'),
            path('resumes/', self.admin_site.admin_view(self.export_resume_clients), name='compteclient_resume')
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

@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ['id', 'date_commande', 'client', 'total', 'statut', 'is_speciale']
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
