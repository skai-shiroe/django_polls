# God Eyes - Sondages Interactifs en Temps Réel

**God Eyes** est une plateforme de sondages moderne et performante conçue avec Django. Elle permet de créer, diffuser et suivre des sondages en temps réel grâce aux WebSockets.

## Fonctionnalités Clés

- **Temps Réel Intégral** : Les résultats se mettent à jour instantanément sans rafraîchissement de page via Django Channels (WebSockets).
- **Supports Multi-Sondages** :
  - Choix unique (avec Pie/Doughnut Chart)
  - Choix multiples (avec Bar Chart)
  - Échelle de notation (1 à 5 étoiles avec Radial Gauge)
  - Réponses textuelles libres (Flux de messages dynamique)
- **Interface Professionnelle** : Design épuré "Simple & Pro" basé sur la police Inter et Tailwind CSS.
- **Mode Sombre** : Support complet du mode sombre avec détection automatique et bascule manuelle.
- **Administration Simplifiée** : Interface de création de sondages dédiée pour les administrateurs (Staff).
- **Sécurité** : Authentification complète et gestion des droits d'accès.

## Stack Technique

- **Backend** : Django 5+, Django Channels 4+
- **Serveur ASGI** : Daphne
- **Base de données** : SQLite (par défaut)
- **Frontend** : Tailwind CSS, Alpine.js, Chart.js
- **Temps Réel** : WebSockets via `InMemoryChannelLayer`

## Installation

1. **Clonage du dépôt** :
   ```bash
   git clone <url-du-depot>
   cd django_polls
   ```

2. **Environnement Virtuel** :
   ```bash
   python -m venv venv
   source venv/Scripts/activate  # Windows
   # ou
   source venv/bin/activate      # Linux/macOS
   ```

3. **Installation des dépendances** :
   ```bash
   pip install -r requirements.txt
   ```

4. **Migrations et Super-utilisateur** :
   ```bash
   python manage.py migrate
   python manage.py createsuperuser
   ```

5. **Lancement du serveur** :
   ```bash
   python manage.py runserver
   ```

## Utilisation

- **Utilisateurs** : Peuvent s'inscrire, se connecter et participer aux sondages.
- **Administrateurs (Staff)** : Ont accès au bouton "Créer un sondage" dans la barre de navigation pour concevoir de nouveaux questionnaires à l'adresse `/create/`.
- **Résultats** : Accessibles à tout moment pour suivre les tendances en direct.

##  Configuration

Le projet utilise `InMemoryChannelLayer` pour simplifier le développement local. Pour une mise en production avec plusieurs serveurs, il est recommandé de passer à `RedisChannelLayer`.
