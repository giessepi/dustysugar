from django.db import models
from django.utils.timezone import now
from django.template.loader import render_to_string
from weasyprint import HTML
import os
from django.conf import settings

class Ingredient(models.Model):
    nom = models.CharField(max_length=100)
    quantite_stock = models.FloatField()
    unite = models.CharField(max_length=20)
    seuil_minimum = models.FloatField()

    def __str__(self):
        return self.nom

class Produit(models.Model):
    nom = models.CharField(max_length=100)
    prix = models.FloatField()
    ingredients = models.ManyToManyField(Ingredient, through='ProduitIngredient')

    def __str__(self):
        return self.nom

class ProduitIngredient(models.Model):
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    ingredient = models.ForeignKey(Ingredient, on_delete=models.CASCADE)
    quantite = models.FloatField()

    def __str__(self):
        return f"{self.quantite} {self.ingredient.unite} de {self.ingredient.nom} pour {self.produit.nom}"

class Client(models.Model):
    nom = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    telephone = models.CharField(max_length=15, blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)

    def __str__(self):
        return self.nom

class Commande(models.Model):
    client = models.ForeignKey(Client, on_delete=models.SET_NULL, null=True, blank=True, related_name='commandes')
    date_commande = models.DateTimeField(auto_now_add=True)
    produits = models.ManyToManyField(Produit, through='CommandeProduit')
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
        super().save(*args, **kwargs)
        self.calculer_total()
        self.deduire_stock()

        facture, created = Facture.objects.get_or_create(
            commande=self,
            defaults={'montant_total': self.total}
        )
        facture.montant_total = self.total
        facture.save()
        facture.generer_pdf()

    def calculer_total(self):
        total = sum(cp.produit.prix * cp.quantite for cp in self.commande_produits.all())
        self.total = total
        super().save(update_fields=['total'])

    def deduire_stock(self):
        for cp in self.commande_produits.all():
            produit = cp.produit
            for pi in produit.produitingredient_set.all():
                ingredient = pi.ingredient
                quantite_utilisee = pi.quantite * cp.quantite
                ingredient.quantite_stock -= quantite_utilisee
                ingredient.save()

    def __str__(self):
        return f"Commande #{self.id} - {self.statut}"

class CommandeProduit(models.Model):
    commande = models.ForeignKey(Commande, on_delete=models.CASCADE, related_name='commande_produits')
    produit = models.ForeignKey(Produit, on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        self.commande.calculer_total()

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom} (Commande #{self.commande.id})"

class Facture(models.Model):
    commande = models.OneToOneField('Commande', on_delete=models.CASCADE, related_name='facture')
    date_facture = models.DateTimeField(default=now)
    montant_total = models.FloatField()

    def generer_pdf(self):
        print(f"📄 Génération PDF pour Facture #{self.id}")

        file_name = f"Facture_{self.id}.pdf"
        file_path = os.path.join(settings.BASE_DIR, 'factures', file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        context = {
            'facture': self,
            'commande': self.commande,
        }

        html_content = render_to_string('facture_template.html', context)
        print("🔍 Contenu HTML extrait ✅")

        HTML(string=html_content).write_pdf(file_path)
        print(f"✅ PDF généré : {file_path}")

        return file_path

    def __str__(self):
        return f"Facture #{self.id} pour Commande #{self.commande.id}"
