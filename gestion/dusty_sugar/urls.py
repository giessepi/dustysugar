from django.contrib import admin
from django.urls import path, include

urlpatterns = [
    path('admin/', admin.site.urls),  # URL pour l'interface admin
    path('api/', include('gestion.urls')),  # Inclure les URLs de gestion sous "/api/"
]
