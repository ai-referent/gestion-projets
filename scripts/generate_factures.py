#!/usr/bin/env python3
"""Génère les factures PDF au format Factur-X BASIC — Projet renovation_2026."""
import argparse
import hashlib
import json
from pathlib import Path

OUTPUT_DIR = Path(__file__).parent.parent / "data" / "factures"

# Fixed object IDs for single-page Factur-X PDF layout
_CONTENT_ID  = 1  # page content stream
_XMP_ID      = 2  # XMP metadata stream
_EF_ID       = 3  # EmbeddedFile stream (factur-x.xml)
_FS_ID       = 4  # Filespec dictionary
_PAGE_ID     = 5  # Page object
_PAGES_ID    = 6  # Pages tree
_CATALOG_ID  = 7  # Catalog

_MONTHS_FR = [
    "", "janvier", "fevrier", "mars", "avril", "mai", "juin",
    "juillet", "aout", "septembre", "octobre", "novembre", "decembre",
]

# Static XMP metadata declaring Factur-X BASIC / PDF-A-3B conformance
_XMP = (
    '﻿<?xpacket begin="﻿" id="W5M0MpCehiHzreSzNTczkc9d"?>'
    '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
    '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
    '<rdf:Description rdf:about=""'
    ' xmlns:pdfaid="http://www.aiim.org/pdfa/ns/id/"'
    ' xmlns:fx="urn:factur-x:pdfa:CrossIndustryDocument:invoice:1p0#">'
    "<pdfaid:part>3</pdfaid:part>"
    "<pdfaid:conformance>B</pdfaid:conformance>"
    "<fx:DocumentType>INVOICE</fx:DocumentType>"
    "<fx:DocumentFileName>factur-x.xml</fx:DocumentFileName>"
    "<fx:Version>1.0</fx:Version>"
    "<fx:ConformanceLevel>BASIC</fx:ConformanceLevel>"
    "</rdf:Description>"
    "</rdf:RDF>"
    "</x:xmpmeta>"
    '<?xpacket end="w"?>'
).encode("utf-8")

BUYER = {
    "name": "RenovBat",
    "address": "8 avenue des Batisseurs",
    "postcode": "69000",
    "city": "Lyon",
    "country": "FR",
}

INVOICES = [
    {
        "filename": "FAC-2026-001.pdf",
        "id": "FAC-2026-001",
        "date": "20260315",
        "due_date": "20260414",
        "lot": "isolation_thermique",
        "seller": {
            "name": "Platr'O'Matic SARL",
            "siret": "00000000000001",
            "address": "42 rue du Crepissage",
            "postcode": "75011",
            "city": "Paris",
            "country": "FR",
        },
        "lines": [
            {
                "id": "1",
                "desc": "Travaux d'aplanissement de facade - Lot A",
                "qty": 1.0,
                "unit_price": 10416.67,
                "vat_rate": 20.0,
                "total_ht": 10416.67,
            },
        ],
        "total_ht": 10416.67,
        "total_vat": 2083.33,
        "total_ttc": 12500.00,
    },
    {
        "filename": "FAC-2026-002.pdf",
        "id": "FAC-2026-002",
        "date": "20260328",
        "due_date": "20260427",
        "lot": "isolation_acoustique",
        "seller": {
            "name": "RevetoPower & Associes",
            "siret": "00000000000002",
            "address": "17 impasse du Carreau",
            "postcode": "13001",
            "city": "Marseille",
            "country": "FR",
        },
        "lines": [
            {
                "id": "1",
                "desc": "Pose revetement isolant - facade Nord et Sud",
                "qty": 1.0,
                "unit_price": 13020.83,
                "vat_rate": 20.0,
                "total_ht": 13020.83,
            },
            {
                "id": "2",
                "desc": "Fourniture materiaux incluse",
                "qty": 1.0,
                "unit_price": 2604.17,
                "vat_rate": 20.0,
                "total_ht": 2604.17,
            },
        ],
        "total_ht": 15625.00,
        "total_vat": 3125.00,
        "total_ttc": 18750.00,
    },
    {
        "filename": "FAC-2026-003.pdf",
        "id": "FAC-2026-003",
        "date": "20260405",
        "due_date": "20260531",
        "lot": "renovation_chauffage",
        "seller": {
            "name": "ChaudoMagic SAS",
            "siret": "00000000000003",
            "address": "3 boulevard de la Vapeur",
            "postcode": "31000",
            "city": "Toulouse",
            "country": "FR",
        },
        "lines": [
            {"id": "1", "desc": "Depose ancienne chaudiere",  "qty": 1.0, "unit_price": 2500.00, "vat_rate": 20.0, "total_ht": 2500.00},
            {"id": "2", "desc": "Fourniture chaudiere neuve", "qty": 1.0, "unit_price": 8000.00, "vat_rate": 20.0, "total_ht": 8000.00},
            {"id": "3", "desc": "Pose et raccordement",       "qty": 1.0, "unit_price": 4000.00, "vat_rate": 20.0, "total_ht": 4000.00},
            {"id": "4", "desc": "Mise en service et tests",   "qty": 1.0, "unit_price": 1000.00, "vat_rate": 20.0, "total_ht": 1000.00},
            {"id": "5", "desc": "Deplacements et divers",     "qty": 1.0, "unit_price":  583.33, "vat_rate": 20.0, "total_ht":  583.33},
        ],
        "total_ht": 16083.33,
        "total_vat":  3216.67,
        "total_ttc": 19300.00,
    },
]


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fmt_amt(v: float) -> str:
    """Format float as French currency string: 12500.0 → '12 500,00'."""
    integer = int(v)
    cents = round(v * 100) % 100
    return f"{integer:,}".replace(",", " ") + f",{cents:02d}"


