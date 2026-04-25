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
  "budget_total"  : 20000.0
}

Sortie stdout: chemin du fichier sauvegardé.
"""

import json
import pathlib
import sys
from datetime import date

import openpyxl
from openpyxl.styles import Alignment, Font, PatternFill


def _fmt_eur(cell):
    cell.number_format = '#,##0.00 "EUR"'


def _bold(cell, size=None, color=None):
    kwargs = {"bold": True}
    if size:
        kwargs["size"] = size
    if color:
        kwargs["color"] = color
    cell.font = Font(**kwargs)


def add_sheet(data: dict) -> str:
    target_file = pathlib.Path(data["target_file"])
    sheet_name  = data["sheet_name"]
    fac         = data["fac"]
    id_lot      = data["id_lot"]
    approved    = data["approved"]
    motif       = data.get("motif")
    cumul_existant = float(data.get("cumul_existant", 0))
    budget_total   = float(data.get("budget_total", 0))
    montant        = float(fac["montant_ttc"])
    today          = date.today().strftime("%d/%m/%Y")

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

    # ── FICHE NAVETTE ─────────────────────────────────────────────────────────
    GREEN  = "1E8449"
    RED    = "C0392B"

    ws["A1"] = "FICHE NAVETTE — PROJET renovation_2026"
    ws["A1"].font = Font(bold=True, size=13)
    ws.merge_cells("A1:B1")

    ws["A3"] = "MOE";  ws["B3"] = "RenovBat"
    ws["A4"] = "MOA";  ws["B4"] = "IMMOSOCIAL_69"

    ws["A6"]  = "Référence facture";   ws["B6"]  = fac["numero"]
    ws["A7"]  = "Date de la facture";  ws["B7"]  = fac["date"]
    ws["A8"]  = "Émetteur";            ws["B8"]  = fac["societe"]
    ws["A9"]  = "Lot concerné";        ws["B9"]  = id_lot
    ws["A10"] = "Montant TTC"
    ws["B10"] = montant
    _fmt_eur(ws["B10"])

    if approved:
        ws["A12"] = "✓ FACTURE APPROUVÉE"
        ws["A12"].font = Font(bold=True, color=GREEN)
        ws.merge_cells("A12:B12")
        ws["A13"] = "Date d'approbation"; ws["B13"] = today
        ws["A14"] = "Approuvé par";       ws["B14"] = "RenovBat"
    else:
        ws["A12"] = "✗ FACTURE REJETÉE"
        ws["A12"].font = Font(bold=True, color=RED)
        ws.merge_cells("A12:B12")
        ws["A13"] = "Date de traitement"; ws["B13"] = today
        ws["A14"] = "Motif du rejet";     ws["B14"] = motif or ""
        ws["A15"] = "Traité par";         ws["B15"] = "RenovBat"

    # ── BON DE PAIEMENT (uniquement si approuvée) ─────────────────────────────
    if approved:
        nouveau_cumul = cumul_existant + montant

        ws["A17"] = "BON DE PAIEMENT — PROJET renovation_2026"
        ws["A17"].font = Font(bold=True, size=13)
        ws.merge_cells("A17:B17")

        ws["A19"] = "Montant global prévu pour le lot"
        ws["B19"] = budget_total
        _fmt_eur(ws["B19"])

        ws["A20"] = "Situations précédentes"
        ws["B20"] = cumul_existant
        _fmt_eur(ws["B20"])

        ws["A21"] = "Présente situation"
        ws["B21"] = montant
        _fmt_eur(ws["B21"])

        ws["A23"] = "Nouveau cumul"
        ws["B23"] = nouveau_cumul
        ws["B23"].font = Font(bold=True)
        _fmt_eur(ws["B23"])

        ws["A24"] = "Reste à régler"
        ws["B24"] = budget_total - nouveau_cumul
        _fmt_eur(ws["B24"])

        ws["A26"] = "Date d'émission";  ws["B26"] = today
        ws["A27"] = "Établi par";       ws["B27"] = "RenovBat (MOE)"
        ws["A28"] = "À destination de"; ws["B28"] = "IMMOSOCIAL_69 (MOA)"

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
