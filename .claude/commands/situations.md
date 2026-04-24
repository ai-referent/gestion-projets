# Skill : Traitement des situations (factures) — Projet renovation_2026

Ce skill traite toutes les **nouvelles** factures dans `data/factures/` pour le compte de **RenovBat** (MOE).
Pour chaque nouvelle facture (non encore traitée), il effectue un pré-check budgétaire, puis met à jour le fichier Excel du lot-prestataire dans `data/navettes_et_bons/` en ajoutant une feuille avec fiche navette et bon de paiement.
Les mails de transmission (RenovBat → IMMOSOCIAL_69) sont simulés dans `data/navettes_et_bons/mails/`.

---

## Étape 1 — Charger les données de référence

```python
import csv, pathlib, re, xml.etree.ElementTree as ET, unicodedata
from datetime import date

def load_csv(path):
    with open(path, newline='', encoding='utf-8') as f:
        return list(csv.DictReader(f))

# prestataires.csv — colonnes : id_prestataire, nom_prestataire, adresse_prestataire, mail_prestataire, siret
prestataires = {p["id_prestataire"]: p for p in load_csv("data/prestataires/prestataires.csv")}

# budget_lot_prestataire.csv — colonnes : id_prestataire, id_lot, montant_initial, avenant_1, avenant_2
budgets = {}
lot_nums = {}
for i, b in enumerate(load_csv("data/budget/budget_lot_prestataire.csv"), start=1):
    id_p = b["id_prestataire"]
    budgets[id_p] = {
        "id_lot": b["id_lot"].strip(),
        "budget_total": float(b["montant_initial"]) + float(b["avenant_1"]) + float(b["avenant_2"]),
    }
    lot_nums[id_p] = i

factures_pdf = sorted(pathlib.Path("data/factures").glob("*.pdf"))
```

---

## Étape 2 — Parser chaque facture PDF

```python
_NS = {
    "rsm": "urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100",
    "ram": "urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100",
    "udt": "urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100",
}
_MOIS = ["","janvier","fevrier","mars","avril","mai","juin",
         "juillet","aout","septembre","octobre","novembre","decembre"]

def _parse_xml(data):
    m = re.search(b'<rsm:CrossIndustryInvoice.*?</rsm:CrossIndustryInvoice>', data, re.DOTALL)
    if not m:
        return None
    try:
        root = ET.fromstring(m.group(0).decode('utf-8'))
    except ET.ParseError:
        return None
    inv_id = root.findtext("rsm:ExchangedDocument/ram:ID", namespaces=_NS)
    d      = root.findtext("rsm:ExchangedDocument/ram:IssueDateTime/udt:DateTimeString", namespaces=_NS)
    seller = root.findtext(".//ram:SellerTradeParty/ram:Name", namespaces=_NS)
    total  = root.findtext(".//ram:GrandTotalAmount", namespaces=_NS)
    siret  = root.findtext(".//ram:SellerTradeParty/ram:SpecifiedLegalOrganization/ram:ID", namespaces=_NS)
    if not all([inv_id, d, seller, total]):
        return None
    return {
        "numero": inv_id.strip(),
        "date": f"{int(d[6:8])} {_MOIS[int(d[4:6])]} {d[:4]}",
        "societe": seller.strip(),
        "montant_ttc": float(total.strip()),
        "siret": siret.strip() if siret else None,
    }

def _parse_streams(data):
    texts = []
    for s in re.findall(b'stream\n(.*?)\nendstream', data, re.DOTALL):
        for line in s.decode('latin-1').split('\n'):
            m = re.search(r'\(([^)]+)\)', line)
            if m:
                texts.append(m.group(1).strip())
    fac = next((t for t in texts if 'FAC-' in t), None)
    dat = next((t for t in texts if 'Date' in t), None)
    soc = next((t for t in texts if len(t) > 5 and 'avenue' not in t.lower()
                and 'SIRET' not in t and 'FAC-' not in t
                and 'Date' not in t and 'Client' not in t), None)
    idx = next((i for i, t in enumerate(texts) if 'TOTAL TTC' in t), None)
    if not all([fac, dat, soc, idx is not None]):
        return None
    amt = re.sub(r'[^\d,.]', '', texts[idx+1] if idx+1 < len(texts) else "").replace(',', '.')
    try:
        return {"numero": re.sub(r'^[^:]*:\s*', '', fac).strip(),
                "date": re.sub(r'^[Dd]ate[^:]*:\s*', '', dat).strip(),
                "societe": soc, "montant_ttc": float(amt), "siret": None}
    except ValueError:
        return None

def parse_facture(path):
    data = pathlib.Path(path).read_bytes()
    return _parse_xml(data) or _parse_streams(data)
```

