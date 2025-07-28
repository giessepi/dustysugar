from django.db import models
from django.utils.timezone import now, timedelta
from django.template.loader import render_to_string
from weasyprint import HTML
import os
from django.conf import settings
from django.db.models import JSONField
from decimal import Decimal
from collections import defaultdict

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
    quantite_stock = models.DecimalField(max_digits=10, decimal_places=2)
    unite = models.CharField(max_length=20)
    seuil_minimum = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return self.nom

class Produit(models.Model):
    CATEGORIES = [
        ('croissanterie', 'Croissanterie'),
        ('sale', 'Salé'),
        ('patisserie', 'Pâtisserie'),
    ]

    nom = models.CharField(max_length=100)
    prix = models.DecimalField(max_digits=10, decimal_places=2)
    categorie = models.CharField(max_length=20, choices=CATEGORIES, default='croissanterie')
    ingredients = models.ManyToManyField('Ingredient', through='ProduitIngredient')

    def __str__(self):
        return self.nom

class ProduitIngredient(models.Model):
    produit = models.ForeignKey('Produit', on_delete=models.CASCADE)
    ingredient = models.ForeignKey('Ingredient', on_delete=models.CASCADE)
    quantite = quantite = models.DecimalField(max_digits=10, decimal_places=2)
    


    def __str__(self):
        return f"{self.quantite} {self.ingredient.unite} de {self.ingredient.nom} pour {self.produit.nom}"

class Client(models.Model):
    nom = models.CharField(max_length=100)
    email = models.EmailField(unique=True, blank=True, null=True)
    telephone = models.CharField(max_length=15, blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    matricule_fiscale = models.CharField(max_length=100, blank=True, null=True)

    livre_par_nous = models.BooleanField(
        default=True,
        help_text="Indique si ce client est livré par nos soins"
    )

    mode_livraison = models.CharField(
        max_length=10,
        choices=[('bac', 'Par bacs'), ('paquet', 'Par paquets')],
        default='bac',
        help_text="Méthode de livraison pour le chargement"
    )


    solde = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
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
        self.solde = Decimal(commandes_total) - Decimal(paiements_total)
        self.save(update_fields=["solde"])

class Commande(models.Model):
    client = models.ForeignKey('Client', on_delete=models.SET_NULL, null=True, blank=True, related_name='commandes')
    date_commande = models.DateTimeField(auto_now_add=True)
    date_livraison = models.DateField(default=now)
    produits = models.ManyToManyField('Produit', through='CommandeProduit')
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
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
        total = Decimal('0.00')
        for cp in self.commande_produits.all():
            prix = cp.prix_unitaire if cp.prix_unitaire is not None else Decimal(str(cp.produit.prix))
            total += prix * cp.quantite
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
    prix_unitaire = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.commande:
            self.commande.calculer_total()
            if self.commande.client:
                self.commande.client.recalculer_solde()

    @property
    def total_ligne(self):
        prix = self.prix_unitaire if self.prix_unitaire is not None else self.produit.prix
        return prix * self.quantite

    def __str__(self):
        return f"{self.quantite} x {self.produit.nom} (Commande #{self.commande.id})"

class Facture(models.Model):
    commande = models.OneToOneField('Commande', on_delete=models.CASCADE, related_name='facture')
    date_facture = models.DateTimeField(default=now)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)

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
    montant = models.DecimalField(max_digits=10, decimal_places=2)
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
        

    def get_lignes_regroupees(self):
        lignes = defaultdict(lambda: {"quantite": 0, "prix_unitaire": None, "total_ligne": Decimal("0.000")})

        for commande in self.commandes.all():
            for ligne in commande.commande_produits.all():
                produit = ligne.produit.nom
                prix = ligne.prix_unitaire if ligne.prix_unitaire is not None else ligne.produit.prix

                lignes[produit]["quantite"] += ligne.quantite
                lignes[produit]["prix_unitaire"] = prix
                lignes[produit]["total_ligne"] += prix * ligne.quantite

        return [
            {
                "produit": produit,
                "quantite": data["quantite"],
                "prix_unitaire": data["prix_unitaire"],
                "total_ligne": data["total_ligne"]
            }
            for produit, data in lignes.items()
        ]


