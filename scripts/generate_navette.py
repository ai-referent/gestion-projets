#!/usr/bin/env python3
"""Génère ou met à jour une feuille fiche-navette + bon de paiement dans un classeur xlsx.

Usage:
    python3 scripts/generate_navette.py '<json>'

JSON attendu:
{
  "target_file"   : "data/navettes_et_bons/lot01_...",
  "sheet_name"    : "FAC-2026-001",
  "fac"           : {"numero": "FAC-2026-001", "date": "15 mars 2026",
                     "societe": "Platr'O'Matic SARL", "montant_ttc": 12500.0},
  "id_lot"        : "isolation_thermique",
  "approved"      : true,
  "motif"         : null,
  "cumul_existant": 0.0,
  "budget_total"  : 20000.0        (HT, depuis budget_lot_prestataire.csv)
}

Cellules de référence pour la lecture par situations.md :
  B10 = montant HT, B11 = TVA, B12 = montant TTC
  A14 = marqueur approbation ("✓ FACTURE APPROUVÉE" ou "✗ FACTURE REJETÉE")
  B24 = nouveau cumul TTC (bon de paiement)

Sortie stdout: message de statut.
"""

import json
import pathlib
import sys
from datetime import date

import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment

TVA_TAUX = 0.20


def _eur(cell):
    cell.number_format = '#,##0.00 "EUR"'


def add_sheet(data: dict) -> str:
    target_file = pathlib.Path(data["target_file"])
    sheet_name  = data["sheet_name"]
    fac         = data["fac"]
    id_lot      = data["id_lot"]
    approved    = data["approved"]
    motif       = data.get("motif")
    cumul_existant_ttc = float(data.get("cumul_existant", 0))
    budget_ht          = float(data.get("budget_total", 0))

    montant_ttc = float(fac["montant_ttc"])
    montant_ht  = round(montant_ttc / (1 + TVA_TAUX), 2)
    montant_tva = round(montant_ttc - montant_ht, 2)
    budget_ttc  = round(budget_ht * (1 + TVA_TAUX), 2)
    today       = date.today().strftime("%d/%m/%Y")

    # Charger ou créer le classeur
    if target_file.exists():
        wb = openpyxl.load_workbook(target_file)
        if sheet_name in wb.sheetnames:
            return f"IGNORÉE (déjà traitée) — {target_file.name}"
    else:
        wb = openpyxl.Workbook()
        if "Sheet" in wb.sheetnames:
            del wb["Sheet"]

    ws = wb.create_sheet(title=sheet_name)

    GREEN = "1E8449"
    RED   = "C0392B"

    # ── FICHE NAVETTE ─────────────────────────────────────────────────────────

    ws["A1"] = "FICHE NAVETTE — PROJET renovation_2026"
    ws["A1"].font = Font(bold=True, size=13)
    ws.merge_cells("A1:B1")

    ws["A2"] = "RenovBat Bureau d'Etude Bâtiment"
    ws["A2"].font = Font(bold=True, color="FFFFFF")
    ws["A2"].fill = PatternFill("solid", fgColor="1E8449")
    ws["A2"].alignment = Alignment(horizontal="center")
    ws.merge_cells("A2:B2")

    ws["A4"] = "MOA";  ws["B4"] = "IMMOSOCIAL_69"

    ws["A6"] = "Référence facture";  ws["B6"] = fac["numero"]
    ws["A7"] = "Date de la facture"; ws["B7"] = fac["date"]
    ws["A8"] = "Émetteur";           ws["B8"] = fac["societe"]
    ws["A9"] = "Lot concerné";       ws["B9"] = id_lot

    # Détail HT / TVA / TTC  (B10, B11, B12 = cellules de référence)
    ws["A10"] = "Montant HT";        ws["B10"] = montant_ht;  _eur(ws["B10"])
    ws["A11"] = f"TVA ({TVA_TAUX:.0%})"; ws["B11"] = montant_tva; _eur(ws["B11"])
    ws["A12"] = "Montant TTC";       ws["B12"] = montant_ttc; _eur(ws["B12"])

    # Statut — A14 est la cellule de référence lue par situations.md
    if approved:
        ws["A14"] = "✓ FACTURE APPROUVÉE"
        ws["A14"].font = Font(bold=True, color=GREEN)
        ws.merge_cells("A14:B14")
        ws["A15"] = "Date d'approbation"; ws["B15"] = today
        ws["A16"] = "Approuvé par";       ws["B16"] = "RenovBat"
    else:
        ws["A14"] = "✗ FACTURE REJETÉE"
        ws["A14"].font = Font(bold=True, color=RED)
        ws.merge_cells("A14:B14")
        ws["A15"] = "Date de traitement"; ws["B15"] = today
        ws["A16"] = "Motif du rejet";     ws["B16"] = motif or ""
        ws["A17"] = "Traité par";         ws["B17"] = "RenovBat"

    # ── BON DE PAIEMENT (uniquement si approuvée) ─────────────────────────────
    if approved:
        nouveau_cumul_ttc = cumul_existant_ttc + montant_ttc

        ws["A19"] = "BON DE PAIEMENT — PROJET renovation_2026"
        ws["A19"].font = Font(bold=True, size=13)
        ws.merge_cells("A19:B19")

        ws["A21"] = "Budget total du lot HT";  ws["B21"] = budget_ht;  _eur(ws["B21"])
        ws["A22"] = "Budget total du lot TTC"; ws["B22"] = budget_ttc; _eur(ws["B22"])

        ws["A24"] = "Situations précédentes TTC"
        ws["B24"] = cumul_existant_ttc;  _eur(ws["B24"])

        ws["A25"] = "Présente situation HT";  ws["B25"] = montant_ht;  _eur(ws["B25"])
        ws["A26"] = "Présente situation TVA"; ws["B26"] = montant_tva; _eur(ws["B26"])
        ws["A27"] = "Présente situation TTC"; ws["B27"] = montant_ttc; _eur(ws["B27"])

        # B29 = nouveau cumul TTC (cellule de référence pour le récapitulatif)
        ws["A29"] = "Nouveau cumul TTC"
        ws["B29"] = nouveau_cumul_ttc
        ws["B29"].font = Font(bold=True)
        _eur(ws["B29"])

        ws["A30"] = "Reste à régler TTC"
        ws["B30"] = round(budget_ttc - nouveau_cumul_ttc, 2)
        _eur(ws["B30"])

        ws["A32"] = "Date d'émission";  ws["B32"] = today
        ws["A33"] = "Établi par";       ws["B33"] = "RenovBat (MOE)"
        ws["A34"] = "Signataire";       ws["B34"] = "J. Pons"
        ws["A35"] = "À destination de"; ws["B35"] = "IMMOSOCIAL_69 (MOA)"

    ws.column_dimensions["A"].width = 38
    ws.column_dimensions["B"].width = 22

    target_file.parent.mkdir(parents=True, exist_ok=True)
    wb.save(target_file)
    statut = "APPROUVÉE ✓" if approved else "REJETÉE ✗"
    return f"{sheet_name} : {statut} — {target_file.name}"


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: generate_navette.py '<json>'", file=sys.stderr)
        sys.exit(1)
    result = add_sheet(json.loads(sys.argv[1]))
    print(result)
