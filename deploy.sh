#!/bin/bash

echo "🔐 Déploiement sécurisé lancé..."

# Vérifie que db.sqlite3 est bien ignorée par Git
if git check-ignore -q db.sqlite3; then
  echo "✅ db.sqlite3 est bien ignorée par Git"
else
  echo "❌ ERREUR : db.sqlite3 n'est pas ignorée. Abandon du déploiement."
  exit 1
fi

# Installation des dépendances
echo "📦 Installation des dépendances"
pip install -r requirements.txt

# Sauvegarde de la base de données si elle existe
if [ -f db.sqlite3 ]; then
  BACKUP_NAME="backup_$(date +%Y%m%d_%H%M%S).sqlite3"
  cp db.sqlite3 "$BACKUP_NAME"
  echo "💾 Sauvegarde créée : $BACKUP_NAME"
fi

# Application des migrations Django
echo "🛠️ Application des migrations"
python manage.py migrate --noinput

echo "✅ Déploiement terminé avec succès 🎉"
