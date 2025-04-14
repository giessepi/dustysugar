from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
import os

urlpatterns = [
    path('admin/', admin.site.urls),
    path('api/', include('gestion.urls')),
]

# Pour servir les fichiers PDF statiques
urlpatterns += static('/factures/', document_root=os.path.join(settings.BASE_DIR, 'factures'))
