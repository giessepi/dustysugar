from django.contrib import admin
from .models import Commande, Produit, Ingredient, ProduitIngredient, CommandeProduit, Client, Facture

class CommandeProduitInline(admin.TabularInline):
    model = CommandeProduit
    extra = 1  # Nombre de lignes vides par défaut
    fields = ['produit', 'quantite']

@admin.register(Commande)
class CommandeAdmin(admin.ModelAdmin):
    list_display = ['id', 'date_commande', 'client', 'total', 'statut']
    inlines = [CommandeProduitInline]
    list_filter = ['statut', 'date_commande']
    search_fields = ['client__nom', 'id']

    def save_model(self, request, obj, form, change):
        obj.save()
        if hasattr(obj, 'facture'):
            obj.facture.montant_total = obj.total
            obj.facture.save()
            obj.facture.generer_pdf()

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
    list_display = ('nom', 'email', 'telephone', 'adresse')
    search_fields = ('nom', 'email')
    list_filter = ('nom',)

@admin.register(Facture)
class FactureAdmin(admin.ModelAdmin):
    list_display = ['id', 'commande', 'date_facture', 'montant_total']
    search_fields = ['commande__id', 'id']
