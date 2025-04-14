from django.contrib import admin
from .models import Ingredient, Produit, ProduitIngredient, Client, Commande, CommandeProduit, Facture

class ProduitIngredientInline(admin.TabularInline):
    model = ProduitIngredient
    extra = 1

class ProduitAdmin(admin.ModelAdmin):
    list_display = ('nom', 'prix')
    inlines = [ProduitIngredientInline]  # Ajoute les ingrédients via le modèle intermédiaire

class ProduitIngredientAdmin(admin.ModelAdmin):
    list_display = ('produit', 'ingredient', 'quantite')
    list_filter = ('produit',)

class IngredientAdmin(admin.ModelAdmin):
    list_display = ('nom', 'quantite_stock', 'unite', 'seuil_minimum')
    search_fields = ('nom',)

class ClientAdmin(admin.ModelAdmin):
    list_display = ('nom', 'email', 'telephone')

class CommandeProduitInline(admin.TabularInline):
    model = CommandeProduit
    extra = 1

class CommandeAdmin(admin.ModelAdmin):
    list_display = ('id', 'client', 'date_commande', 'total', 'statut')
    list_filter = ('statut', 'date_commande')
    inlines = [CommandeProduitInline]

class FactureAdmin(admin.ModelAdmin):
    list_display = ('id', 'commande', 'date_facture', 'montant_total')

admin.site.register(Ingredient, IngredientAdmin)
admin.site.register(Produit, ProduitAdmin)
admin.site.register(ProduitIngredient, ProduitIngredientAdmin)
admin.site.register(Client, ClientAdmin)
admin.site.register(Commande, CommandeAdmin)
admin.site.register(Facture, FactureAdmin)
