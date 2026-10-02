#!/usr/bin/env python3
"""Generate a 50-case synthetic Indian IT/software invoice + PO benchmark.

Outputs:
  test_dataset/invoices/
  test_dataset/purchase_orders/
  test_dataset/ground_truth.json
  test_dataset/ground_truth.csv
  test_dataset/README.txt

All companies, GSTINs, addresses, document numbers, and transactions are synthetic.
"""

from __future__ import annotations

import csv
import json
import math
import random
import shutil
from dataclasses import dataclass, asdict
from datetime import date, timedelta
from pathlib import Path
from typing import Any

from PIL import Image, ImageDraw, ImageEnhance, ImageFilter, ImageFont
from reportlab.lib import colors
from reportlab.lib.enums import TA_RIGHT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak
)

SEED = 20260925
random.seed(SEED)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "test_dataset"
INVOICE_DIR = OUT / "invoices"
PO_DIR = OUT / "purchase_orders"
TMP_DIR = OUT / "_tmp"

BUYER = {
    "name": "BluePeak Digital Operations Pvt Ltd",
    "address": "42 Innovation Park, Whitefield, Bengaluru, Karnataka 560066",
    "state": "Karnataka",
    "state_code": "29",
    "gstin": "29AABCB1234C1Z7",  # synthetic
}

VENDORS = [
    {"name": "NimbleStack Technologies Pvt Ltd", "state": "Karnataka", "state_code": "29", "gstin": "29AACCN4101A1Z5", "city": "Bengaluru"},
    {"name": "CloudHarbor Systems Pvt Ltd", "state": "Maharashtra", "state_code": "27", "gstin": "27AACCC5202B1Z4", "city": "Pune"},
    {"name": "SecureOrbit Infotech Pvt Ltd", "state": "Telangana", "state_code": "36", "gstin": "36AACCS6303C1Z3", "city": "Hyderabad"},
    {"name": "DataSprout Solutions Pvt Ltd", "state": "Karnataka", "state_code": "29", "gstin": "29AACCD7404D1Z2", "city": "Bengaluru"},
    {"name": "VertexWave Software Services Pvt Ltd", "state": "Tamil Nadu", "state_code": "33", "gstin": "33AACCV8505E1Z1", "city": "Chennai"},
]

CATALOG = [
    ("Enterprise software licence - annual", "997331", 12000.00),
    ("Cloud platform subscription - monthly", "998315", 8500.00),
    ("Premium technical support", "998313", 25000.00),
    ("Implementation consulting", "998313", 18000.00),
    ("Cybersecurity monitoring service", "998313", 22000.00),
    ("User training workshop", "999293", 15000.00),
    ("API integration services", "998314", 20000.00),
    ("Data migration services", "998313", 17500.00),
    ("Managed database service", "998315", 11000.00),
    ("Application maintenance support", "998314", 16000.00),
]

SCENARIOS = (
    ["CLEAN_MATCH"] * 20
    + ["PRICE_VARIANCE"] * 5
    + ["QUANTITY_VARIANCE"] * 4
    + ["TAX_VARIANCE"] * 4
    + ["TOTAL_CALCULATION_ERROR"] * 3
    + ["UNMATCHED_LINE"] * 3
    + ["PO_NUMBER_MISMATCH"] * 2
    + ["VENDOR_MISMATCH"] * 2
    + ["DUPLICATE_INVOICE"] * 2
    + ["CURRENCY_MISMATCH"]
    + ["SCAN_CHALLENGE"]
    + ["IMAGE_CHALLENGE"]
    + ["MULTIPAGE_CHALLENGE"]
    + ["MULTIPLE_EXCEPTIONS"]
)
assert len(SCENARIOS) == 50

# 60% native PDF, 30% digital image, 10% scan-style image at the document level.
DOC_FORMATS = ["pdf"] * 60 + ["png"] * 20 + ["jpg"] * 10 + ["scan_jpg"] * 10
random.shuffle(DOC_FORMATS)


