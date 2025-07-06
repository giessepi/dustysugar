#!/bin/bash

echo "🔐 Déploiement sécurisé lancé..."

# Vérifie que la base est ignorée
if grep -q "db.sqlite3" .gitignore; then
  echo "✅ db.sqlite3 est bien ignorée par Git"
else
  echo "❌ ERREUR : db.sqlite3 n'est pas ignorée. Abandon du déploiement."
  exit 1
fi

echo "📦 Installation des dépendances Python"
pip install -r requirements.txt

echo "🛠️ Application des migrations"
python manage.py migrate --noinput

echo "✅ Déploiement terminé avec succès 🎉"
