from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError


class GestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestion'

    def ready(self):
        try:
            from . import admin
            from .models import (
                Jour, Commande, CommandeProduit, PaiementClient, Client,
                FactureFournisseur, PaiementFournisseur, Fournisseur,
                PlanLivraisonPrincipal, EtapeLivraison
            )
            from django.db.models.signals import post_save, post_delete
            from django.dispatch import receiver

            # Auto-créer les jours de la semaine si non présents
            jours = [
                ('0', 'Lundi'),
                ('1', 'Mardi'),
                ('2', 'Mercredi'),
                ('3', 'Jeudi'),
                ('4', 'Vendredi'),
                ('5', 'Samedi'),
                ('6', 'Dimanche'),
            ]
            for code, _ in jours:
                Jour.objects.get_or_create(code=code)

            # Recalcul solde client à chaque modification de commande
            @receiver([post_save, post_delete], sender=Commande)
            def maj_solde_apres_commande(sender, instance, **kwargs):
                if instance.client:
                    instance.client.recalculer_solde()

            # Recalcul solde client à chaque modification de paiement
            @receiver([post_save, post_delete], sender=PaiementClient)
            def maj_solde_apres_paiement(sender, instance, **kwargs):
                if instance.client:
                    instance.client.recalculer_solde()

            # Recalcul commande + solde client quand un produit de commande change
            @receiver([post_save, post_delete], sender=CommandeProduit)
            def maj_total_et_solde_apres_produit(sender, instance, **kwargs):
                if instance.commande:
                    instance.commande.calculer_total()
                    if instance.commande.client:
                        instance.commande.client.recalculer_solde()

            # Recalcul solde fournisseur à chaque modification de facture
            @receiver([post_save, post_delete], sender=FactureFournisseur)
            def maj_solde_fournisseur_apres_facture(sender, instance, **kwargs):
                if instance.fournisseur:
                    instance.fournisseur.recalculer_solde()

            # Recalcul solde fournisseur à chaque modification de paiement
            @receiver([post_save, post_delete], sender=PaiementFournisseur)
            def maj_solde_fournisseur_apres_paiement(sender, instance, **kwargs):
                if instance.fournisseur:
                    instance.fournisseur.recalculer_solde()

            # Synchronisation automatique des étapes de livraison
            plan, _ = PlanLivraisonPrincipal.objects.get_or_create(nom="Plan principal")

            clients_actuels_ids = set(plan.etapes.values_list('client_id', flat=True))
            clients_a_ajouter = Client.objects.filter(livre_par_nous=True).exclude(id__in=clients_actuels_ids)

            for client in clients_a_ajouter:
                EtapeLivraison.objects.create(plan=plan, client=client)

            clients_a_supprimer = Client.objects.filter(livre_par_nous=False, id__in=clients_actuels_ids)
            EtapeLivraison.objects.filter(plan=plan, client__in=clients_a_supprimer).delete()

        except (OperationalError, ProgrammingError):
            pass