class FactureCloturee(models.Model):
    produits_json = models.JSONField(blank=True, null=True)
    paiements_json = models.JSONField(blank=True, null=True)
    client = models.ForeignKey('Client', on_delete=models.CASCADE, related_name='factures_cloturees')
    date_facture = models.DateTimeField(default=now)
    montant_total_commandes = models.DecimalField(max_digits=10, decimal_places=2)
    montant_total_paye = models.DecimalField(max_digits=10, decimal_places=2)
    commentaire = models.TextField(blank=True, null=True)
    numero = models.CharField(max_length=20, blank=True, null=True, unique=True)


    def generer_pdf(self):
        from weasyprint import HTML
        from django.template.loader import render_to_string
        from decimal import Decimal
        import os

        file_name = f"FactureCloturee_{self.id}.pdf"
        file_path = os.path.join(settings.BASE_DIR, 'factures', file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        # 1. Regrouper les produits
        from collections import defaultdict
        produits = defaultdict(lambda: {"quantite": 0, "prix_unitaire": 0})

        for ligne in self.produits_json:
            nom = ligne["produit"]
            produits[nom]["quantite"] += ligne["quantite"]
            produits[nom]["prix_unitaire"] = ligne["prix_unitaire"]

        

        produits_list = []
        montant_ht = Decimal("0.000")

        for nom, infos in produits.items():
            quantite = Decimal(infos["quantite"])
            prix = Decimal(str(infos["prix_unitaire"]))  # conversion sûre
            total = quantite * prix
            montant_ht += total
            produits_list.append({
                "nom": nom,
                "quantite": int(quantite),
                "prix_unitaire": prix,
                "total": total
            })


        # 2. Calcul TVA si client a un matricule fiscale
        tva = Decimal("0.000")
        if self.client.matricule_fiscale:
            tva = round(montant_ht * Decimal("0.19"), 3)
            timbre = Decimal("1.000")
            total_ttc = montant_ht + tva + timbre
        else:
            tva = None
            timbre = None
            total_ttc = montant_ht

        logo_path = os.path.join(settings.BASE_DIR,"gestion", "static", "img", "logo.png")
        logo_uri = "file:///" + logo_path.replace("\\","/")

        from .models import JournalNumerotation  # en haut si pas déjà importé

    # Générer un numéro si TVA applicable et pas encore défini
        if self.client.matricule_fiscale and not self.numero:
            annee = self.date_facture.year
            journal, _ = JournalNumerotation.objects.get_or_create(annee=annee)

            journal.dernier_numero += 1
            journal.save()

            self.numero = f"{journal.dernier_numero:05d}/{annee}"
            self.save(update_fields=["numero"])


        context = {
            "facture": self,
            "client": self.client,
            "produits": produits_list,
            "montant_ht": montant_ht,
            "tva": tva,
            "timbre": timbre,
            "total_ttc": total_ttc,
            "date_livraison": self.date_facture.date(),
            "logo_uri": logo_uri,
        }

        html_content = render_to_string("facture_cloturee_template.html", context)
        HTML(string=html_content).write_pdf(file_path)
        
        return file_path




    def __str__(self):
        return f"Facture clôturée - {self.client.nom} ({self.date_facture.date()})"

    
# Fournisseurs et dépenses

class Fournisseur(models.Model):
    nom = models.CharField(max_length=100)
    email = models.EmailField(blank=True, null=True)
    telephone = models.CharField(max_length=20, blank=True, null=True)
    adresse = models.TextField(blank=True, null=True)
    solde = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))

    def __str__(self):
        return self.nom

    def recalculer_solde(self):
        total_factures = self.factures.aggregate(total=models.Sum('montant_total'))['total'] or 0
        total_paye = PaiementFournisseur.objects.filter(facture__fournisseur=self).aggregate(total=models.Sum('montant'))['total'] or 0
        self.solde = total_factures - total_paye
        self.save(update_fields=['solde'])

class FactureFournisseur(models.Model):
    fournisseur = models.ForeignKey('Fournisseur', on_delete=models.CASCADE, related_name='factures')
    date_facture = models.DateField(default=now)
    montant_total = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    statut = models.CharField(
        max_length=20,
        choices=[('non payée', 'Non payée'), ('payée', 'Payée')],
        default='non payée'
    )

    def __str__(self):
        return f"Facture #{self.id} - {self.fournisseur.nom}"

class PaiementFournisseur(models.Model):
    facture = models.ForeignKey('FactureFournisseur', on_delete=models.CASCADE, related_name='paiements')
    fournisseur = models.ForeignKey('Fournisseur', on_delete=models.CASCADE, related_name='paiements', null=True, blank=True)
    montant = models.DecimalField(max_digits=10, decimal_places=2)
    date_paiement = models.DateField(default=now)
    mode_paiement = models.CharField(
        max_length=20,
        choices=[('virement', 'Virement'), ('espèces', 'Espèces'), ('chèque', 'Chèque')]
    )

    def save(self, *args, **kwargs):
        if self.facture and not self.fournisseur:
            self.fournisseur = self.facture.fournisseur
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Paiement de {self.montant} TND à {self.facture.fournisseur.nom}"


class CompteFournisseur(Fournisseur):
    class Meta:
        proxy = True
        verbose_name = "Compte fournisseur"
        verbose_name_plural = "Comptes fournisseurs"

