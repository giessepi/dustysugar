# dustysugar/urls.py
from django.contrib import admin
from django.urls import path, include
from gestion.admin import admin_site

urlpatterns = [
    path("admin/", admin_site.urls),              # ✅ TON ADMIN PERSONNALISÉ
    path("api/", include("gestion.urls")),        # ✅ TON API DRF
]
