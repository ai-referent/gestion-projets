# Skill : Réinitialisation des documents générés — Projet renovation_2026

Ce skill remet à zéro les documents produits (fiches navette, bons de paiement) tout en **préservant les factures PDF**.
Il permet de rejouer `/situations` sur une ardoise vierge.

---

## Étape 1 — Confirmation

Afficher le message suivant et demander confirmation avant de procéder :

```
⚠️  RÉINITIALISATION — Projet renovation_2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Les fichiers suivants vont être supprimés :
  - data/fiche_navette/navette_*.txt
  - data/fiche_navette/rejet_*.txt
  - data/bons_paiement/bon_*.txt
  - data/mails/mail_*.txt
  - data/vue_globale/recap_*.txt
  - data/vue_globale/budget_*.png
  - data/vue_globale/budget_*.xlsx

Les factures PDF dans data/factures/ seront préservées.

Confirmer ? (oui / non)
```

Si la réponse n'est pas "oui" → annuler et afficher "Réinitialisation annulée."

---

## Étape 2 — Suppression des fichiers générés

Supprimer tous les fichiers correspondant aux patterns suivants (en Python) :

```python
import pathlib

base = pathlib.Path("data")
patterns = [
    "fiche_navette/navette_*.txt",
    "fiche_navette/rejet_*.txt",
    "bons_paiement/bon_*.txt",
    "mails/mail_*.txt",
    "vue_globale/recap_*.txt",
    "vue_globale/budget_*.png",
    "vue_globale/budget_*.xlsx",
]
deleted = []
for pattern in patterns:
    for f in base.glob(pattern):
        f.unlink()
        deleted.append(str(f))
```

Afficher la liste des fichiers supprimés. Si aucun fichier n'existait, afficher "Aucun document à supprimer."

---

## Étape 3 — Récapitulatif

Afficher :

```
✓ Réinitialisation terminée.
  Fichiers supprimés : <N>
  Factures préservées : <liste des PDFs dans data/factures/>

Vous pouvez relancer /situations pour retraiter les factures.
```