def _xml_escape(s: str) -> str:
    return (s.replace("&", "&amp;").replace("<", "&lt;")
             .replace(">", "&gt;").replace('"', "&quot;").replace("'", "&apos;"))


def _fmt_date_fr(yyyymmdd: str) -> str:
    """'20260315' → '15 mars 2026'."""
    d, m, y = int(yyyymmdd[6:8]), int(yyyymmdd[4:6]), yyyymmdd[:4]
    return f"{d} {_MONTHS_FR[m]} {y}"


# ── PDF page content ─────────────────────────────────────────────────────────

def make_page_content(inv: dict) -> str:
    """Generate PDF BT…ET content stream from invoice data."""
    s = inv["seller"]
    addr = s.get("address", "")
    if s.get("postcode") and s.get("city"):
        addr += f" - {s['postcode']} {s['city']}"
    siret = f"SIRET : {s['siret']}" if s.get("siret") else ""

    rows = [
        "BT",
        "/F2 16 Tf", "50 820 Td",
        f"({s['name']}) Tj",
        "/F1 10 Tf", "0 -18 Td",
        f"({addr}) Tj",
        "0 -14 Td",
        f"({siret}) Tj",
        "/F2 14 Tf", "0 -45 Td",
        "(FACTURE) Tj",
        "/F1 11 Tf", "0 -22 Td",
        f"(Numero        : {inv['id']}) Tj",
        "0 -16 Td",
        f"(Date          : {_fmt_date_fr(inv['date'])}) Tj",
        "0 -16 Td",
        f"(Client        : {BUYER['name']} - {BUYER['address']}, {BUYER['postcode']} {BUYER['city']}) Tj",
        "0 -16 Td",
        f"(Lot           : {inv.get('lot', '')}) Tj",
        "/F2 11 Tf", "0 -35 Td",
        "(Designation) Tj",
        "300 0 Td",
        "(Montant HT) Tj",
    ]

    dy = -20
    for item in inv["lines"]:
        rows += [
            "/F1 11 Tf",
            f"-300 {dy} Td",
            f"({item['desc']}) Tj",
            "300 0 Td",
            f"({_fmt_amt(item['total_ht'])} EUR) Tj",
        ]
        dy = -16

    vat_rate = inv["lines"][0]["vat_rate"] if inv["lines"] else 20.0
    rows += [
        f"-300 {dy} Td",
        f"(TVA {vat_rate:.0f}%) Tj",
        "300 0 Td",
        f"({_fmt_amt(inv['total_vat'])} EUR) Tj",
        "/F2 12 Tf",
        "-300 -22 Td",
        "(TOTAL TTC) Tj",
        "300 0 Td",
        f"({_fmt_amt(inv['total_ttc'])} EUR) Tj",
        "/F1 9 Tf",
        "-300 -60 Td",
        "(Paiement a 30 jours.) Tj",
        "ET",
    ]
    return "\n".join(rows)


