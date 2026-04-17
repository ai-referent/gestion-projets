#!/usr/bin/env python3
"""Génère les 3 factures PDF du projet renovation_2026 sans librairie externe."""
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "factures"


def make_stream(content: str) -> bytes:
    return content.encode("latin-1", errors="replace")


def build_pdf(pages_content: list[str]) -> bytes:
    objects: list[bytes] = []
    stream_ids = []
    page_ids = []

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


FACTURES = {
    "FAC-2026-001.pdf": """BT
/F2 16 Tf
180 800 Td
(Platr'O'Matic SARL) Tj
/F1 10 Tf
0 -20 Td
(42 rue du Crepissage - 75011 Paris | SIRET : 123 456 789 00012) Tj
/F2 13 Tf
-80 -50 Td
(FACTURE) Tj
/F1 11 Tf
0 -25 Td
(Numero       : FAC-2026-001) Tj
0 -18 Td
(Date         : 15 mars 2026) Tj
0 -18 Td
(Client       : RenovBat - 8 avenue des Batisseurs, 69000 Lyon) Tj
/F2 11 Tf
0 -40 Td
(DESIGNATION) Tj
200 0 Td
(MONTANT HT) Tj
/F1 11 Tf
-200 -20 Td
(Travaux d'aplanissement de facade - Lot A) Tj
200 0 Td
(10 416,67 EUR) Tj
-200 -35 Td
(TVA 20 %) Tj
200 0 Td
(  2 083,33 EUR) Tj
/F2 12 Tf
-200 -25 Td
(TOTAL TTC) Tj
200 0 Td
(12 500,00 EUR) Tj
/F1 9 Tf
-200 -60 Td
(Paiement a 30 jours.) Tj
ET""",
    "FAC-2026-002.pdf": """BT
/F2 14 Tf
350 820 Td
(RevetoPower) Tj
/F1 9 Tf
0 -15 Td
(& Associes) Tj
0 -13 Td
(17 impasse du Carreau) Tj
0 -13 Td
(13001 Marseille) Tj
0 -13 Td
(contact@revetopower.fr) Tj
/F1 10 Tf
50 -50 Td
(Destinataire : RenovBat) Tj
0 -14 Td
(             8 avenue des Batisseurs) Tj
0 -14 Td
(             69000 Lyon) Tj
/F2 18 Tf
0 -50 Td
(FACTURE N FAC-2026-002) Tj
/F1 11 Tf
0 -25 Td
(Date d'emission : 28 mars 2026) Tj
/F2 11 Tf
0 -40 Td
(Prestation) Tj
250 0 Td
(Montant TTC) Tj
/F1 11 Tf
-250 -20 Td
(Pose revetement isolant - facade Nord et Sud) Tj
250 0 Td
( 15 625,00 EUR) Tj
-250 -18 Td
(Fourniture materiaux incluse) Tj
250 0 Td
(  3 125,00 EUR) Tj
/F2 12 Tf
-250 -30 Td
(TOTAL TTC) Tj
250 0 Td
( 18 750,00 EUR) Tj
/F1 8 Tf
-250 -70 Td
(Conditions : net 30 jours - Pas d'escompte) Tj
ET""",
    "FAC-2026-003.pdf": """BT
/F2 20 Tf
50 820 Td
(ChaudoMagic SAS) Tj
/F1 9 Tf
0 -18 Td
(Specialists du chauffage et au-dela) Tj
0 -12 Td
(3 boulevard de la Vapeur - 31000 Toulouse) Tj
0 -12 Td
(SIRET : 987 654 321 00034 | TVA : FR12987654321) Tj
/F2 14 Tf
0 -45 Td
(== FACTURE ==) Tj
/F1 11 Tf
0 -22 Td
(Ref. facture  : FAC-2026-003) Tj
0 -16 Td
(Date          : 5 avril 2026) Tj
0 -16 Td
(Ref. client   : RENOVBAT-LYON-001) Tj
0 -16 Td
(Objet         : Renovation complete de la chaudiere centrale) Tj
/F2 11 Tf
0 -35 Td
(Detail des travaux :) Tj
/F1 11 Tf
0 -18 Td
(  - Depose ancienne chaudiere      2 500,00 EUR HT) Tj
0 -16 Td
(  - Fourniture chaudiere neuve     8 000,00 EUR HT) Tj
0 -16 Td
(  - Pose et raccordement           4 000,00 EUR HT) Tj
0 -16 Td
(  - Mise en service et tests       1 000,00 EUR HT) Tj
0 -16 Td
(  - Deplacements et divers           583,33 EUR HT) Tj
/F1 11 Tf
0 -25 Td
(Sous-total HT :                   16 083,33 EUR) Tj
0 -16 Td
(TVA 20 %  :                        3 216,67 EUR) Tj
/F2 12 Tf
0 -20 Td
(TOTAL TTC :                       19 300,00 EUR) Tj
/F1 8 Tf
0 -55 Td
(Garantie 2 ans pieces et main d'oeuvre - Paiement 30 jours fin de mois) Tj
ET"""
}


if __name__ == "__main__":
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for filename, page_content in FACTURES.items():
        path = OUTPUT_DIR / filename
        path.write_bytes(build_pdf([page_content]))
        print(f"Créé : {path}")
    print("Terminé.")
