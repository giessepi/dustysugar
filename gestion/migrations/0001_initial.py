from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name='Jour',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('code', models.CharField(choices=[('0', 'Lundi'), ('1', 'Mardi'), ('2', 'Mercredi'), ('3', 'Jeudi'),
                                                   ('4', 'Vendredi'), ('5', 'Samedi'), ('6', 'Dimanche')],
                                          max_length=1, unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Ingredient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100)),
                ('quantite_stock', models.FloatField()),
                ('unite', models.CharField(max_length=20)),
                ('seuil_minimum', models.FloatField()),
            ],
        ),
        migrations.CreateModel(
            name='Produit',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100)),
                ('prix', models.FloatField()),
                ('categorie', models.CharField(choices=[('croissanterie', 'Croissanterie'), ('sale', 'Salé'),
                                                        ('patisserie', 'Pâtisserie')], default='croissanterie',
                                               max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='ProduitIngredient',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('quantite', models.FloatField()),
                ('ingredient', models.ForeignKey(on_delete=models.CASCADE, to='gestion.Ingredient')),
                ('produit', models.ForeignKey(on_delete=models.CASCADE, to='gestion.Produit')),
            ],
        ),
        migrations.CreateModel(
            name='Client',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('nom', models.CharField(max_length=100)),
                ('email', models.EmailField(blank=True, null=True, unique=True)),
                ('telephone', models.CharField(blank=True, max_length=15, null=True)),
                ('adresse', models.TextField(blank=True, null=True)),
                ('solde', models.FloatField(default=0.0)),
                ('frequence_paiement', models.CharField(choices=[('journalier', 'Journalier'),
                                                                 ('hebdomadaire', 'Hebdomadaire'),
                                                                 ('mensuel', 'Mensuel')],
                                                        default='journalier', max_length=20)),
            ],
        ),
        # Tu peux compléter à partir d'ici avec les autres modèles si besoin
    ]
