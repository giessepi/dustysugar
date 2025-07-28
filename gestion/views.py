from rest_framework import viewsets
from .models import Ingredient, Produit, Commande, Facture, EtapeLivraison, CommandeModele
from .serializers import IngredientSerializer, ProduitSerializer, CommandeSerializer, FactureSerializer

from django.core.management import call_command
from django.contrib.admin.views.decorators import staff_member_required
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from django.utils.timezone import now, timedelta
from collections import defaultdict
import os
from django.conf import settings
import zipfile
import io
import math


class IngredientViewSet(viewsets.ModelViewSet):
    queryset = Ingredient.objects.all()
    serializer_class = IngredientSerializer

class ProduitViewSet(viewsets.ModelViewSet):
    queryset = Produit.objects.all()
    serializer_class = ProduitSerializer

class CommandeViewSet(viewsets.ModelViewSet):
    queryset = Commande.objects.all()
    serializer_class = CommandeSerializer

class FactureViewSet(viewsets.ModelViewSet):
    queryset = Facture.objects.all()
    serializer_class = FactureSerializer


@staff_member_required
def generer_commandes_journalieres_view(request):
    # 1. Génère les commandes pour demain
    call_command('generer_commandes_journalieres')

    # 2. Prépare les commandes de demain
    tomorrow = now().date() + timedelta(days=1)
    date_str = tomorrow.strftime("%Y-%m-%d")
    commandes = Commande.objects.filter(date_livraison=tomorrow)

    # 🔁 Recalcule les totaux pour être sûr
    for commande in commandes:
        commande.calculer_total()

    # 3. Génère la page de résumé (PDF)
    total_global = sum(commande.total for commande in commandes)
    resume_html = render_to_string("commandes_resume.html", {
        'commandes': commandes,
        'date_livraison': tomorrow,
        'total_global': total_global
    })
    pdf_resume = HTML(string=resume_html).write_pdf()

    # 4. Génère les listes par catégorie
    fichiers = generer_pdfs_par_categorie(commandes, tomorrow)
    fichiers[f"commandes_{date_str}.pdf"] = pdf_resume

    # 5. Génère la liste de chargement livraison
    fichiers[f"liste_chargement_{date_str}.pdf"] = generer_pdf_liste_chargement(tomorrow)

    # 6. Retourne un ZIP contenant tout
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, 'w') as zf:
        for filename, content in fichiers.items():
            zf.writestr(filename, content)

    zip_buffer.seek(0)
    response = HttpResponse(zip_buffer.getvalue(), content_type='application/zip')
    response['Content-Disposition'] = f'attachment; filename=livraison_{date_str}.zip'
    return response


def generer_pdfs_par_categorie(commandes, date_livraison):
    regroupement = defaultdict(lambda: defaultdict(int))

    for commande in commandes:
        for cp in commande.commande_produits.all():
            cat = cp.produit.categorie
            regroupement[cat][cp.produit] += cp.quantite

    fichiers = {}
    for categorie, produits_dict in regroupement.items():
        produits = [{'nom': p.nom, 'quantite': q} for p, q in produits_dict.items()]
        html = render_to_string("liste_preparation_categorie.html", {
            'categorie': categorie.title(),
            'date_livraison': date_livraison,
            'produits': produits
        })
        pdf_bytes = HTML(string=html).write_pdf()
        fichiers[f"{categorie}_{date_livraison.strftime('%Y-%m-%d')}.pdf"] = pdf_bytes

    return fichiers


def generer_pdf_liste_chargement(date_livraison):
    etapes = EtapeLivraison.objects.filter(actif=True).order_by('ordre').select_related('client')
    commandes_par_client = []

    for etape in etapes:
        client = etape.client

        if not client.livre_par_nous:
            continue

        commande = Commande.objects.filter(client=client, date_livraison=date_livraison).first()
        if not commande:
            continue

        produits = commande.commande_produits.select_related('produit')
        produits_filtrés = [cp for cp in produits if cp.produit.categorie in ['croissanterie', 'sale']]
        total_articles = sum(cp.quantite for cp in produits_filtrés)

        mode_livraison = client.mode_livraison

        ligne = {
            'client': client.nom,
            'type_livraison': mode_livraison,
            'total_articles': total_articles,
            'nb_bacs': math.ceil(total_articles / 25) if mode_livraison == 'bac' else '',
            'nb_paquets': math.ceil(total_articles / 10) if mode_livraison == 'paquet' else '',
            'produits': [
                {
                    'nom': cp.produit.nom,
                    'quantite': cp.quantite,
                    'type': mode_livraison  # on injecte le type ici
                }
                for cp in produits_filtrés
            ]
        }

        commandes_par_client.append(ligne)

    total_bacs = sum(l['nb_bacs'] for l in commandes_par_client if isinstance(l['nb_bacs'], int))
    total_paquets = sum(l['nb_paquets'] for l in commandes_par_client if isinstance(l['nb_paquets'], int))

    # ⬇️ Filtrage par type
    clients_avec_bacs = [l for l in commandes_par_client if isinstance(l['nb_bacs'], int)]
    clients_avec_paquets = [l for l in commandes_par_client if isinstance(l['nb_paquets'], int)]

    html = render_to_string('liste_chargement_template.html', {
        'commandes_par_client': commandes_par_client,
        'clients_avec_bacs': clients_avec_bacs,
        'clients_avec_paquets': clients_avec_paquets,
        'date_livraison': date_livraison,
        'date_generation': now().strftime("%d/%m/%Y %H:%M"),
        'total_bacs': total_bacs,
        'total_paquets': total_paquets,
    })
    return HTML(string=html).write_pdf()
