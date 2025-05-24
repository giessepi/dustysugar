from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone

class Migration(migrations.Migration):

    dependencies = [
        ('gestion', '0001_initial'),  # adapte si ce n'est pas la dernière
    ]

    operations = [
        migrations.CreateModel(
            name='FactureFournisseurCloturee',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('date_cloture', models.DateTimeField(default=django.utils.timezone.now)),
                ('montant_total_factures', models.FloatField()),
                ('montant_total_paye', models.FloatField()),
                ('description', models.TextField(blank=True, null=True)),
                ('factures_json', models.JSONField(blank=True, null=True)),
                ('paiements_json', models.JSONField(blank=True, null=True)),
                ('fournisseur', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='factures_cloturees', to='gestion.fournisseur')),
            ],
        ),
    ]
