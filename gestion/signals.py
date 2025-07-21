from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from .models import Commande, CommandeProduit, PaiementClient

@receiver([post_save, post_delete], sender=CommandeProduit)
def update_total_commande(sender, instance, **kwargs):
    if instance.commande:
        instance.commande.calculer_total()
        if instance.commande.client:
            instance.commande.client.recalculer_solde()

@receiver([post_save, post_delete], sender=Commande)
def update_client_solde_on_commande_change(sender, instance, **kwargs):
    if instance.client:
        instance.client.recalculer_solde()

@receiver([post_save, post_delete], sender=PaiementClient)
def update_client_solde_on_paiement(sender, instance, **kwargs):
    if instance.client:
        instance.client.recalculer_solde()

@receiver(post_save, sender=Client)
def maj_etape_livraison(sender, instance, **kwargs):
    plan, _ = PlanLivraison.objects.get_or_create(nom="Plan principal")

    etape, created = EtapeLivraison.objects.get_or_create(client=instance, defaults={
        'plan': plan,
        'ordre': (plan.etapes.aggregate(max_ordre=models.Max('ordre'))['max_ordre'] or 0) + 10,
        'actif': instance.livre_par_nous,
    })

    if not created:
        # Ne jamais changer l’ordre existant, juste l’état actif
        if etape.actif != instance.livre_par_nous:
            etape.actif = instance.livre_par_nous
            etape.save()