# ── Factur-X XML (CII BASIC profile) ─────────────────────────────────────────

def build_facturx_xml(inv: dict) -> bytes:
    s = inv["seller"]
    vat_rate = inv["lines"][0]["vat_rate"] if inv["lines"] else 20.0

    siret_block = ""
    if s.get("siret"):
        siret_block = (
            "      <ram:SpecifiedLegalOrganization>\n"
            f'        <ram:ID schemeID="0002">{s["siret"]}</ram:ID>\n'
            "      </ram:SpecifiedLegalOrganization>\n"
        )

    lines_xml = ""
    for item in inv["lines"]:
        lines_xml += (
            "  <ram:IncludedSupplyChainTradeLineItem>\n"
            "    <ram:AssociatedDocumentLineDocument>\n"
            f"      <ram:LineID>{item['id']}</ram:LineID>\n"
            "    </ram:AssociatedDocumentLineDocument>\n"
            "    <ram:SpecifiedTradeProduct>\n"
            f"      <ram:Name>{_xml_escape(item['desc'])}</ram:Name>\n"
            "    </ram:SpecifiedTradeProduct>\n"
            "    <ram:SpecifiedLineTradeAgreement>\n"
            "      <ram:NetPriceProductTradePrice>\n"
            f"        <ram:ChargeAmount>{item['unit_price']:.2f}</ram:ChargeAmount>\n"
            "      </ram:NetPriceProductTradePrice>\n"
            "    </ram:SpecifiedLineTradeAgreement>\n"
            "    <ram:SpecifiedLineTradeDelivery>\n"
            f'      <ram:BilledQuantity unitCode="C62">{item["qty"]:.2f}</ram:BilledQuantity>\n'
            "    </ram:SpecifiedLineTradeDelivery>\n"
            "    <ram:SpecifiedLineTradeSettlement>\n"
            "      <ram:ApplicableTradeTax>\n"
            "        <ram:TypeCode>VAT</ram:TypeCode>\n"
            "        <ram:CategoryCode>S</ram:CategoryCode>\n"
            f"        <ram:RateApplicablePercent>{item['vat_rate']:.2f}</ram:RateApplicablePercent>\n"
            "      </ram:ApplicableTradeTax>\n"
            "      <ram:SpecifiedTradeSettlementLineMonetarySummation>\n"
            f"        <ram:LineTotalAmount>{item['total_ht']:.2f}</ram:LineTotalAmount>\n"
            "      </ram:SpecifiedTradeSettlementLineMonetarySummation>\n"
            "    </ram:SpecifiedLineTradeSettlement>\n"
            "  </ram:IncludedSupplyChainTradeLineItem>\n"
        )

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        "<rsm:CrossIndustryInvoice\n"
        '  xmlns:rsm="urn:un:unece:uncefact:data:standard:CrossIndustryInvoice:100"\n'
        '  xmlns:ram="urn:un:unece:uncefact:data:standard:ReusableAggregateBusinessInformationEntity:100"\n'
        '  xmlns:udt="urn:un:unece:uncefact:data:standard:UnqualifiedDataType:100">\n'
        "  <rsm:ExchangedDocumentContext>\n"
        "    <ram:GuidelineSpecifiedDocumentContextParameter>\n"
        "      <ram:ID>urn:factur-x.eu:1p0:basic</ram:ID>\n"
        "    </ram:GuidelineSpecifiedDocumentContextParameter>\n"
        "  </rsm:ExchangedDocumentContext>\n"
        "  <rsm:ExchangedDocument>\n"
        f"    <ram:ID>{inv['id']}</ram:ID>\n"
        "    <ram:TypeCode>380</ram:TypeCode>\n"
        "    <ram:IssueDateTime>\n"
        f'      <udt:DateTimeString format="102">{inv["date"]}</udt:DateTimeString>\n'
        "    </ram:IssueDateTime>\n"
        "  </rsm:ExchangedDocument>\n"
        "  <rsm:SupplyChainTradeTransaction>\n"
        + lines_xml
        + "    <ram:ApplicableHeaderTradeAgreement>\n"
        "      <ram:SellerTradeParty>\n"
        f"        <ram:Name>{_xml_escape(s['name'])}</ram:Name>\n"
        + siret_block
        + "        <ram:PostalTradeAddress>\n"
        f"          <ram:LineOne>{_xml_escape(s.get('address', ''))}</ram:LineOne>\n"
        f"          <ram:PostcodeCode>{s.get('postcode', '')}</ram:PostcodeCode>\n"
        f"          <ram:CityName>{_xml_escape(s.get('city', ''))}</ram:CityName>\n"
        f"          <ram:CountryID>{s.get('country', 'FR')}</ram:CountryID>\n"
        "        </ram:PostalTradeAddress>\n"
        "      </ram:SellerTradeParty>\n"
        "      <ram:BuyerTradeParty>\n"
        f"        <ram:Name>{_xml_escape(BUYER['name'])}</ram:Name>\n"
        "        <ram:PostalTradeAddress>\n"
        f"          <ram:LineOne>{_xml_escape(BUYER['address'])}</ram:LineOne>\n"
        f"          <ram:PostcodeCode>{BUYER['postcode']}</ram:PostcodeCode>\n"
        f"          <ram:CityName>{_xml_escape(BUYER['city'])}</ram:CityName>\n"
        f"          <ram:CountryID>{BUYER['country']}</ram:CountryID>\n"
        "        </ram:PostalTradeAddress>\n"
        "      </ram:BuyerTradeParty>\n"
        "    </ram:ApplicableHeaderTradeAgreement>\n"
        "    <ram:ApplicableHeaderTradeDelivery/>\n"
        "    <ram:ApplicableHeaderTradeSettlement>\n"
        "      <ram:InvoiceCurrencyCode>EUR</ram:InvoiceCurrencyCode>\n"
        "      <ram:ApplicableTradeTax>\n"
        f"        <ram:CalculatedAmount>{inv['total_vat']:.2f}</ram:CalculatedAmount>\n"
        "        <ram:TypeCode>VAT</ram:TypeCode>\n"
        f"        <ram:BasisAmount>{inv['total_ht']:.2f}</ram:BasisAmount>\n"
        "        <ram:CategoryCode>S</ram:CategoryCode>\n"
        f"        <ram:RateApplicablePercent>{vat_rate:.2f}</ram:RateApplicablePercent>\n"
        "      </ram:ApplicableTradeTax>\n"
        "      <ram:SpecifiedTradePaymentTerms>\n"
        "        <ram:DueDateDateTime>\n"
        f'          <udt:DateTimeString format="102">{inv["due_date"]}</udt:DateTimeString>\n'
        "        </ram:DueDateDateTime>\n"
        "      </ram:SpecifiedTradePaymentTerms>\n"
        "      <ram:SpecifiedTradeSettlementHeaderMonetarySummation>\n"
        f"        <ram:LineTotalAmount>{inv['total_ht']:.2f}</ram:LineTotalAmount>\n"
        f"        <ram:TaxBasisTotalAmount>{inv['total_ht']:.2f}</ram:TaxBasisTotalAmount>\n"
        f'        <ram:TaxTotalAmount currencyID="EUR">{inv["total_vat"]:.2f}</ram:TaxTotalAmount>\n'
        f"        <ram:GrandTotalAmount>{inv['total_ttc']:.2f}</ram:GrandTotalAmount>\n"
        f"        <ram:DuePayableAmount>{inv['total_ttc']:.2f}</ram:DuePayableAmount>\n"
        "      </ram:SpecifiedTradeSettlementHeaderMonetarySummation>\n"
        "    </ram:ApplicableHeaderTradeSettlement>\n"
        "  </rsm:SupplyChainTradeTransaction>\n"
        "</rsm:CrossIndustryInvoice>\n"
    )
    return xml.encode("utf-8")


