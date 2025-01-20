from rest_framework import serializers
from .models import Ingredient, Produit, Commande, CommandeProduit, Facture

class IngredientSerializer(serializers.ModelSerializer):
    class Meta:
        model = Ingredient
        fields = '__all__'

class ProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = Produit
        fields = '__all__'

class CommandeProduitSerializer(serializers.ModelSerializer):
    class Meta:
        model = CommandeProduit
        fields = ['produit', 'quantite']

class CommandeSerializer(serializers.ModelSerializer):
    commande_produits = CommandeProduitSerializer(many=True)

    class Meta:
        model = Commande
        fields = ['id', 'date_commande', 'commande_produits', 'total', 'statut']

    def create(self, validated_data):
        produits_data = validated_data.pop('commande_produits')
        commande = Commande.objects.create(**validated_data)
        for produit_data in produits_data:
            CommandeProduit.objects.create(commande=commande, **produit_data)
        return commande

class FactureSerializer(serializers.ModelSerializer):
    class Meta:
        model = Facture
        fields = '__all__'