---

## Étape 3 — Pour chaque PDF, identifier le prestataire et vérifier l'éligibilité

**a) Trouver le prestataire** — par SIRET en priorité, sinon par nom (souple) :

```python
def normalize(s):
    s = unicodedata.normalize('NFD', s)
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    return re.sub(r'[^a-z0-9]', '', s.lower())

def find_prestataire(fac, prestataires):
    if fac.get("siret"):
        for id_p, p in prestataires.items():
            if p["siret"] == fac["siret"]:
                return id_p
    fn = normalize(fac["societe"])
    for id_p, p in prestataires.items():
        pn = normalize(p["nom_prestataire"])
        if pn in fn or fn in pn:
            return id_p
    return None
```

Si non trouvé → **REJET** : `"Société non référencée sur le projet"`.

**b) Localiser le fichier Excel du lot** dans `data/navettes_et_bons/`.
Un fichier correspond si son nom (stem) contient `id_lot` (insensible à la casse, `_` équivalent à espace).
Si aucun fichier trouvé, le nom standard est `lot{num:02d}_{id_lot_CamelCase}_{id_p}.xlsx`.

```python
import openpyxl

base_nav = pathlib.Path("data/navettes_et_bons")
id_lot = budgets[id_p]["id_lot"]
search = id_lot.lower().replace("_", " ")
target_file = None
for f in sorted(base_nav.glob("*.xlsx")):
    if search in f.stem.lower().replace("_", " "):
        target_file = f
        break
if not target_file:
    num = lot_nums[id_p]
    cap = id_lot.replace("_", " ").title().replace(" ", "_")
    target_file = base_nav / f"lot{num:02d}_{cap}_{id_p}.xlsx"
```

**c) Vérifier si la facture est déjà traitée** (feuille de même nom dans le classeur) :

```python
if target_file.exists():
    wb = openpyxl.load_workbook(target_file)
    if fac["numero"] in wb.sheetnames:
        print(f"  → {fac['numero']} : déjà traitée, ignorée.")
        # passer à la facture suivante
else:
    wb = openpyxl.Workbook()
    if "Sheet" in wb.sheetnames:
        del wb["Sheet"]
```

**d) Calculer le cumul existant** à partir des feuilles approuvées déjà présentes :
La cellule `A12` contient `"✓ FACTURE APPROUVÉE"` si approuvée ; `B10` contient le montant TTC.

```python
cumul_existant = 0.0
for sname in wb.sheetnames:
    ws_ex = wb[sname]
    if ws_ex["A12"].value and "APPROUVÉE" in str(ws_ex["A12"].value):
        try:
            cumul_existant += float(ws_ex["B10"].value or 0)
        except (TypeError, ValueError):
            pass
```

**e) Vérification budgétaire** :

```python
budget_total = budgets[id_p]["budget_total"]
montant = fac["montant_ttc"]
if cumul_existant + montant > budget_total:
    approved = False
    motif = (f"Dépassement du budget lot "
             f"(budget={budget_total:.2f}€, engagé={cumul_existant:.2f}€, facture={montant:.2f}€)")
else:
    approved = True
    motif = None
```

---

