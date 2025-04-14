from django.db import models
from django.utils.timezone import now
from django.template.loader import render_to_string
from weasyprint import HTML
import os

class Ingredient(models.Model):
    nom = models.CharField(max_length=100)  # Nom de l'ingrédient
    quantite_stock = models.FloatField()    # Quantité disponible
    unite = models.CharField(max_length=20) # Unité de mesure (kg, litre, etc.)
    seuil_minimum = models.FloatField()     # Seuil minimum avant alerte

    def __str__(self):
        return self.nom


class Produit(models.Model):
    nom = models.CharField(max_length=100)  # Nom du produit
    prix = models.FloatField()              # Prix du produit
    ingredients = models.ManyToManyField(Ingredient, through='ProduitIngredient')

    def __str__(self):
        return self.nom


class ProduitIngredient(models.Model):
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantite = models.FloatField()  # Quantité nécessaire pour cet ingrédient

    def __str__(self):
        return f"{self.quantite} {self.ingredient.unite} de {self.ingredient.nom} pour {self.produit.nom}"


class Commande(models.Model):
    date_commande = models.DateTimeField(auto_now_add=True)  # Date de la commande
    produits = models.ManyToManyField(Produit)              # Produits dans la commande
    total = models.FloatField(default=0)                    # Total de la commande
    statut = models.CharField(
        max_length=20,
        choices=[
            ('En attente', 'En attente'),
            ('En préparation', 'En préparation'),
            ('Livrée', 'Livrée'),
        ],
        default='En attente'
    )

    def save(self, *args, **kwargs):
        # Enregistrer la commande pour obtenir un ID
        super().save(*args, **kwargs)

        # Calculer le total des produits après l'enregistrement
        total = sum(produit.prix for produit in self.produits.all())
        if self.total != total:
            self.total = total
            super().save(update_fields=['total'])

        # Générer automatiquement la facture si elle n'existe pas
        if not hasattr(self, 'facture'):
            Facture.objects.get_or_create(
                commande=self,
                defaults={'montant_total': self.total}
            )

    def __str__(self):
        return f"Commande #{self.id} - {self.statut}"


class Facture(models.Model):
    commande = models.OneToOneField('Commande', on_delete=models.CASCADE, related_name='facture')
    date_facture = models.DateTimeField(default=now)        # Date de la facture
    montant_total = models.FloatField()                    # Total de la facture

    def generer_pdf(self):
        # Chemin du fichier PDF
        file_name = f"Facture_{self.id}.pdf"
        file_path = os.path.join('factures', file_name)

        # Charger le modèle HTML avec les données de la facture
        context = {
            'facture': self,
            'commande': self.commande,
        }
        html_content = render_to_string('factures/facture_template.html', context)

        # Générer le PDF
        HTML(string=html_content).write_pdf(file_path)

        return file_path

    def __str__(self):
        return f"Facture #{self.id} pour Commande #{self.commande.id}"
