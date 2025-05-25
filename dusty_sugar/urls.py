from django.urls import path, include
from gestion.admin import admin_site  # ton admin personnalisé

urlpatterns = [
    path('admin/', admin_site.urls),         # ✅ active l’interface regroupée
    path('api/', include('gestion.urls')),   # ✅ conserve les API et commandes journalières
]
