# Skill : Ajout d'une facture — Projet renovation_2026

Ce skill guide la saisie d'une nouvelle facture, crée le PDF Factur-X correspondant et l'ajoute dans `data/factures/`.
Si le prestataire est nouveau, il est ajouté dans `data/prestataires/prestataires.csv` et `data/budget/budget_lot_prestataire.csv`.

---

## Étape 1 — Collecte des informations

Poser les questions suivantes une par une (attendre la réponse avant de passer à la suivante) :

1. **Numéro de facture** — format recommandé : `FAC-AAAA-NNN` (ex: FAC-2026-004)
2. **Date de la facture** — format JJ/MM/AAAA ou texte libre (ex: 20 avril 2026)
3. **Nom de la société émettrice**
4. **Identifiant de la société** — code court en majuscules (ex: REVE001). Si la société est déjà dans `data/prestataires/prestataires.csv`, utiliser son identifiant existant.
5. **Lot concerné** — doit correspondre à un `id_lot` existant dans `data/budget/budget_lot_prestataire.csv`. Afficher la liste des lots disponibles (colonne `id_lot`) avant de poser la question.
6. **Objet des travaux** — description courte (ex: Pose isolation combles)
7. **Montant HT** — en euros (ex: 8000)
8. **Taux de TVA** — en % (défaut : 20)
9. **Adresse de la société** (optionnel — laisser vide pour passer)
10. **Code postal et ville** (optionnel — laisser vide pour passer)
11. **SIRET** (optionnel — laisser vide pour passer)

Calculer automatiquement :
- Montant TVA = Montant HT × (taux TVA / 100)
- Montant TTC = Montant HT + Montant TVA

Afficher un récapitulatif et demander confirmation avant de créer le PDF.

---

## Étape 2 — Vérification du prestataire

Lire `data/prestataires/prestataires.csv` (colonnes : `id_prestataire`, `nom_prestataire`, `adresse_prestataire`, `mail_prestataire`, `siret`).

- Si l'`id_prestataire` existe déjà → vérifier que le lot correspond dans `budget_lot_prestataire.csv`. Si le lot diffère, signaler l'incohérence et demander confirmation.
- Si l'`id_prestataire` est nouveau → ajouter une ligne dans `prestataires.csv` :
  ```
  <id_prestataire>,<nom>,<adresse ou vide>,<mail ou vide>,<siret ou vide>
  ```
  Puis ajouter une ligne dans `data/budget/budget_lot_prestataire.csv` :
  ```
  <id_prestataire>,<id_lot>,0,0,0
  ```
  Signaler : "Nouveau prestataire ajouté : `<nom>` (`<id>`) sur le lot `<lot>`. Budget initialisé à 0 — à mettre à jour manuellement dans `budget_lot_prestataire.csv`."

---

## Étape 3 — Génération du PDF Factur-X

Construire le dict JSON et appeler le script :

```python
import json, subprocess

inv = {
    "filename": "<NUMERO>.pdf",          # ex: FAC-2026-004.pdf
    "id": "<NUMERO>",                    # ex: FAC-2026-004
    "date": "<YYYYMMDD>",                # convertir JJ/MM/AAAA → AAAAMMJJ
    "lot": "<ID_LOT>",
    "seller": {
        "name": "<NOM SOCIETE>",
        "siret": "<SIRET>",              # omettre la clé si non fourni
        "address": "<ADRESSE>",          # omettre si non fourni
        "postcode": "<CODE POSTAL>",     # omettre si non fourni
        "city": "<VILLE>",               # omettre si non fourni
        "country": "FR",
    },
    "lines": [
        {
            "id": "1",
            "desc": "<OBJET TRAVAUX>",
            "qty": 1.0,
            "unit_price": <MONTANT_HT>,
            "vat_rate": <TAUX_TVA>,
            "total_ht": <MONTANT_HT>,
        }
    ],
    "total_ht": <MONTANT_HT>,
    "total_vat": <MONTANT_TVA>,
    "total_ttc": <MONTANT_TTC>,
}

result = subprocess.run(
    ["python3", "scripts/generate_factures.py", "--create", json.dumps(inv)],
    capture_output=True, text=True
)
print(result.stdout.strip())  # affiche le chemin du PDF créé
```

Le script génère un PDF **Factur-X BASIC** (PDF 1.7 + XML CII embarqué).
La date d'échéance (`due_date`) est calculée automatiquement à date + 30 jours.

---

## Étape 4 — Confirmation finale

Afficher :

```
✓ Facture créée : data/factures/<numero>.pdf
  Société  : <nom>
  Lot      : <lot>
  TTC      : <montant> EUR

Voulez-vous lancer /situations maintenant pour traiter cette facture ? (oui / non)
```

Si oui → exécuter le skill `/situations`.