## Étape 4 — Mettre à jour le fichier Excel lot-prestataire

Ajouter une feuille nommée `fac["numero"]` dans le classeur.
**Disposition fixe** (A = libellés, B = valeurs) :

```python
from openpyxl.styles import Font, Alignment

ws = wb.create_sheet(title=fac["numero"])
today = date.today().strftime("%d/%m/%Y")

# ── FICHE NAVETTE ──────────────────────────────────────────
ws["A1"] = "FICHE NAVETTE — PROJET renovation_2026"
ws["A1"].font = Font(bold=True, size=13)
ws.merge_cells("A1:B1")

ws["A3"] = "MOE" ; ws["B3"] = "RenovBat"
ws["A4"] = "MOA" ; ws["B4"] = "IMMOSOCIAL_69"

ws["A6"] = "Référence facture"  ; ws["B6"] = fac["numero"]
ws["A7"] = "Date de la facture" ; ws["B7"] = fac["date"]
ws["A8"] = "Émetteur"           ; ws["B8"] = fac["societe"]
ws["A9"] = "Lot concerné"       ; ws["B9"] = id_lot
ws["A10"] = "Montant TTC"
ws["B10"] = montant
ws["B10"].number_format = '#,##0.00 "EUR"'

# Statut — A12 est la cellule de référence pour le calcul du cumul
if approved:
    ws["A12"] = "✓ FACTURE APPROUVÉE"
    ws["A12"].font = Font(bold=True, color="1E8449")
    ws.merge_cells("A12:B12")
    ws["A13"] = "Date d'approbation" ; ws["B13"] = today
    ws["A14"] = "Approuvé par"       ; ws["B14"] = "RenovBat"
else:
    ws["A12"] = "✗ FACTURE REJETÉE"
    ws["A12"].font = Font(bold=True, color="C0392B")
    ws.merge_cells("A12:B12")
    ws["A13"] = "Date de traitement" ; ws["B13"] = today
    ws["A14"] = "Motif du rejet"     ; ws["B14"] = motif
    ws["A15"] = "Traité par"         ; ws["B15"] = "RenovBat"

# ── BON DE PAIEMENT (uniquement si approuvée) ──────────────
if approved:
    nouveau_cumul = cumul_existant + montant

    ws["A17"] = "BON DE PAIEMENT — PROJET renovation_2026"
    ws["A17"].font = Font(bold=True, size=13)
    ws.merge_cells("A17:B17")

    ws["A19"] = "Montant global prévu pour le lot"
    ws["B19"] = budget_total
    ws["B19"].number_format = '#,##0.00 "EUR"'

    ws["A20"] = "Situations précédentes"
    ws["B20"] = cumul_existant
    ws["B20"].number_format = '#,##0.00 "EUR"'

    ws["A21"] = "Présente situation"
    ws["B21"] = montant
    ws["B21"].number_format = '#,##0.00 "EUR"'

    ws["A23"] = "Nouveau cumul"
    ws["B23"] = nouveau_cumul
    ws["B23"].font = Font(bold=True)
    ws["B23"].number_format = '#,##0.00 "EUR"'

    ws["A24"] = "Reste à régler"
    ws["B24"] = budget_total - nouveau_cumul
    ws["B24"].number_format = '#,##0.00 "EUR"'

    ws["A26"] = "Date d'émission"    ; ws["B26"] = today
    ws["A27"] = "Établi par"         ; ws["B27"] = "RenovBat (MOE)"
    ws["A28"] = "À destination de"   ; ws["B28"] = "IMMOSOCIAL_69 (MOA)"

ws.column_dimensions["A"].width = 38
ws.column_dimensions["B"].width = 22

target_file.parent.mkdir(parents=True, exist_ok=True)
wb.save(target_file)
print(f"  → {fac['numero']} : {'APPROUVÉE ✓' if approved else 'REJETÉE ✗'} — {target_file.name}")
```

---

