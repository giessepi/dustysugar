from django.db import models
from django.utils.timezone import now, timedelta
from django.template.loader import render_to_string
from weasyprint import HTML
import os
from django.conf import settings

JOUR_CHOIX = [
    ('0', 'Lundi'),
    ('1', 'Mardi'),
    ('2', 'Mercredi'),
    ('3', 'Jeudi'),
    ('4', 'Vendredi'),
    ('5', 'Samedi'),
    ('6', 'Dimanche'),
]

class Jour(models.Model):
    code = models.CharField(max_length=1, choices=JOUR_CHOIX, unique=True)

    def __str__(self):
        return self.get_code_display()

class Ingredient(models.Model):
    nom = models.CharField(max_length=100)
    quantite_stock = models.FloatField()
    unite = models.CharField(max_length=20)
    seuil_minimum = models.FloatField()

    def __str__(self):
        return self.nom

class Produit(models.Model):
    CATEGORIES = [
        ('croissanterie', 'Croissanterie'),
        ('sale', 'Salé'),
        ('patisserie', 'Pâtisserie'),
    ]

    nom = models.CharField(max_length=100)
    prix = models.FloatField()
    categorie = models.CharField(max_length=20, choices=CATEGORIES, default='croissanterie')
    ingredients = models.ManyToManyField('Ingredient', through='ProduitIngredient')

    def __str__(self):
        return self.nom

class ProduitIngredient(models.Model):
    produit = models.ForeignKey('Produit', on_delete=models.CASCADE)
    ingredient = models.ForeignKey('Ingredient', on_delete=models.CASCADE)
    quantite = models.FloatField()

    def __str__(self):
        return f"{self.quantite} {self.ingredient.unite} de {self.ingredient.nom} pour {self.produit.nom}"

class Client(models.Model):
    nom = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=True, null=True)
    telephone = models.CharField(max_length=15, blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    solde = models.FloatField(default=0.0)
    frequence_paiement = models.CharField(
        max_length=20,
        choices=[
            ('journalier', 'Journalier'),
            ('hebdomadaire', 'Hebdomadaire'),
            ('mensuel', 'Mensuel'),
        ],
        default='journalier'
    )

    def __str__(self):
        return self.nom

    def recalculer_solde(self):
        commandes_total = self.commandes.aggregate(total=models.Sum('total'))['total'] or 0
        paiements_total = self.paiements.aggregate(total=models.Sum('montant'))['total'] or 0
        self.solde = commandes_total - paiements_total
        self.save(update_fields=["solde"])

class Commande(models.Model):
    client = models.ForeignKey('Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='commandes')
    date_commande = models.DateTimeField(auto_now_add=True)
    date_livraison = models.DateField(default=now)
    produits = models.ManyToManyField('Produit', through='CommandeProduit')
    total = models.FloatField(default=0)
    is_speciale = models.BooleanField(default=False)
    statut = models.CharField(
        max_length=20,
        choices=[
            ('En attente', 'En attente'),
            ('En préparation', 'En préparation'),
            ('Livrée', 'Livrée'),
        ],
        default='En attente'
    )
    remarque = models.TextField(blank=True, null=True)

    def calculer_total(self):
        total = sum(cp.produit.prix * cp.quantite for cp in self.commande_produits.all())
        self.total = total
        self.save(update_fields=['total'])

    def deduire_stock(self):
        for cp in self.commande_produits.all():
            produit = cp.produit
            for pi in produit.produitingredient_set.all():
                ingredient = pi.ingredient
                quantite_utilisee = pi.quantite * cp.quantite
                ingredient.quantite_stock -= quantite_utilisee
                ingredient.save()

    def update_facture(self):
        self.calculer_total()
        facture, created = Facture.objects.get_or_create(
            commande=self,
            defaults={'montant_total': self.total}
        )
        if not created:
            facture.montant_total = self.total
            facture.save()
        return facture

    def finaliser_commande(self):
        self.save()
        self.calculer_total()
        self.deduire_stock()
        if self.client:
            self.client.recalculer_solde()

    def __str__(self):
        return f"Commande #{self.id} - {self.statut}"

class CommandeProduit(models.Model):
    commande = models.ForeignKey('Commande', on_delete=models.CASCADE, related_name='commande_produits')
    produit = models.ForeignKey('Produit', on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField(default=1)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.commande:
            self.commande.calculer_total()

    @property
    def total_ligne(self):
        return self.quantite * self.produit.prix

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom} (Commande #{self.commande.id})"

class Facture(models.Model):
    commande = models.OneToOneField('Commande', on_delete=models.CASCADE, related_name='facture')
    date_facture = models.DateTimeField(default=now)
    montant_total = models.FloatField()

    def generer_pdf(self):
        file_name = f"Facture_{self.id}.pdf"
        file_path = os.path.join(settings.BASE_DIR, 'factures', file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        livraison = self.commande.date_livraison if self.commande.date_livraison else now().date() + timedelta(days=1)

        context = {
            'facture': self,
            'commande': self.commande,
            'date_affichee': livraison
        }

        html_content = render_to_string('facture_template.html', context)
        HTML(string=html_content).write_pdf(file_path)

        return file_path

    def __str__(self):
        return f"Facture #{self.id} pour Commande #{self.commande.id}"

class PaiementClient(models.Model):
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='paiements')
    montant = models.FloatField()
    date_paiement = models.DateField(default=now)
    mode_paiement = models.CharField(
        max_length=50,
        choices=[
            ('especes', 'Espèces'),
            ('virement', 'Virement'),
            ('cheque', 'Chèque'),
            ('carte', 'Carte Bancaire'),
        ],
        default='especes'
    )
    commentaire = models.TextField(blank=True, null=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.client:
            self.client.recalculer_solde()

    def __str__(self):
        return f"Paiement de {self.montant} TND pour {self.client.nom}"

class CommandeModele(models.Model):
    client = models.ForeignKey('Client', on_delete=models.CASCADE)
    produits = models.ManyToManyField('Produit', through='CommandeModeleProduit')
    jours = models.ManyToManyField('Jour', related_name='modeles')
    active = models.BooleanField(default=True)
    remarque = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Modèle de {self.client}"

class CommandeModeleProduit(models.Model):
    commande_modele = models.ForeignKey('CommandeModele', on_delete=models.CASCADE)
    produit = models.ForeignKey('Produit', on_delete=models.CASCADE)
    quantite = models.PositiveIntegerField()

class CompteClient(Client):
    class Meta:
        proxy = True
        verbose_name = "Compte client"
        verbose_name_plural = "Comptes clients"
