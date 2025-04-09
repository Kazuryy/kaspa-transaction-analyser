# Kaspa Transaction Analyzer - Guide d'utilisation

## Description

Kaspa Transaction Analyzer est un outil d'analyse forensique des transactions blockchain pour le réseau Kaspa. Cette application web permet d'explorer visuellement les transferts de fonds, de détecter des patterns suspects et d'identifier les connexions entre différentes adresses.

## Fonctionnalités principales

- **Visualisation de graphe de transactions** - Explorez les flux de fonds entre adresses Kaspa
- **Détection de patterns suspects** - Identifiez automatiquement des schémas de transactions potentiellement liés à des activités illicites (layering, smurfing, cycling, etc.)
- **Identification d'exchanges** - Détectez les adresses appartenant à des exchanges connus ou potentiels
- **Recherche de connexions** - Trouvez des liens directs ou indirects entre deux adresses spécifiques
- **Filtres interactifs** - Affinez votre analyse selon différents critères

## Installation

### Prérequis

- Python 3.9+ 
- pip (gestionnaire de packages Python)

### Étapes d'installation

1. Clonez ce dépôt ou extrayez l'archive ZIP :
```bash
git clone https://github.com/votre-compte/kaspa-transaction-analyzer.git
cd kaspa-transaction-analyzer
```

2. Installez les dépendances requises :
```bash
pip install -r requirements.txt
```

## Utilisation

1. Démarrez le serveur web local :
```bash
python app.py
```

2. Ouvrez votre navigateur et accédez à : http://localhost:8000

3. Entrez une adresse Kaspa valide dans le formulaire et configurez les paramètres d'analyse

4. Cliquez sur "Analyser" pour générer la visualisation du graphe

### Analyse des transactions

- **Adresse Kaspa** - Entrez l'adresse Kaspa de départ
- **Profondeur d'analyse** - Nombre de niveaux de transactions à suivre (plus la profondeur est élevée, plus l'analyse sera complète mais prendra du temps)
- **Montant minimum** - Filtre les transactions inférieures à ce montant (en KAS)
- **Transactions max** - Limite le nombre total de transactions analysées
- **Identifier les exchanges** - Active la détection automatique des adresses d'exchanges

### Exploration du graphe

- Utilisez la souris pour déplacer et zoomer dans le graphe
- Cliquez sur une adresse pour la sélectionner et voir plus de détails
- Utilisez les filtres pour mettre en évidence certains types d'adresses
- Changez le layout pour visualiser les données différemment (force, radial, arbre)

### Recherche de connexions

Pour trouver des liens entre deux adresses :
1. Entrez l'adresse source et l'adresse cible dans le panneau "Recherche de chemin"
2. Configurez la profondeur maximale et le montant minimum
3. Cliquez sur "Chercher un chemin"
4. Le système analysera s'il existe un chemin de transactions entre ces deux adresses

## Structure du projet

```
kaspa-transaction-analyzer/
│
├── app.py                # Point d'entrée de l'application
├── requirements.txt      # Dépendances Python
│
├── kaspa/                # Module d'accès à l'API Kaspa
│   ├── __init__.py
│   └── client.py         # Client API Kaspa
│
├── graph/                # Module d'analyse de graphe
│   ├── __init__.py
│   ├── builder.py        # Construction du graphe
│   ├── analysis.py       # Analyse et détection de patterns
│   └── path_finder.py    # Recherche de chemins entre adresses
│
└── static/               # Interface utilisateur
    ├── index.html        # Page principale
    ├── css/
    │   └── style.css     # Styles CSS
    └── js/
        ├── graph.js      # Visualisation D3.js
        ├── api.js        # Communication avec le backend
        ├── controls.js   # Contrôleurs d'interface
        └── path-finder.js # Recherche de chemins
```

## Exemples d'adresses pour tester

- `kaspa:qz0c4pc68r2dd76uvhvh6l7lst5750kgc8eqv7kuf73hjkf95aeu7uy9j5aat` (Binance)
- `kaspa:qzm47s5pt54k48devr5a2kct3c4wzm0d28u2kjtexkw5xvsce6ftuzy2spg3j` (KuCoin)
- `kaspa:qp2hnzdnzpm4m9l86tufk73yz0ew6av6vv0hc52gqrq9h3w6swafw80g06qmc` (OKX)

## Limites connues

- L'application dépend de l'API Kaspa publique (https://api.kaspa.org) qui peut présenter des limitations ou des données incomplètes
- Les analyses très profondes (>3 niveaux) peuvent prendre un temps considérable et générer des graphes complexes
- Certaines adresses à très fort volume peuvent ralentir l'analyse

## Dépannage

Si vous rencontrez des erreurs :

1. **Erreur 500 lors de l'analyse** - Essayez avec une adresse différente ou réduisez la profondeur d'analyse
2. **Aucun nœud affiché** - Vérifiez que l'adresse est valide et possède des transactions
3. **Problèmes de chargement des fichiers JavaScript** - Assurez-vous que tous les fichiers sont dans les bons dossiers

## Contribution

Les contributions sont les bienvenues ! N'hésitez pas à ouvrir une issue ou soumettre une pull request pour améliorer cet outil.