@dataclass
class Line:
    description: str
    sac: str
    quantity: float
    unit_price: float
    amount: float


def money(v: float) -> str:
    return f"{v:,.2f}"


def round2(v: float) -> float:
    return round(float(v) + 1e-9, 2)


def make_lines(case_no: int) -> list[Line]:
    rng = random.Random(SEED + case_no * 17)
    count = rng.randint(2, 5)
    selected = rng.sample(CATALOG, count)
    lines = []
    for desc, sac, base in selected:
        qty = rng.choice([1, 1, 2, 3, 5, 10])
        # Stable but varied price around catalog base.
        factor = rng.choice([0.9, 1.0, 1.05, 1.1])
        price = round2(base * factor)
        lines.append(Line(desc, sac, qty, price, round2(qty * price)))
    return lines


def totals(lines: list[Line], vendor_state: str, tax_override: float | None = None) -> dict[str, float]:
    subtotal = round2(sum(x.amount for x in lines))
    tax_rate = 0.18
    tax = round2(subtotal * tax_rate) if tax_override is None else round2(tax_override)
    if vendor_state == BUYER["state"]:
        cgst, sgst, igst = round2(tax / 2), round2(tax / 2), 0.0
    else:
        cgst, sgst, igst = 0.0, 0.0, tax
    return {
        "subtotal": subtotal,
        "tax_rate": tax_rate,
        "cgst": cgst,
        "sgst": sgst,
        "igst": igst,
        "tax": tax,
        "total": round2(subtotal + tax),
    }


def clone_lines(lines: list[Line]) -> list[Line]:
    return [Line(**asdict(x)) for x in lines]


def expected_exception_types(scenario: str) -> list[str]:
    return {
        "CLEAN_MATCH": [],
        "PRICE_VARIANCE": ["PRICE_VARIANCE", "LINE_AMOUNT_VARIANCE", "TOTAL_MISMATCH"],
        "QUANTITY_VARIANCE": ["QUANTITY_VARIANCE", "LINE_AMOUNT_VARIANCE", "TOTAL_MISMATCH"],
        "TAX_VARIANCE": ["TAX_VARIANCE", "TOTAL_MISMATCH"],
        "TOTAL_CALCULATION_ERROR": ["INVOICE_CALCULATION_ERROR", "TOTAL_MISMATCH"],
        "UNMATCHED_LINE": ["UNMATCHED_INVOICE_LINE", "TOTAL_MISMATCH"],
        "PO_NUMBER_MISMATCH": ["PO_NUMBER_MISMATCH"],
        "VENDOR_MISMATCH": ["VENDOR_MISMATCH"],
        "DUPLICATE_INVOICE": ["DUPLICATE_INVOICE"],
        "CURRENCY_MISMATCH": ["CURRENCY_MISMATCH"],
        "SCAN_CHALLENGE": [],
        "IMAGE_CHALLENGE": [],
        "MULTIPAGE_CHALLENGE": [],
        "MULTIPLE_EXCEPTIONS": ["PRICE_VARIANCE", "QUANTITY_VARIANCE", "LINE_AMOUNT_VARIANCE", "TAX_VARIANCE", "TOTAL_MISMATCH"],
    }[scenario]


