# Skill : Traitement des situations (factures) — Projet renovation_2026

Ce skill traite toutes les factures présentes dans `data/factures/` pour le compte de **RenovBat**.
Pour chaque facture, il effectue un pré-check budgétaire puis génère une fiche navette et un bon de paiement.

---

## Étape 1 — Lire les données de référence

Charge les fichiers suivants :

- `data/prestataires/prestataires.csv` → colonnes : `identifiant`, `nom`, `lot`
- `data/budget/budget_global.csv` → colonnes : `nom_du_lot`, `montant_global`
- `data/budget/budget_prestataire.csv` → colonnes : `id_prestataire`, `id_lot`, `montant_max`

Puis liste tous les fichiers `*.pdf` dans `data/factures/`.

---

## Étape 2 — Parser chaque facture PDF

Pour chaque PDF, extrais les champs depuis les streams PDF (chaînes entre parenthèses dans les lignes `Tj`) :

```python
import re, pathlib

def parse_facture(path):
    data = pathlib.Path(path).read_bytes()
    streams = re.findall(b'stream\n(.*?)\nendstream', data, re.DOTALL)
    texts = []
    for s in streams:
        for line in s.decode('latin-1').split('\n'):
            m = re.search(r'\(([^)]+)\)', line)
            if m:
                texts.append(m.group(1).strip())
    return texts
```

Cherche dans `texts` :
- Numéro de facture : premier élément contenant `FAC-`
- Date : élément contenant `Date`
- Société : premier texte > 5 caractères, pas une adresse ni un SIRET
- Montant TTC : élément contenant `TOTAL TTC`, extraire le nombre

---

## Étape 3 — Pré-check

**a. Vérification du prestataire**
- Cherche l'émetteur dans `prestataires.csv` (comparaison souple : insensible à la casse, sans accents).
- Si absent → **REJET** : "Société non référencée sur le projet".

**b. Identification du lot**
- Récupère le `lot` du prestataire dans `prestataires.csv`.

**c. Budget global du lot**
- Somme des montants des `navette_*.txt` existants pour ce lot + montant en cours.
- Si total > `montant_global` → **REJET** : "Dépassement du budget lot (global=X€, engagé=Y€, facture=Z€)".

**d. Budget prestataire**
- Somme des montants des `navette_*.txt` existants pour ce prestataire + montant en cours.
- Si total > `montant_max` → **REJET** : "Dépassement du budget prestataire (max=X€, engagé=Y€, facture=Z€)".

Pour lire les montants des navettes existantes, chercher la ligne `Montant TTC` dans chaque `navette_*.txt` et normaliser : supprimer les espaces, remplacer la virgule par un point.

---

## Étape 4 — Fiche navette

**Si approuvée** → créer `data/fiche_navette/navette_<ref>.txt` :

```
========================================
FICHE NAVETTE — PROJET renovation_2026
========================================
Référence facture  : <ref>
Date de la facture : <date>
Émetteur           : <société>
Lot concerné       : <lot>
Montant TTC        : <montant> EUR

----------------------------------------
          ✓ FACTURE APPROUVÉE
----------------------------------------
Date d'approbation : <JJ/MM/AAAA>
Approuvé par       : RenovBat
========================================
```

**Si rejetée** → créer `data/fiche_navette/rejet_<ref>.txt` :

```
========================================
FICHE NAVETTE — PROJET renovation_2026
========================================
Référence facture  : <ref>
Date de la facture : <date>
Émetteur           : <société>
Lot concerné       : <lot ou "inconnu">
Montant TTC        : <montant> EUR

----------------------------------------
          ✗ FACTURE REJETÉE
----------------------------------------
Date de traitement : <JJ/MM/AAAA>
Motif du rejet     : <motif>
Traité par         : RenovBat
========================================
```

---

## Étape 5 — Bon de paiement (uniquement si approuvée)

Créer `data/bons_paiement/bon_<ref>.txt` :

```
========================================
BON DE PAIEMENT — PROJET renovation_2026
========================================
Référence facture  : <ref>
Date de la facture : <date>
Émetteur           : <société>
Lot concerné       : <lot>
Montant TTC        : <montant> EUR

Date de mise en paiement : <date du jour + 30 jours, JJ/MM/AAAA>

Établi par : RenovBat
========================================
```

Puis afficher le message de transmission à IMMOSOCIAL :

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📨 TRANSMISSION À IMMOSOCIAL
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
À      : IMMOSOCIAL
Objet  : Bon de paiement — Facture <ref>

Veuillez trouver ci-joint le bon pour la facture n° <ref> en date du <date>
émise par la société <nom> pour le lot <lot> du projet renovation_2026.

Cordialement,
RenovBat
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
```

---

## Étape 6 — Récapitulatif

Afficher un tableau de toutes les factures traitées dans cette session :

| Référence | Société | Lot | Montant TTC | Statut |
|---|---|---|---|---|
| FAC-... | ... | ... | ... EUR | ✓ Approuvée / ✗ Rejetée |

---

## Règles

- Ne pas retraiter une facture dont `navette_*.txt` ou `rejet_*.txt` existe déjà.
- La date du jour est dans le contexte système (`currentDate`).
- Les PDFs dans `data/factures/` peuvent être régénérés avec `python3 scripts/generate_factures.py`.
