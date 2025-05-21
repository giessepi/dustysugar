from rest_framework import viewsets
from .models import Ingredient, Produit, Commande, Facture
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

# 🔁 Vue combinée : génère commandes + génère PDF automatiquement
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

    # 3. Génère la page de résumé
    total_global = sum(commande.total for commande in commandes)
    resume_html = render_to_string("commandes_resume.html", {
        'commandes': commandes,
        'date_livraison': tomorrow,
        'total_global': total_global
    })

    # 4. Génère les factures pages
    factures_html = ""
    for commande in commandes:
        facture = commande.facture
        html_facture = render_to_string("facture_template.html", {
            'facture': facture,
            'commande': commande,
        })
        factures_html += f"<div style='page-break-before: always;'>{html_facture}</div>"

    # 5. Fusionne résumé + factures
    pdf_commandes = HTML(string=resume_html + factures_html).write_pdf()

    # ➕ Générer les listes par catégorie
    fichiers = generer_pdfs_par_categorie(commandes, tomorrow)
    fichiers[f"commandes_{date_str}.pdf"] = pdf_commandes

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