def build_case(case_no: int, scenario: str) -> dict[str, Any]:
    rng = random.Random(SEED + case_no)
    vendor = dict(VENDORS[(case_no - 1) % len(VENDORS)])
    po_vendor = dict(vendor)
    invoice_lines = make_lines(case_no)
    po_lines = clone_lines(invoice_lines)
    invoice_date = date(2026, 4, 1) + timedelta(days=case_no * 2)
    po_date = invoice_date - timedelta(days=rng.randint(5, 30))
    po_number = f"PO-26-{case_no:04d}"
    invoice_number = f"{vendor['name'].split()[0][:3].upper()}/26-27/{case_no:04d}"
    invoice_po_number = po_number
    invoice_currency = po_currency = "INR"

    po_totals = totals(po_lines, po_vendor["state"])
    invoice_totals = totals(invoice_lines, vendor["state"])

    if scenario == "PRICE_VARIANCE":
        invoice_lines[0].unit_price = round2(invoice_lines[0].unit_price * 1.08)
        invoice_lines[0].amount = round2(invoice_lines[0].quantity * invoice_lines[0].unit_price)
        invoice_totals = totals(invoice_lines, vendor["state"])
    elif scenario == "QUANTITY_VARIANCE":
        invoice_lines[0].quantity += 1
        invoice_lines[0].amount = round2(invoice_lines[0].quantity * invoice_lines[0].unit_price)
        invoice_totals = totals(invoice_lines, vendor["state"])
    elif scenario == "TAX_VARIANCE":
        correct = totals(invoice_lines, vendor["state"])
        invoice_totals = totals(invoice_lines, vendor["state"], tax_override=correct["tax"] + 500.00)
    elif scenario == "TOTAL_CALCULATION_ERROR":
        invoice_totals = totals(invoice_lines, vendor["state"])
        invoice_totals["total"] = round2(invoice_totals["total"] + 750.00)
    elif scenario == "UNMATCHED_LINE":
        invoice_lines.append(Line("Additional onsite support", "998313", 1, 12000.00, 12000.00))
        invoice_totals = totals(invoice_lines, vendor["state"])
    elif scenario == "PO_NUMBER_MISMATCH":
        invoice_po_number = f"PO-26-{case_no + 7000:04d}"
    elif scenario == "VENDOR_MISMATCH":
        po_vendor = dict(VENDORS[case_no % len(VENDORS)])
        if po_vendor["name"] == vendor["name"]:
            po_vendor = dict(VENDORS[(case_no + 1) % len(VENDORS)])
        po_totals = totals(po_lines, po_vendor["state"])
    elif scenario == "DUPLICATE_INVOICE":
        # Pair 44 duplicates 43, pair 45 duplicates 44. Ground truth explicitly records it.
        invoice_number = "DUP/26-27/0001"
    elif scenario == "CURRENCY_MISMATCH":
        invoice_currency = "USD"
    elif scenario == "MULTIPLE_EXCEPTIONS":
        invoice_lines[0].quantity += 2
        invoice_lines[0].unit_price = round2(invoice_lines[0].unit_price * 1.12)
        invoice_lines[0].amount = round2(invoice_lines[0].quantity * invoice_lines[0].unit_price)
        correct = totals(invoice_lines, vendor["state"])
        invoice_totals = totals(invoice_lines, vendor["state"], tax_override=correct["tax"] + 1000.00)

    return {
        "case_id": f"CASE-{case_no:03d}",
        "category": "IT Software & Technology Services",
        "scenario": scenario,
        "expected_decision": "MATCH" if not expected_exception_types(scenario) else "EXCEPTION",
        "expected_exceptions": expected_exception_types(scenario),
        "invoice": {
            "vendor": vendor,
            "invoice_number": invoice_number,
            "invoice_date": invoice_date.isoformat(),
            "po_number": invoice_po_number,
            "currency": invoice_currency,
            "lines": [asdict(x) for x in invoice_lines],
            **invoice_totals,
        },
        "purchase_order": {
            "vendor": po_vendor,
            "po_number": po_number,
            "po_date": po_date.isoformat(),
            "currency": po_currency,
            "lines": [asdict(x) for x in po_lines],
            **po_totals,
        },
    }


def styles():
    ss = getSampleStyleSheet()
    ss.add(ParagraphStyle(name="SmallRight", parent=ss["Normal"], fontSize=8, leading=10, alignment=TA_RIGHT))
    ss.add(ParagraphStyle(name="Tiny", parent=ss["Normal"], fontSize=7, leading=9))
    return ss


