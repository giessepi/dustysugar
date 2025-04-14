from django.contrib import admin
from django.urls import path, include

from django.conf import settings
from django.conf.urls.static import static
import os

urlpatterns = [
    path('admin/', admin.site.urls),  # Interface admin
    path('api/', include('gestion.urls')),  # API de l'app gestion
]

# 👇 Permet d'accéder aux PDF via http://127.0.0.1:8000/factures/Facture_4.pdf
urlpatterns += static('/factures/', document_root=os.path.join(settings.BASE_DIR, 'factures'))
