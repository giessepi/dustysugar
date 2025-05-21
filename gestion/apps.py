from django.apps import AppConfig
from django.db.utils import OperationalError, ProgrammingError

class GestionConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'gestion'

    def ready(self):
        try:
            from .models import Jour
            jours = [
                ('0', 'Lundi'),
                ('1', 'Mardi'),
                ('2', 'Mercredi'),
                ('3', 'Jeudi'),
                ('4', 'Vendredi'),
                ('5', 'Samedi'),
                ('6', 'Dimanche'),
            ]
            for code, _ in jours:
                Jour.objects.get_or_create(code=code)
        except (OperationalError, ProgrammingError):
            # La base n'est peut-être pas encore prête (migrations)
            pass
