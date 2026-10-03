# Gestionnaire de tâches

Une application de gestion de tâches avec interface Fluent (Windows 11),
basée sur PySide6 et qfluentwidgets.

## Fonctionnalités

- Tableau de bord avec statistiques et taux d'achèvement
- Listes filtrées : toutes, en cours, en retard, terminées
- Recherche et tri (manuel, échéance, priorité, date de création)
- Glisser-déposer pour réordonner les tâches
- Thème clair / sombre / auto

## Installation

```bash
pip install -r requirements.txt
```

## Lancement

```bash
python main.py
```

## Fichiers

- `main.py` — fenêtre principale et thème
- `models.py` — modèle de tâche et stockage
- `pages.py` — tableau de bord et listes de tâches
- `task_card.py` — carte de tâche
- `task_dialog.py` — formulaire d'édition
- `tasks.json` — données des tâches
- `config.json` — préférences (thème)

(je vais publier bientot la premiere release apres quelque fix et features.)
