from django.db import models
from django.utils.timezone import now
from reportlab.pdfgen import canvas
from django.http import FileResponse
import io

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
    date_commande = models.DateTimeField(auto_now_add=True)
    produits = models.ManyToManyField(Produit)
    total = models.FloatField(default=0)
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
        # 1. Enregistrer la commande pour obtenir un ID
        super().save(*args, **kwargs)

        # 2. Calculer le total des produits après l'enregistrement
        total = sum(produit.prix for produit in self.produits.all())
        if self.total != total:
            self.total = total
            super().save(update_fields=['total'])

        # 3. Générer une facture si elle n'existe pas encore
        if not hasattr(self, 'facture'):
            Facture.objects.get_or_create(
                commande=self,
                defaults={'montant_total': self.total}
            )

    def __str__(self):
        return f"Commande #{self.id} - {self.statut}"

class Facture(models.Model):
    commande = models.OneToOneField('Commande', on_delete=models.CASCADE, related_name='facture')
    date_facture = models.DateTimeField(default=now)
    montant_total = models.FloatField()

    def __str__(self):
        return f"Facture #{self.id} pour Commande #{self.commande.id}"

    def generer_pdf(self):
        buffer = io.BytesIO()
        pdf = canvas.Canvas(buffer)

        # Détails de la facture
        pdf.drawString(100, 750, f"Facture #{self.id}")
        pdf.drawString(100, 730, f"Date : {self.date_facture}")
        pdf.drawString(100, 710, f"Montant Total : {self.montant_total} TND")
        pdf.drawString(100, 690, f"Commande : #{self.commande.id}")

        # Fin du PDF
        pdf.showPage()
        pdf.save()
        buffer.seek(0)
        return FileResponse(buffer, as_attachment=True, filename=f'facture_{self.id}.pdf')
