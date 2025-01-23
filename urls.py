# urls.py dans dusty_sugar/dusty_sugar

from django.contrib import admin
from django.http import HttpResponse
from django.urls import path, include

urlpatterns = [
    path('', lambda request: HttpResponse("Bienvenue sur Dusty Sugar!"), name='home'),  # Page d'accueil
    path('admin/', admin.site.urls),  # Interface admin
    path('api/', include('gestion.urls')),  # Inclure les URLs de gestion sous "/api/"
]