def render_pdf(case: dict[str, Any], kind: str, path: Path, template: int) -> None:
    ss = styles()
    data = case["invoice"] if kind == "invoice" else case["purchase_order"]
    vendor = data["vendor"]
    is_invoice = kind == "invoice"
    title = "TAX INVOICE" if is_invoice else "PURCHASE ORDER"
    doc_no = data["invoice_number"] if is_invoice else data["po_number"]
    doc_date = data["invoice_date"] if is_invoice else data["po_date"]

    doc = SimpleDocTemplate(str(path), pagesize=A4, rightMargin=15*mm, leftMargin=15*mm, topMargin=14*mm, bottomMargin=14*mm)
    story = []
    if template % 2 == 0:
        story.append(Paragraph(f"<b>{title}</b>", ss["Title"]))
        story.append(Paragraph(vendor["name"] if is_invoice else BUYER["name"], ss["Heading2"]))
    else:
        header = Table([[Paragraph(f"<b>{vendor['name'] if is_invoice else BUYER['name']}</b>", ss["Heading2"]), Paragraph(f"<b>{title}</b>", ss["Title"])]], colWidths=[100*mm, 75*mm])
        story.append(header)

    issuer = vendor if is_invoice else BUYER
    story += [
        Paragraph(f"{issuer.get('city','Bengaluru')}, {issuer['state']} | GSTIN: {issuer['gstin']}", ss["Normal"]),
        Spacer(1, 5*mm),
    ]
    if is_invoice:
        meta = [["Invoice No.", doc_no, "Invoice Date", doc_date], ["PO Number", data["po_number"], "Currency", data["currency"]]]
        party = f"Bill To: {BUYER['name']}<br/>{BUYER['address']}<br/>GSTIN: {BUYER['gstin']}"
    else:
        meta = [["PO Number", doc_no, "PO Date", doc_date], ["Currency", data["currency"], "Category", case["category"]]]
        party = f"Supplier: {vendor['name']}<br/>{vendor.get('city','')}, {vendor['state']}<br/>GSTIN: {vendor['gstin']}"
    mt = Table(meta, colWidths=[28*mm, 58*mm, 28*mm, 58*mm])
    mt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.4,colors.grey),("BACKGROUND",(0,0),(0,-1),colors.whitesmoke),("BACKGROUND",(2,0),(2,-1),colors.whitesmoke),("FONTSIZE",(0,0),(-1,-1),8),("VALIGN",(0,0),(-1,-1),"MIDDLE")]))
    story += [mt, Spacer(1,4*mm), Paragraph(party, ss["Normal"]), Spacer(1,5*mm)]

    rows = [["#", "Description", "SAC", "Qty", "Unit Price", "Amount"]]
    for i, line in enumerate(data["lines"], 1):
        rows.append([str(i), line["description"], line["sac"], str(line["quantity"]), money(line["unit_price"]), money(line["amount"])])
    table = Table(rows, colWidths=[8*mm, 72*mm, 20*mm, 14*mm, 28*mm, 30*mm], repeatRows=1)
    table.setStyle(TableStyle([
        ("BACKGROUND",(0,0),(-1,0),colors.HexColor("#E9EEF7") if template < 3 else colors.whitesmoke),
        ("GRID",(0,0),(-1,-1),0.35,colors.grey), ("FONTSIZE",(0,0),(-1,-1),7.5),
        ("ALIGN",(3,1),(-1,-1),"RIGHT"), ("VALIGN",(0,0),(-1,-1),"TOP"),
        ("TOPPADDING",(0,0),(-1,-1),5), ("BOTTOMPADDING",(0,0),(-1,-1),5),
    ]))
    story.append(table)

    if case["scenario"] == "MULTIPAGE_CHALLENGE" and is_invoice:
        story += [PageBreak(), Paragraph("Continuation / Service Details", ss["Heading2"]), Paragraph("Supporting service schedule for the above invoice. This page intentionally makes the invoice multi-page for extraction testing.", ss["Normal"]), Spacer(1, 120*mm)]

    t = data
    tax_rows = [["Subtotal", money(t["subtotal"])]]
    if vendor["state"] == BUYER["state"]:
        tax_rows += [["CGST @ 9%", money(t["cgst"])], ["SGST @ 9%", money(t["sgst"])]]
    else:
        tax_rows += [["IGST @ 18%", money(t["igst"])]]
    tax_rows += [["Total Tax", money(t["tax"])], ["Grand Total", f"{t['currency']} {money(t['total'])}"]]
    tt = Table(tax_rows, colWidths=[45*mm, 38*mm], hAlign="RIGHT")
    tt.setStyle(TableStyle([("GRID",(0,0),(-1,-1),0.35,colors.grey),("ALIGN",(1,0),(-1,-1),"RIGHT"),("FONTNAME",(0,-1),(-1,-1),"Helvetica-Bold"),("BACKGROUND",(0,-1),(-1,-1),colors.whitesmoke),("FONTSIZE",(0,0),(-1,-1),8)]))
    story += [Spacer(1,5*mm), tt, Spacer(1,7*mm)]
    footer = "Computer-generated document for synthetic testing only. No real commercial transaction."
    story.append(Paragraph(footer, ss["Tiny"]))
    doc.build(story)


