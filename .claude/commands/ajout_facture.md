# Skill : Ajout d'une facture — Projet renovation_2026

Ce skill guide la saisie d'une nouvelle facture, crée le PDF correspondant et l'ajoute dans `data/factures/`.
Si le prestataire est nouveau, il est également ajouté dans `data/prestataires/prestataires.csv`.

---

## Étape 1 — Collecte des informations

Poser les questions suivantes une par une (attendre la réponse avant de passer à la suivante) :

1. **Numéro de facture** — format recommandé : `FAC-AAAA-NNN` (ex: FAC-2026-004)
2. **Date de la facture** — format JJ/MM/AAAA ou texte libre (ex: 20 avril 2026)
3. **Nom de la société émettrice**
4. **Identifiant de la société** — code court en majuscules (ex: REVE001). Si la société est déjà dans `data/prestataires/prestataires.csv`, utiliser son identifiant existant.
5. **Lot concerné** — doit correspondre à un lot existant dans `data/budget/budget_global.csv`. Afficher la liste des lots disponibles avant de poser la question.
6. **Objet des travaux** — description courte (ex: Pose isolation combles)
7. **Montant HT** — en euros (ex: 8000)
8. **Taux de TVA** — en % (défaut : 20)
9. **Adresse de la société** (optionnel — laisser vide pour passer)
10. **SIRET** (optionnel — laisser vide pour passer)

Calculer automatiquement :
- Montant TVA = Montant HT × (taux TVA / 100)
- Montant TTC = Montant HT + Montant TVA

Afficher un récapitulatif et demander confirmation avant de créer le PDF.

---

## Étape 2 — Vérification du prestataire

Lire `data/prestataires/prestataires.csv`.

- Si l'identifiant existe déjà → vérifier que le lot correspond. Si le lot diffère, signaler l'incohérence et demander confirmation.
- Si l'identifiant est nouveau → ajouter une ligne dans `prestataires.csv` :
  ```
  <identifiant>,<nom>,<lot>
  ```
  Et signaler : "Nouveau prestataire ajouté : <nom> (<identifiant>) sur le lot <lot>."

---

## Étape 3 — Génération du PDF

Créer le fichier `data/factures/<numero_facture>.pdf` en utilisant le code suivant (à adapter avec les données saisies) :

```python
import pathlib

def make_stream(content: str) -> bytes:
    return content.encode("latin-1", errors="replace")

def build_pdf(pages_content: list[str]) -> bytes:
    objects = []
    stream_ids, page_ids = [], []
    for page_text in pages_content:
        stream_data = make_stream(page_text)
        stream_obj = f"<< /Length {len(stream_data)} >>\nstream\n".encode() + stream_data + b"\nendstream"
        objects.append(stream_obj)
        stream_ids.append(len(objects))
    for sid in stream_ids:
        page_obj = (
            f"<< /Type /Page /Parent 2 0 R "
            f"/Resources << /Font << /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >> "
            f"/F2 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >> >> >> "
            f"/MediaBox [0 0 595 842] /Contents {sid} 0 R >>"
        ).encode()
        objects.append(page_obj)
        page_ids.append(len(objects))
    kids = " ".join(f"{pid} 0 R" for pid in page_ids)
    objects.append(f"<< /Type /Pages /Kids [{kids}] /Count {len(page_ids)} >>".encode())
    pages_id = len(objects)
    fixed = []
    for i, obj in enumerate(objects):
        if (i + 1) in page_ids:
            obj = obj.replace(b"/Parent 2 0 R", f"/Parent {pages_id} 0 R".encode())
        fixed.append(obj)
    objects = fixed
    objects.append(f"<< /Type /Catalog /Pages {pages_id} 0 R >>".encode())
    catalog_id = len(objects)
    body = b"%PDF-1.4\n"
    offsets = []
    for i, obj in enumerate(objects):
        offsets.append(len(body))
        body += f"{i+1} 0 obj\n".encode() + obj + b"\nendobj\n"
    xref_pos = len(body)
    xref = f"xref\n0 {len(objects)+1}\n0000000000 65535 f \n"
    for off in offsets:
        xref += f"{off:010d} 00000 n \n"
    trailer = f"trailer\n<< /Size {len(objects)+1} /Root {catalog_id} 0 R >>\nstartxref\n{xref_pos}\n%%EOF\n"
    return body + xref.encode() + trailer.encode()
```

Contenu de la page PDF (adapter avec les valeurs saisies) :

```
BT
/F2 16 Tf
50 820 Td
(<NOM SOCIETE>) Tj
/F1 10 Tf
0 -18 Td
(<ADRESSE SI FOURNIE>) Tj
0 -14 Td
(<SIRET SI FOURNI>) Tj
/F2 14 Tf
0 -45 Td
(FACTURE) Tj
/F1 11 Tf
0 -22 Td
(Numero        : <NUMERO>) Tj
0 -16 Td
(Date          : <DATE>) Tj
0 -16 Td
(Client        : RenovBat - 8 avenue des Batisseurs, 69000 Lyon) Tj
0 -16 Td
(Lot           : <LOT>) Tj
/F2 11 Tf
0 -35 Td
(Designation) Tj
300 0 Td
(Montant) Tj
/F1 11 Tf
-300 -20 Td
(<OBJET TRAVAUX>) Tj
300 0 Td
(<MONTANT HT> EUR HT) Tj
-300 -18 Td
(TVA <TAUX>%) Tj
300 0 Td
(<MONTANT TVA> EUR) Tj
/F2 12 Tf
-300 -22 Td
(TOTAL TTC) Tj
300 0 Td
(<MONTANT TTC> EUR) Tj
/F1 9 Tf
-300 -60 Td
(Paiement a 30 jours.) Tj
ET
```

Formater les montants avec 2 décimales et espace comme séparateur des milliers (ex: `12 500,00`).

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
