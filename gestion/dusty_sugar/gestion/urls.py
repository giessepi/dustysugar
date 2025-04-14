from django.urls import path, include
from rest_framework.routers import DefaultRouter
from .views import IngredientViewSet, ProduitViewSet, CommandeViewSet, FactureViewSet, telecharger_facture

router = DefaultRouter()
router.register(r'ingredients', IngredientViewSet)
router.register(r'produits', ProduitViewSet)
router.register(r'commandes', CommandeViewSet)
router.register(r'factures', FactureViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('factures/<int:pk>/pdf/', telecharger_facture, name='telecharger_facture'),
]