def pdf_to_image(pdf_path: Path, image_path: Path, scan: bool = False) -> None:
    # Uses PyMuPDF already present in the invoice-agent project.
    import pymupdf
    pdf = pymupdf.open(pdf_path)
    page = pdf[0]
    pix = page.get_pixmap(matrix=pymupdf.Matrix(1.65, 1.65), alpha=False)
    temp_png = TMP_DIR / (image_path.stem + "_render.png")
    pix.save(str(temp_png))
    img = Image.open(temp_png).convert("RGB")

    if scan:
        rng = random.Random(SEED + sum(map(ord, image_path.name)))
        angle = rng.choice([-2.2, -1.3, 1.1, 1.8])
        img = img.rotate(angle, expand=True, fillcolor="white")
        img = ImageEnhance.Contrast(img).enhance(0.88)
        img = ImageEnhance.Brightness(img).enhance(1.04)
        img = img.filter(ImageFilter.GaussianBlur(radius=0.35))
        # light deterministic scan streaks/noise
        draw = ImageDraw.Draw(img)
        for _ in range(18):
            y = rng.randrange(0, img.height)
            shade = rng.randrange(225, 245)
            draw.line((0, y, img.width, y), fill=(shade, shade, shade), width=1)
        img = img.resize((max(900, int(img.width * 0.82)), max(1200, int(img.height * 0.82))))

    suffix = image_path.suffix.lower()
    if suffix == ".jpg":
        img.save(image_path, "JPEG", quality=72 if scan else 90, optimize=True)
    else:
        img.save(image_path, "PNG", optimize=True)


def output_document(case: dict[str, Any], kind: str, fmt: str, template: int) -> str:
    target_dir = INVOICE_DIR if kind == "invoice" else PO_DIR
    base = f"{case['case_id']}-{'invoice' if kind == 'invoice' else 'po'}"
    pdf_tmp = TMP_DIR / f"{base}.pdf"
    render_pdf(case, kind, pdf_tmp, template)

    if fmt == "pdf":
        final = target_dir / f"{base}.pdf"
        shutil.copy2(pdf_tmp, final)
    elif fmt == "png":
        final = target_dir / f"{base}.png"
        pdf_to_image(pdf_tmp, final, scan=False)
    elif fmt == "jpg":
        final = target_dir / f"{base}.jpg"
        pdf_to_image(pdf_tmp, final, scan=False)
    elif fmt == "scan_jpg":
        final = target_dir / f"{base}.jpg"
        pdf_to_image(pdf_tmp, final, scan=True)
    else:
        raise ValueError(fmt)
    return str(final.relative_to(OUT))


