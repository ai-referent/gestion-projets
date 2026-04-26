# Skill : Traitement des situations (factures) — Projet renovation_2026

Ce skill traite toutes les **nouvelles** factures dans `data/factures/` pour le compte de **RenovBat** (MOE).
Pour chaque nouvelle facture (non encore traitée), il effectue un pré-check budgétaire, puis met à jour le fichier Excel du lot-prestataire dans `data/navettes_et_bons/` en ajoutant une feuille avec fiche navette et bon de paiement.
Les mails de transmission (RenovBat → IMMOSOCIAL_69) sont simulés dans `data/navettes_et_bons/mails/`.

---

## Exécution

Depuis la racine du projet, lancer les deux scripts dans l'ordre :

### Étape 1 — Traiter les factures

```bash
python3 scripts/process_situations.py
```

Pour chaque PDF dans `data/factures/` :
- Parse le PDF (XML embarqué ou flux texte)
- Identifie le prestataire par SIRET en priorité, sinon par nom approché
- Si non trouvé → **REJET** : `"Société non référencée sur le projet"`
- Vérifie le budget du lot ; si dépassement → **REJET** avec motif
- Appelle `scripts/generate_navette.py` pour écrire la feuille Excel (fiche navette + bon de paiement)
- Génère le mail de transmission dans `data/navettes_et_bons/mails/` (si approuvée)

Produit `data/vue_globale/.current_session.json` pour l'étape suivante.

### Étape 2 — Générer le récapitulatif

```bash
python3 scripts/generate_recap.py
```

Produit dans `data/vue_globale/` :
- `recap_<AAAAMMJJ>.txt` — tableau texte + consommation par lot
- `budget_<AAAAMMJJ>.png` — graphique horizontal coloré
- `budget_<AAAAMMJJ>.xlsx` — classeur Excel avec onglets Factures et Budget

### Étape 3 — Afficher le résultat

Lire et afficher le contenu de `data/vue_globale/recap_<AAAAMMJJ>.txt`
(`AAAAMMJJ` = date du jour depuis `currentDate`).

---

## Règles

- Ne pas retraiter une facture dont la feuille existe déjà dans le fichier Excel du lot.
- La source de vérité des situations traitées est les fichiers Excel dans `data/navettes_et_bons/`.
- La date du jour est dans le contexte système (`currentDate`).
- Les PDFs dans `data/factures/` peuvent être régénérés avec `python3 scripts/generate_factures.py`.
