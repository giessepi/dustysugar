from django.http import HttpResponse
from django.urls import path

urlpatterns = [
    path('', lambda request: HttpResponse("Bienvenue sur Dusty Sugar!"), name='home'),
    path('admin/', admin.site.urls),
    # Ajoutez vos autres routes ici
]