def main() -> None:
    if OUT.exists():
        shutil.rmtree(OUT)
    INVOICE_DIR.mkdir(parents=True)
    PO_DIR.mkdir(parents=True)
    TMP_DIR.mkdir(parents=True)

    cases = []
    format_pool = iter(DOC_FORMATS)
    for i, scenario in enumerate(SCENARIOS, 1):
        case = build_case(i, scenario)
        inv_fmt = next(format_pool)
        po_fmt = next(format_pool)

        # Force the challenge cases into meaningful image/multipage formats.
        if scenario == "SCAN_CHALLENGE": inv_fmt = "scan_jpg"
        if scenario == "IMAGE_CHALLENGE": po_fmt = "png"
        if scenario == "MULTIPAGE_CHALLENGE": inv_fmt = "pdf"

        case["invoice_format"] = inv_fmt
        case["po_format"] = po_fmt
        case["invoice_file"] = output_document(case, "invoice", inv_fmt, (i - 1) % 5)
        case["po_file"] = output_document(case, "po", po_fmt, (i + 1) % 5)
        cases.append(case)

    # Ground truth JSON
    payload = {
        "dataset_name": "Synthetic Indian IT Procurement Invoice-PO Benchmark",
        "version": "1.0",
        "seed": SEED,
        "synthetic": True,
        "buyer": BUYER,
        "case_count": len(cases),
        "cases": cases,
    }
    (OUT / "ground_truth.json").write_text(json.dumps(payload, indent=2), encoding="utf-8")

    # Flat CSV useful for quick evaluation/reporting.
    fields = [
        "case_id", "scenario", "expected_decision", "expected_exceptions",
        "invoice_file", "po_file", "invoice_format", "po_format",
        "invoice_vendor", "po_vendor", "invoice_number", "invoice_po_number", "po_number",
        "invoice_currency", "po_currency", "invoice_subtotal", "invoice_tax", "invoice_total",
        "po_subtotal", "po_tax", "po_total", "invoice_line_count", "po_line_count",
    ]
    with (OUT / "ground_truth.csv").open("w", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for c in cases:
            inv, po = c["invoice"], c["purchase_order"]
            w.writerow({
                "case_id": c["case_id"], "scenario": c["scenario"], "expected_decision": c["expected_decision"],
                "expected_exceptions": "|".join(c["expected_exceptions"]), "invoice_file": c["invoice_file"], "po_file": c["po_file"],
                "invoice_format": c["invoice_format"], "po_format": c["po_format"],
                "invoice_vendor": inv["vendor"]["name"], "po_vendor": po["vendor"]["name"],
                "invoice_number": inv["invoice_number"], "invoice_po_number": inv["po_number"], "po_number": po["po_number"],
                "invoice_currency": inv["currency"], "po_currency": po["currency"],
                "invoice_subtotal": inv["subtotal"], "invoice_tax": inv["tax"], "invoice_total": inv["total"],
                "po_subtotal": po["subtotal"], "po_tax": po["tax"], "po_total": po["total"],
                "invoice_line_count": len(inv["lines"]), "po_line_count": len(po["lines"]),
            })

    readme = f"""Synthetic Indian IT Procurement Invoice-PO Benchmark\n\nGenerated cases: {len(cases)}\nDocuments: {len(cases)*2}\nRandom seed: {SEED}\n\nAll entities and transactions are synthetic and intended only for software testing.\n\nRun from the invoice-agent project root:\n  python scripts/generate_test_dataset.py\n\nRequired Python packages:\n  reportlab\n  Pillow\n  pymupdf\n\nImportant: expected_exceptions describe the intended benchmark scenario. Your current matcher may emit a subset or slightly different exception names until its rules are aligned with the benchmark.\n"""
    (OUT / "README.txt").write_text(readme, encoding="utf-8")
    shutil.rmtree(TMP_DIR)

    counts = {}
    for c in cases:
        for k in (c["invoice_format"], c["po_format"]): counts[k] = counts.get(k, 0) + 1
    print(f"Created {len(cases)} cases / {len(cases)*2} documents in: {OUT}")
    print("Document formats:", counts)
    print("Ground truth:", OUT / "ground_truth.json")
    print("CSV summary:", OUT / "ground_truth.csv")


if __name__ == "__main__":
    main()
