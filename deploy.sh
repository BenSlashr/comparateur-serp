#!/bin/bash

# Script de déploiement pour SERP Comparateur
# Ce script prépare l'application pour un déploiement dans un sous-dossier

echo "Préparation du déploiement de SERP Comparateur..."

# Vérifier que les variables d'environnement sont configurées
if [ ! -f .env ]; then
    echo "Erreur: Fichier .env non trouvé. Veuillez créer un fichier .env avec vos clés API."
    exit 1
fi

# Créer le dossier de build si nécessaire
mkdir -p build

# Copier les fichiers nécessaires
echo "Copie des fichiers dans le dossier build..."
cp -r static build/
cp -r templates build/
cp main.py build/
cp requirements.txt build/
cp .env build/

# Créer un fichier README pour le déploiement
cat > build/README.md << EOF
# SERP Comparateur - Instructions de déploiement

## Configuration pour un sous-dossier

Cette application est configurée pour fonctionner dans un sous-dossier. Lors du déploiement, assurez-vous de :

1. Configurer votre serveur web pour servir l'application depuis le sous-dossier souhaité
2. Si vous utilisez un proxy inverse (comme Nginx), configurez correctement le header \`X-Forwarded-Prefix\`

## Variables d'environnement

Assurez-vous que les variables d'environnement suivantes sont configurées :

- \`VALUESERP_API_KEY\` : Votre clé API ValueSERP
- \`GEMINI_API_KEY\` : Votre clé API Gemini

## Lancement de l'application

Pour lancer l'application avec Uvicorn :

\`\`\`bash
uvicorn main:app --host 0.0.0.0 --port 8000
\`\`\`

Pour spécifier un chemin de base (sous-dossier) :

\`\`\`bash
uvicorn main:app --host 0.0.0.0 --port 8000 --root-path /nom-outil
\`\`\`
EOF

# Créer un fichier de configuration pour Nginx
cat > build/nginx.conf.example << EOF
# Exemple de configuration Nginx pour SERP Comparateur dans un sous-dossier
# À inclure dans votre configuration Nginx

location /nom-outil/ {
    proxy_pass http://localhost:8000/;
    proxy_set_header Host \$host;
    proxy_set_header X-Real-IP \$remote_addr;
    proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto \$scheme;
    proxy_set_header X-Forwarded-Prefix /nom-outil;
}
EOF

echo "Préparation du déploiement terminée !"
echo "Les fichiers sont prêts dans le dossier 'build'."
echo "Consultez le fichier README.md pour les instructions de déploiement."