## Étape 5 — Générer le mail de transmission (si approuvée)

Créer `data/navettes_et_bons/mails/mail_<ref>.txt` :

```python
mails_dir = pathlib.Path("data/navettes_et_bons/mails")
mails_dir.mkdir(parents=True, exist_ok=True)

if approved:
    nouveau_cumul = cumul_existant + montant
    contenu = f"""\
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📨 MAIL — TRANSMISSION RenovBat → IMMOSOCIAL_69
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
De     : RenovBat (MOE) <moe@renovbat.fr>
À      : IMMOSOCIAL_69 (MOA) <moa@immosocial69.fr>
Date   : {today}
Objet  : Fiche navette et bon de paiement — Facture {fac['numero']}

Madame, Monsieur,

Veuillez trouver ci-joint la fiche navette et le bon de paiement
relatifs à la facture n° {fac['numero']} du {fac['date']},
émise par {fac['societe']} dans le cadre du lot {id_lot}
du projet renovation_2026.

Statut            : ✓ APPROUVÉE
Montant TTC       : {montant:,.2f} EUR
Nouveau cumul lot : {nouveau_cumul:,.2f} EUR
Reste à régler    : {budget_total - nouveau_cumul:,.2f} EUR

Cordialement,
RenovBat — Maître d'Œuvre du projet renovation_2026
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""
    (mails_dir / f"mail_{fac['numero']}.txt").write_text(contenu, encoding="utf-8")
    print(f"  → Mail généré : mail_{fac['numero']}.txt")
```

---

## Étape 6 — Récapitulatif

Afficher un tableau de toutes les factures traitées dans cette session :

| Référence | Société | Lot | Montant TTC | Statut |
|---|---|---|---|---|
| FAC-... | ... | ... | ... EUR | ✓ Approuvée / ✗ Rejetée |

Puis recalculer l'état budgétaire de chaque lot en relisant tous les fichiers Excel mis à jour :

```python
lots_state = {}
for id_p, bud in budgets.items():
    id_lot = bud["id_lot"]
    search = id_lot.lower().replace("_", " ")
    f = next((x for x in sorted(base_nav.glob("*.xlsx"))
               if search in x.stem.lower().replace("_", " ")), None)
    engage = 0.0
    if f and f.exists():
        wb_r = openpyxl.load_workbook(f)
        for sname in wb_r.sheetnames:
            ws_r = wb_r[sname]
            if ws_r["A12"].value and "APPROUVÉE" in str(ws_r["A12"].value):
                try:
                    engage += float(ws_r["B10"].value or 0)
                except (TypeError, ValueError):
                    pass
    lots_state[id_lot] = {"budget": bud["budget_total"], "engage": engage}
```

Générer dans `data/vue_globale/` (créer si absent) :

### a) Récapitulatif texte — `recap_<AAAAMMJJ>.txt`

```
========================================
RÉCAPITULATIF — PROJET renovation_2026
========================================
Date : <JJ/MM/AAAA>

--- Factures traitées ---
| Référence | Société | Lot | Montant TTC | Statut |
|...|...|...|...|...|

--- Consommation budgétaire par lot ---
isolation_thermique  : XX XXX € / YY XXX € (PP %)
isolation_acoustique : XX XXX € / YY XXX € (PP %)
renovation_chauffage : XX XXX € / YY XXX € (PP %)
========================================
```

### b) Graphique PNG — `budget_<AAAAMMJJ>.png`

