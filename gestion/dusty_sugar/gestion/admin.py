from django.contrib import admin
from .models import Ingredient, Produit, ProduitIngredient, Commande

admin.site.register(Ingredient)
admin.site.register(Produit)
admin.site.register(ProduitIngredient)
admin.site.register(Commande)
