# Skill : Réinitialisation des documents générés — Projet renovation_2026

Ce skill remet à zéro les documents produits (fichiers Excel navettes/bons, mails, rapports) tout en **préservant les factures PDF**.
Il permet de rejouer `/situations` sur une ardoise vierge.

---

## Étape 1 — Confirmation

Afficher le message suivant et demander confirmation avant de procéder :

```
⚠️  RÉINITIALISATION — Projet renovation_2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Les fichiers suivants vont être supprimés :
  - data/navettes_et_bons/*.xlsx        (fichiers Excel lot-prestataire)
  - data/navettes_et_bons/mails/mail_*.txt
  - data/navettes_et_bons/rejets/rejet_*.txt
  - data/vue_globale/recap_*.txt
  - data/vue_globale/budget_*.png
  - data/vue_globale/budget_*.xlsx
  - data/tmp/.current_session.json

Les factures PDF dans data/factures/ seront préservées.

Confirmer ? (oui / non)
```

Si la réponse n'est pas "oui" → annuler et afficher "Réinitialisation annulée."

---

## Étape 2 — Suppression des fichiers générés

```python
import pathlib

base = pathlib.Path("data")
patterns = [
    "navettes_et_bons/*.xlsx",
    "navettes_et_bons/mails/mail_*.txt",
    "navettes_et_bons/rejets/rejet_*.txt",
    "vue_globale/recap_*.txt",
    "vue_globale/budget_*.png",
    "vue_globale/budget_*.xlsx",
    "tmp/.current_session.json",
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