```python
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

labels  = list(lots_state.keys())
budgets_v = [lots_state[l]["budget"] for l in labels]
engages = [lots_state[l]["engage"] for l in labels]
pcts    = [e / b * 100 if b > 0 else 0 for e, b in zip(engages, budgets_v)]
colors  = ["#e74c3c" if p > 90 else "#e67e22" if p > 70 else "#2ecc71" for p in pcts]

fig, ax = plt.subplots(figsize=(9, 4))
y = range(len(labels))
ax.barh(y, engages, color=colors, height=0.5, label="Engagé")
ax.barh(y, [b - e for b, e in zip(budgets_v, engages)],
        left=engages, color="#ecf0f1", height=0.5, edgecolor="#bdc3c7", label="Disponible")
for i, (e, b, p) in enumerate(zip(engages, budgets_v, pcts)):
    ax.text(b + 500, i, f"{p:.1f} %  ({e:,.0f} / {b:,.0f} €)".replace(",", " "),
            va="center", fontsize=9)
ax.set_yticks(list(y))
ax.set_yticklabels([l.replace("_", " ").title() for l in labels])
ax.set_xlabel("Montant (EUR)")
ax.set_title("Consommation budgétaire — Projet renovation_2026", fontsize=12, fontweight="bold")
ax.set_xlim(0, max(budgets_v) * 1.45)
ax.legend(loc="lower right", fontsize=8)
ax.grid(axis="x", linestyle="--", alpha=0.4)
fig.tight_layout()
yyyymmdd = date.today().strftime("%Y%m%d")
fig.savefig(pathlib.Path("data/vue_globale") / f"budget_{yyyymmdd}.png", dpi=130)
plt.close()
```

### c) Classeur Excel — `budget_<AAAAMMJJ>.xlsx`

```python
import openpyxl
from openpyxl.chart import BarChart, Reference
from openpyxl.styles import Font, PatternFill, Alignment

wb_out = openpyxl.Workbook()

ws1 = wb_out.active
ws1.title = "Factures"
ws1.append(["Référence", "Société", "Lot", "Montant TTC (€)", "Statut"])
for cell in ws1[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="2C3E50")
    cell.alignment = Alignment(horizontal="center")
for f in factures_session:   # liste de dicts {ref, societe, lot, ttc, statut}
    ws1.append([f["ref"], f["societe"], f["lot"], f["ttc"],
                "✓ Approuvée" if f["statut"] == "Approuvée" else "✗ Rejetée"])
for col, w in zip("ABCDE", [16, 26, 24, 18, 14]):
    ws1.column_dimensions[col].width = w

ws2 = wb_out.create_sheet("Budget")
ws2.append(["Lot", "Budget (€)", "Engagé (€)", "Disponible (€)", "% consommé"])
for cell in ws2[1]:
    cell.font = Font(bold=True, color="FFFFFF")
    cell.fill = PatternFill("solid", fgColor="2C3E50")
for lot_name, v in lots_state.items():
    ws2.append([lot_name, v["budget"], v["engage"],
                v["budget"] - v["engage"],
                round(v["engage"] / v["budget"] * 100, 1) if v["budget"] > 0 else 0])
for col, w in zip("ABCDE", [26, 16, 16, 16, 14]):
    ws2.column_dimensions[col].width = w

chart = BarChart()
chart.type = "bar"
chart.grouping = "stacked"
chart.title = "Budget vs Engagé par lot"
chart.width, chart.height = 18, 10
data_ref = Reference(ws2, min_col=2, max_col=4, min_row=1, max_row=1 + len(lots_state))
cats = Reference(ws2, min_col=1, min_row=2, max_row=1 + len(lots_state))
chart.add_data(data_ref, titles_from_data=True)
chart.set_categories(cats)
ws2.add_chart(chart, "F2")

wb_out.save(pathlib.Path("data/vue_globale") / f"budget_{yyyymmdd}.xlsx")
```

`yyyymmdd` = date du jour au format `AAAAMMJJ` (depuis `currentDate`).

---

## Règles

- Ne pas retraiter une facture dont la feuille existe déjà dans le fichier Excel du lot (vérifier `fac["numero"] in wb.sheetnames`).
- La source de vérité des situations traitées est les fichiers Excel dans `data/navettes_et_bons/`.
- La date du jour est dans le contexte système (`currentDate`).
- Les PDFs dans `data/factures/` peuvent être régénérés avec `python3 scripts/generate_factures.py`.