# ── PDF builder ───────────────────────────────────────────────────────────────

def build_pdf(page_content: str, xml_bytes: bytes) -> bytes:
    """Build a PDF 1.7 file with Factur-X XML embedded as an associated file."""
    content_data = page_content.encode("latin-1", errors="replace")
    md5_hex = hashlib.md5(xml_bytes).hexdigest()
    uf_hex = "FEFF" + "".join(f"{ord(c):04X}" for c in "factur-x.xml")

    def _stream(header: bytes, data: bytes) -> bytes:
        return header + b"\nstream\n" + data + b"\nendstream"

    objs: dict[int, bytes] = {
        _CONTENT_ID: _stream(
            f"<< /Length {len(content_data)} >>".encode(), content_data
        ),
        _XMP_ID: _stream(
            f"<< /Type /Metadata /Subtype /XML /Length {len(_XMP)} >>".encode(), _XMP
        ),
        _EF_ID: _stream(
            (
                f"<< /Type /EmbeddedFile /Subtype /text#2Fxml"
                f" /Params << /Size {len(xml_bytes)} /CheckSum <{md5_hex}> >>"
                f" /Length {len(xml_bytes)} >>"
            ).encode(),
            xml_bytes,
        ),
        _FS_ID: (
            f"<< /Type /Filespec /F (factur-x.xml) /UF <{uf_hex}>"
            f" /Desc (Factur-X Invoice)"
            f" /EF << /F {_EF_ID} 0 R /UF {_EF_ID} 0 R >>"
            f" /AFRelationship /Data >>"
        ).encode(),
        _PAGE_ID: (
            f"<< /Type /Page /Parent {_PAGES_ID} 0 R"
            f" /Resources << /Font <<"
            f" /F1 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>"
            f" /F2 << /Type /Font /Subtype /Type1 /BaseFont /Helvetica-Bold >>"
            f" >> >>"
            f" /MediaBox [0 0 595 842] /Contents {_CONTENT_ID} 0 R >>"
        ).encode(),
        _PAGES_ID: f"<< /Type /Pages /Kids [{_PAGE_ID} 0 R] /Count 1 >>".encode(),
        _CATALOG_ID: (
            f"<< /Type /Catalog /Pages {_PAGES_ID} 0 R"
            f" /Metadata {_XMP_ID} 0 R"
            f" /Names << /EmbeddedFiles << /Names [(factur-x.xml) {_FS_ID} 0 R] >> >>"
            f" /AF [{_FS_ID} 0 R]"
            f" /MarkInfo << /Marked true >> >>"
        ).encode(),
    }

    body = b"%PDF-1.7\n%\xe2\xe3\xcf\xd3\n"
    offsets: dict[int, int] = {}
    for obj_id in sorted(objs):
        offsets[obj_id] = len(body)
        body += f"{obj_id} 0 obj\n".encode() + objs[obj_id] + b"\nendobj\n"

    n = max(objs) + 1
    xref_pos = len(body)
    xref = f"xref\n0 {n}\n0000000000 65535 f \n"
    for i in range(1, n):
        xref += f"{offsets[i]:010d} 00000 n \n"
    trailer = (
        f"trailer\n<< /Size {n} /Root {_CATALOG_ID} 0 R >>\n"
        f"startxref\n{xref_pos}\n%%EOF\n"
    )
    return body + xref.encode() + trailer.encode()


# ── Public API ────────────────────────────────────────────────────────────────

def generate_invoice(inv: dict, output_dir: Path = OUTPUT_DIR) -> Path:
    """Generate a single Factur-X PDF and return its path."""
    if "due_date" not in inv:
        from datetime import datetime, timedelta
        due = datetime.strptime(inv["date"], "%Y%m%d") + timedelta(days=30)
        inv = {**inv, "due_date": due.strftime("%Y%m%d")}
    pdf_bytes = build_pdf(make_page_content(inv), build_facturx_xml(inv))
    out = output_dir / inv["filename"]
    out.write_bytes(pdf_bytes)
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description="Générateur de factures Factur-X")
    parser.add_argument(
        "--create", metavar="JSON",
        help="Créer une facture depuis un dict JSON (affiche le chemin du PDF créé)",
    )
    args = parser.parse_args()

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

    if args.create:
        inv = json.loads(args.create)
        out = generate_invoice(inv)
        print(str(out))
    else:
        for inv in INVOICES:
            out = generate_invoice(inv)
            print(f"Créé : {out}")
        print("Terminé.")


if __name__ == "__main__":
    main()