class FactureFournisseurCloturee(models.Model):
    fournisseur = models.ForeignKey('Fournisseur', on_delete=models.CASCADE, related_name='factures_cloturees')
    date_cloture = models.DateTimeField(default=now)
    montant_total_factures = models.DecimalField(max_digits=10, decimal_places=2)
    montant_total_paye = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField(blank=True, null=True)
    factures_json = models.JSONField(blank=True, null=True)
    paiements_json = models.JSONField(blank=True, null=True)

    def generer_pdf(self):
        file_name = f"FactureFournisseurCloturee_{self.id}.pdf"
        file_path = os.path.join(settings.BASE_DIR, 'factures_fournisseurs_cloturees', file_name)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)

        context = {
            'facture': self,
            'fournisseur': self.fournisseur,
            'date_cloture': self.date_cloture,
            'montant_total_factures': self.montant_total_factures,
            'montant_total_paye': self.montant_total_paye,
            'description': self.description,
            'factures': self.factures_json or [],
            'paiements': self.paiements_json or []
        }

        html = render_to_string("facture_fournisseur_cloturee_template.html", context)
        HTML(string=html).write_pdf(file_path)

        return file_path

    def __str__(self):
        return f"Clôture fournisseur - {self.fournisseur.nom} ({self.date_cloture.date()})"

class JournalNumerotation(models.Model):
    annee = models.PositiveIntegerField(unique=True)
    dernier_numero = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.annee} - Dernier N°: {self.dernier_numero}"


class ClientAdminProxy(Client):
    class Meta:
        proxy = True
        verbose_name = "Client"
        verbose_name_plural = "🧾 Clients - Bases"

class CompteClientAdminProxy(CompteClient):
    class Meta:
        proxy = True
        verbose_name = "Compte client"
        verbose_name_plural = "🧾 Clients - Comptes"

class PaiementClientAdminProxy(PaiementClient):
    class Meta:
        proxy = True
        verbose_name = "Paiement client"
        verbose_name_plural = "🧾 Clients - Paiements"

class FactureAdminProxy(Facture):
    class Meta:
        proxy = True
        verbose_name = "Facture"
        verbose_name_plural = "🧾 Clients - Factures"

class FactureClotureeAdminProxy(FactureCloturee):
    class Meta:
        proxy = True
        verbose_name = "Facture clôturée"
        verbose_name_plural = "🧾 Clients - Cloturées"

class FournisseurAdminProxy(Fournisseur):
    class Meta:
        proxy = True
        verbose_name = "Fournisseur"
        verbose_name_plural = "🏢 Fournisseurs - Bases"

class CompteFournisseurAdminProxy(CompteFournisseur):
    class Meta:
        proxy = True
        verbose_name = "Compte fournisseur"
        verbose_name_plural = "🏢 Fournisseurs - Comptes"

class PaiementFournisseurAdminProxy(PaiementFournisseur):
    class Meta:
        proxy = True
        verbose_name = "Paiement fournisseur"
        verbose_name_plural = "🏢 Fournisseurs - Paiements"

class FactureFournisseurAdminProxy(FactureFournisseur):
    class Meta:
        proxy = True
        verbose_name = "Facture fournisseur"
        verbose_name_plural = "🏢 Fournisseurs - Factures"

class FactureFournisseurClotureeAdminProxy(FactureFournisseurCloturee):
    class Meta:
        proxy = True
        verbose_name = "Facture fournisseur clôturée"
        verbose_name_plural = "🏢 Fournisseurs - Cloturées"

class CommandeAdminProxy(Commande):
    class Meta:
        proxy = True
        verbose_name = "Commande"
        verbose_name_plural = "🛒 Commandes - Bases"

class CommandeModeleAdminProxy(CommandeModele):
    class Meta:
        proxy = True
        verbose_name = "Commande modèle"
        verbose_name_plural = "🛒 Commandes - Modèles"

class CommandeProduitAdminProxy(CommandeProduit):
    class Meta:
        proxy = True
        verbose_name = "Commande produit"
        verbose_name_plural = "🛒 Commandes - Produits"

class CommandeModeleProduitAdminProxy(CommandeModeleProduit):
    class Meta:
        proxy = True
        verbose_name = "Commande modèle produit"
        verbose_name_plural = "🛒 Commandes Modèles - Produits"

class ProduitAdminProxy(Produit):
    class Meta:
        proxy = True
        verbose_name = "Produit"
        verbose_name_plural = "🍰 Produits - Bases"

class IngredientAdminProxy(Ingredient):
    class Meta:
        proxy = True
        verbose_name = "Ingrédient"
        verbose_name_plural = "🍳 Ingrédients"

class PlanLivraison(models.Model):
    nom = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nom        

class EtapeLivraison(models.Model):
    plan = models.ForeignKey(PlanLivraison, on_delete=models.CASCADE, related_name='etapes')
    client = models.OneToOneField('Client', on_delete=models.CASCADE)
    ordre = models.PositiveIntegerField(default=0)
    actif = models.BooleanField(default=True)  # ← ce champ permet de désactiver sans supprimer
    groupe = models.CharField(max_length=100, blank=True, null=True)

    class Meta:
        ordering = ['ordre']

    def __str__(self):
        return f"{self.ordre:03d} - {self.client.nom}" + (" ❌" if not self.actif else "")

class PlanLivraisonPrincipal(PlanLivraison):
    class Meta:
        proxy = True
        verbose_name = "Plan de livraison"
        verbose_name_plural = "🚚 Plan de livraison"
