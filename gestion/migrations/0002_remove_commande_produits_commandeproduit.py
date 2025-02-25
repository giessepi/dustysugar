# Generated by Django 5.1.4 on 2025-01-19 01:43

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0001_initial'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='commande',
            name='produits',
        ),
        migrations.CreateModel(
            name='CommandeProduit',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantite', models.PositiveIntegerField(default=1)),
                ('commande', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='commande_produits', to='gestion.commande')),
                ('produit', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='gestion.produit')),
            ],
        ),
    ]
