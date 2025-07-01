from gestion.models import Client, CommandeProduit
from django.db.models import Prefetch

clients_stables = []

clients = Client.objects.all()

for client in clients:
    commandes = client.commandes.prefetch_related(
        Prefetch('commande_produits', queryset=CommandeProduit.objects.select_related('produit'))
    ).order_by('date_livraison')

    if commandes.count() < 2:
        continue  # pas assez de commandes

    signatures = set()

    for commande in commandes:
        produits = sorted([
            (cp.produit_id, float(cp.quantite)) for cp in commande.commande_produits.all()
        ])
        signatures.add(tuple(produits))

    if len(signatures) == 1:
        clients_stables.append({
            'client': client,
            'frequence': client.frequence_paiement,
            'nb_commandes': commandes.count()
        })

print("📋 Clients avec commandes stables :\n")
for c in clients_stables:
    print(f"✔️ {c['client'].nom} ({c['frequence']}) - {c['nb_commandes']} commandes")
