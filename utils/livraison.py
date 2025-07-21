import math
from django.template.loader import render_to_string
from weasyprint import HTML
import os
from django.conf import settings
from datetime import datetime

def generer_pdf_liste_chargement(commandes_par_client, date_livraison):
    now_str = datetime.now().strftime('%d/%m/%Y %H:%M')
    context = {
        'commandes_par_client': commandes_par_client,
        'date_livraison': date_livraison,
        'date_generation': now_str,
    }

    html = render_to_string('liste_chargement_template.html', context)
    dossier_pdf = os.path.join(settings.BASE_DIR, 'exports')
    os.makedirs(dossier_pdf, exist_ok=True)

    chemin_pdf = os.path.join(dossier_pdf, f'liste_chargement_{date_livraison.strftime("%Y%m%d")}.pdf')
    HTML(string=html).write_pdf(chemin_pdf)

    return chemin_pdf
