# SERP Comparateur

Un outil de comparaison de SERP pour déterminer si vous devez créer une ou plusieurs pages pour différents mots-clés SEO.

## Fonctionnalités

- Comparaison de jusqu'à 4 mots-clés différents
- Analyse des URL communes entre les résultats de recherche
- Recommandation basée sur le score de similarité
- Filtres avancés (pays, localité, moteur de recherche, nombre de résultats, langue, appareil)
- Affichage des SERP côte à côte pour une comparaison facile
- Console de logs pour suivre les opérations

## Prérequis

- Python 3.8+
- Compte ValueSERP avec une clé API valide

## Installation

1. Clonez ce dépôt
2. Installez les dépendances:

```bash
pip install -r requirements.txt
```

3. Configurez votre clé API ValueSERP dans le fichier `.env`:

```
VALUESERP_API_KEY=votre_clé_api_ici
```

## Utilisation

1. Démarrez le serveur:

```bash
uvicorn main:app --reload
```

2. Accédez à l'application dans votre navigateur à l'adresse `http://localhost:8000`

3. Entrez au moins un mot-clé (jusqu'à 4) et configurez vos filtres

4. Cliquez sur "Comparer SERPs" pour lancer l'analyse

## Interprétation des résultats

- **Score de similarité**: Pourcentage d'URL communes entre les différents mots-clés
- **URLs communes**: Nombre d'URL apparaissant dans plusieurs résultats de recherche
- **URLs totales**: Nombre total d'URL uniques trouvées dans tous les résultats

La recommandation est basée sur le score de similarité:
- **Score élevé (>70%)**: Créer une seule page pour tous les mots-clés
- **Score moyen (40-70%)**: Créer une page avec des sections distinctes pour chaque mot-clé
- **Score faible (<40%)**: Créer des pages séparées pour chaque mot-clé

## Notes techniques

- L'application utilise FastAPI pour le backend et JavaScript vanilla pour le frontend
- Les résultats de recherche sont obtenus via l'API ValueSERP
- Les URL communes sont mises en évidence dans les résultats avec une bordure verte
