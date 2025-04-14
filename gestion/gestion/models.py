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

class Client(models.Model):
    nom = models.CharField(max_length=100)  # Nom du client
    email = models.EmailField(unique=True)  # Email du client
    telephone = models.CharField(max_length=15, blank=True, null=True)  # Téléphone du client
    adresse = models.TextField(blank=True, null=True)  # Adresse complète du client

    def __str__(self):
        return self.nom

class Commande(models.Model):
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='commandes')  # Client associé
    date_commande = models.DateTimeField(auto_now_add=True)  # Date de la commande
    produits = models.ManyToManyField(Produit, through='CommandeProduit')  # Produits dans la commande
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
        is_new = self.pk is None
        super().save(*args, **kwargs)

        total = sum(cp.produit.prix * cp.quantite for cp in self.commande_produits.all())
        if self.total != total:
            self.total = total
            super().save(update_fields=['total'])

        facture, created = Facture.objects.get_or_create(
            commande=self,
            defaults={'montant_total': self.total}
        )
        if not created:
            facture.montant_total = self.total
            facture.save()
            facture.generer_pdf()

    def __str__(self):
        return f"Commande #{self.id} - {self.statut}"

class CommandeProduit(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='commande_produits')
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom} (Commande #{self.commande.id})"

class Facture(models.Model):
    commande = models.OneToOneField('Commande', on_delete=models.CASCADE, related_name='facture')
    date_facture = models.DateTimeField(default=now)        # Date de la facture
    montant_total = models.FloatField()

    def generer_pdf(self):
        print(f"Début de la génération du PDF pour la facture #{self.id}")  # Débogage
        file_name = f"Facture_{self.id}.pdf"
        file_path = os.path.join('factures', file_name)

        os.makedirs('factures', exist_ok=True)
        print(f"Dossier 'factures' vérifié ou créé.")  # Débogage

        context = {
            'facture': self,
            'commande': self.commande,
        }
        html_content = render_to_string('facture_template.html', context)
        print(f"Template HTML rendu pour la facture #{self.id}.")  # Débogage

        HTML(string=html_content).write_pdf(file_path)
        print(f"PDF sauvegardé : {file_path}")  # Débogage

        return file_path

    def __str__(self):
        return f"Facture #{self.id} pour Commande #{self.commande.id}"
