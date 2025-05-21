from django.urls import path, include
from rest_framework.routers import DefaultRouter
from . import views

router = DefaultRouter()
router.register('ingredients', views.IngredientViewSet)
router.register('produits', views.ProduitViewSet)
router.register('commandes', views.CommandeViewSet)
router.register('factures', views.FactureViewSet)

urlpatterns = [
    path('', include(router.urls)),
    path('admin/generer-commandes-journalieres/', views.generer_commandes_journalieres_view, name='generer_commandes'),
]
