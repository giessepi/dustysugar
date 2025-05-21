from django.core.management.base import BaseCommand
from django.utils.timezone import now, timedelta
from gestion.models import CommandeModele, Commande, CommandeProduit

class Command(BaseCommand):
    help = "Génère les commandes journalières à partir des CommandeModele actifs et du jour suivant"

    def handle(self, *args, **kwargs):
        today = now().date()
        tomorrow = today + timedelta(days=1)
        jour_code = str(tomorrow.weekday())  # '0' = lundi, '6' = dimanche

        total_generées = 0

        modeles = CommandeModele.objects.filter(active=True, jours__code=jour_code).distinct()

        # 🔁 Étape 1 : Purge des commandes orphelines (aucun modèle actif ne correspond)
        model_client_ids = set(m.client_id for m in modeles)
        commandes_orphelines = Commande.objects.filter(
            date_livraison=tomorrow,
            is_speciale=False
        ).exclude(client_id__in=model_client_ids)

        nb_orphelines = commandes_orphelines.count()
        if nb_orphelines:
            commandes_orphelines.delete()
            self.stdout.write(f"🗑️  {nb_orphelines} commande(s) orpheline(s) supprimée(s) (plus de modèle associé).")

        # 🔁 Étape 2 : Génération ou mise à jour des commandes normales
        for modele in modeles:
            client = modele.client

            # Vérifie si une commande spéciale existe déjà pour ce client demain
            if Commande.objects.filter(client=client, date_livraison=tomorrow, is_speciale=True).exists():
                self.stdout.write(f"❌ Commande spéciale déjà prévue pour {client} le {tomorrow}.")
                continue

            # Vérifie s'il existe déjà une commande normale
            commande_existante = Commande.objects.filter(client=client, date_livraison=tomorrow, is_speciale=False).first()

            produits_modeles = list(modele.commandemodeleproduit_set.all())

            if commande_existante:
                produits_commandes = list(commande_existante.commande_produits.all())

                # Compare les listes de produits (simple comparaison sur produit + quantite)
                produits_modele_set = set((p.produit_id, p.quantite) for p in produits_modeles)
                produits_commande_set = set((p.produit_id, p.quantite) for p in produits_commandes)

                if produits_modele_set == produits_commande_set:
                    self.stdout.write(f"↪️  Commande déjà existante et identique pour {client} — non modifiée.")
                    continue

                # Sinon : mise à jour
                commande_existante.commande_produits.all().delete()
                for item in produits_modeles:
                    CommandeProduit.objects.create(
                        commande=commande_existante,
                        produit=item.produit,
                        quantite=item.quantite
                    )
                commande_existante.update_facture()
                commande_existante.facture.generer_pdf()
                self.stdout.write(f"♻️  Commande mise à jour pour {client} pour le {tomorrow}")
                total_generées += 1

            else:
                # Créer la commande réelle
                commande = Commande.objects.create(
                    client=client,
                    date_livraison=tomorrow,
                    is_speciale=False,
                )

                for item in produits_modeles:
                    CommandeProduit.objects.create(
                        commande=commande,
                        produit=item.produit,
                        quantite=item.quantite
                    )

                facture = commande.update_facture()
                facture.generer_pdf()

                self.stdout.write(f"✅ Commande générée pour {client} pour le {tomorrow}")
                total_generées += 1

        self.stdout.write(self.style.SUCCESS(f"✅ {total_generées} commandes générées ou mises à jour pour le {tomorrow}."))
