from decimal import Decimal
from django.test import TestCase
from gestion.models import Client, Produit, Commande, CommandeProduit, PaiementClient

class SoldeClientSignalTest(TestCase):
    def setUp(self):
        self.client = Client.objects.create(nom="Test Client")
        self.produit = Produit.objects.create(nom="Produit A", prix=Decimal("12.50"))

    def test_solde_apres_ajout_commande(self):
        commande = Commande.objects.create(client=self.client)
        CommandeProduit.objects.create(commande=commande, produit=self.produit, quantite=2)
        commande.refresh_from_db()
        self.client.refresh_from_db()
        self.assertEqual(commande.total, Decimal("25.00"))
        self.assertEqual(self.client.solde, Decimal("25.00"))

    def test_solde_apres_paiement(self):
        commande = Commande.objects.create(client=self.client)
        CommandeProduit.objects.create(commande=commande, produit=self.produit, quantite=2)
        PaiementClient.objects.create(client=self.client, montant=Decimal("10.00"))
        self.client.refresh_from_db()
        self.assertEqual(self.client.solde, Decimal("15.00"))

    def test_solde_apres_suppression_commande(self):
        commande = Commande.objects.create(client=self.client)
        CommandeProduit.objects.create(commande=commande, produit=self.produit, quantite=2)
        commande.delete()
        self.client.refresh_from_db()
        self.assertEqual(self.client.solde, Decimal("0.00"))

    def test_solde_apres_suppression_paiement(self):
        commande = Commande.objects.create(client=self.client)
        CommandeProduit.objects.create(commande=commande, produit=self.produit, quantite=2)
        paiement = PaiementClient.objects.create(client=self.client, montant=Decimal("10.00"))
        paiement.delete()
        self.client.refresh_from_db()
        self.assertEqual(self.client.solde, Decimal("25.00"))
