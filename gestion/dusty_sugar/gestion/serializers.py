from rest_framework import serializers
from .models import Ingredient, Produit, ProduitIngredient, Commande, Facture

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'

class ProduitIngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProduitIngredient
        fields = '__all__'

class ProduitSerializer(serializers.ModelSerializer):
    ingredients = ProduitIngredientSerializer(source='produitingredient_set', many=True)

    class Meta:
        model = Produit
        fields = '__all__'

class CommandeSerializer(serializers.ModelSerializer):
    produits = serializers.PrimaryKeyRelatedField(
        many=True,
        queryset=Produit.objects.all()
    )

    class Meta:
        model = Commande
        fields = '__all__'

class FactureSerializer(serializers.ModelSerializer):
    commande = CommandeSerializer()

    class Meta:
        model = Facture
        fields = '__all__'
