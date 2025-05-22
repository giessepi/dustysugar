from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

class GestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestion'

    def ready(self):
        try:
            from .models import Jour, Commande, PaiementClient
            from django.db.models.signals import post_save, post_delete
            from django.dispatch import receiver

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

            @receiver([post_save, post_delete], sender=Commande)
            def maj_solde_apres_commande(sender, instance, **kwargs):
                if instance.client:
                    instance.client.recalculer_solde()

            @receiver([post_save, post_delete], sender=PaiementClient)
            def maj_solde_apres_paiement(sender, instance, **kwargs):
                if instance.client:
                    instance.client.recalculer_solde()

        except (OperationalError, ProgrammingError):
            pass
