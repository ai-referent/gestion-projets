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

Pour chaque PDF, tente d'abord d'extraire les données depuis le XML Factur-X embarqué
(via `xml.etree.ElementTree`), et utilise le parsing des streams PDF en fallback.

```python
import re, pathlib, xml.etree.ElementTree as ET

_NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}
_MOIS = ["","janvier","fevrier","mars","avril","mai","juin",
         "juillet","aout","septembre","octobre","novembre","decembre"]

def _parse_facturx_xml(data):
    xml_m = re.search(b'<rsm:CrossIndustryInvoice.*?</rsm:CrossIndustryInvoice>', data, re.DOTALL)
    if not xml_m:
        return None
    try:
        root = ET.fromstring(xml_m.group(0).decode('utf-8'))
    except ET.ParseError:
        return None
    inv_id = root.findtext("rsm:ExchangedDocument/ram:ID", namespaces=_NS)
    d      = root.findtext("rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString", namespaces=_NS)
    seller = root.findtext(".//ram:SellerTradeParty/ram:Name", namespaces=_NS)
    total  = root.findtext(".//ram:GrandTotalAmount", namespaces=_NS)
    if not all([inv_id, d, seller, total]):
        return None
    date_fr = f"{int(d[6:8])} {_MOIS[int(d[4:6])]} {d[:4]}"
    return {"numero": inv_id.strip(), "date": date_fr,
            "societe": seller.strip(), "montant_ttc": float(total.strip())}

def _parse_pdf_streams(data):
    streams = re.findall(b'stream\n(.*?)\nendstream', data, re.DOTALL)
    texts = []
    for s in streams:
        for line in s.decode('latin-1').split('\n'):
            m = re.search(r'\(([^)]+)\)', line)
            if m:
                texts.append(m.group(1).strip())
    numero_raw = next((t for t in texts if 'FAC-' in t), None)
    date_raw   = next((t for t in texts if 'Date' in t), None)
    societe    = next((t for t in texts if len(t) > 5 and 'avenue' not in t.lower()
                       and 'SIRET' not in t and 'FAC-' not in t
                       and 'Date' not in t and 'Client' not in t), None)
    ttc_idx    = next((i for i, t in enumerate(texts) if 'TOTAL TTC' in t), None)
    if not all([numero_raw, date_raw, societe, ttc_idx is not None]):
        return None
    numero  = re.sub(r'^[^:]*:\s*', '', numero_raw).strip()
    date    = re.sub(r'^[Dd]ate[^:]*:\s*', '', date_raw).strip()
    amt_str = texts[ttc_idx + 1] if ttc_idx + 1 < len(texts) else ""
    amt_str = re.sub(r'[^\d,.]', '', amt_str).replace(',', '.')
    try:
        montant = float(amt_str)
    except ValueError:
        return None
    return {"numero": numero, "date": date, "societe": societe, "montant_ttc": montant}

def parse_facture(path):
    data = pathlib.Path(path).read_bytes()
    result = _parse_facturx_xml(data) or _parse_pdf_streams(data)
    if result is None:
        raise ValueError(f"Impossible de parser {path}")
    return result
```

Utilise directement les champs du dict retourné :
- `result["numero"]`      → numéro de facture (ex: `FAC-2026-001`)
- `result["date"]`        → date lisible (ex: `15 mars 2026`)
- `result["societe"]`     → nom de la société émettrice
- `result["montant_ttc"]` → montant TTC en float (ex: `12500.0`)

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

Pour lire les montants des navettes existantes, chercher la ligne `Montant TTC` dans chaque `navette_*.txt` et normaliser : supprimer les espaces insécables et normaux, remplacer la virgule par un point.

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

Puis composer le message de transmission à IMMOSOCIAL et le stocker dans `data/mails/mail_<ref>.txt` :

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

Créer `data/mails/` si absent. Afficher le contenu du mail à l'écran après sauvegarde.

---

## Étape 6 — Récapitulatif

Afficher un tableau de toutes les factures traitées dans cette session :

| Référence | Société | Lot | Montant TTC | Statut |
|---|---|---|---|---|
| FAC-... | ... | ... | ... EUR | ✓ Approuvée / ✗ Rejetée |

Puis sauvegarder ce tableau et un graphique de consommation budgétaire dans `data/vue_globale/recap_<AAAAMMJJ>.txt` :

```
========================================
RÉCAPITULATIF — PROJET renovation_2026
========================================
Date : <JJ/MM/AAAA>

--- Factures traitées ---
| Référence | Société | Lot | Montant TTC | Statut |
|...|...|...|...|...|

--- Consommation budgétaire par lot ---

<Pour chaque lot, calculer : engagé = somme des navettes approuvées,
 budget = montant_global du lot, pct = engagé / budget * 100>

isolation_thermique
  Engagé  : XX XXX,XX EUR / YY XXX,XX EUR (PP %)
  [████████░░░░░░░░░░░░] PP %

renovation_chauffage
  Engagé  : XX XXX,XX EUR / YY XXX,XX EUR (PP %)
  [████████████░░░░░░░░] PP %

(barre de 20 caractères : █ pour chaque 5 % consommé, arrondi)
========================================
```

Créer `data/vue_globale/` si absent.

---

## Règles

- Ne pas retraiter une facture dont `navette_*.txt` ou `rejet_*.txt` existe déjà.
- La date du jour est dans le contexte système (`currentDate`).
- Les PDFs dans `data/factures/` peuvent être régénérés avec `python3 scripts/generate_factures.py`.
