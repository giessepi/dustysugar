from django.test import TestCase
from gestion.models import Client, Produit, Commande, CommandeProduit, PaiementClient

class SoldeClientTestCase(TestCase):
    def setUp(self):
        self.client = Client.objects.create(nom="Test Client")
        self.produit = Produit.objects.create(nom="Produit A", prix=10.0)

    def test_solde_apres_commande_et_paiement(self):
        commande = Commande.objects.create(client=self.client)
        CommandeProduit.objects.create(commande=commande, produit=self.produit, quantite=2)
        commande.finaliser_commande()

        PaiementClient.objects.create(client=self.client, montant=15.0)

        self.client.refresh_from_db()
        self.assertEqual(self.client.solde, 5.0)
