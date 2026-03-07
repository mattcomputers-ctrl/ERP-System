"""
PDF generation service for BatchFlow ERP.
Generates invoices, purchase orders, packing lists, batch tickets, and COAs.
"""
import io
import os
from datetime import datetime
from decimal import Decimal
from typing import Optional

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import (
    SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, HRFlowable,
)
from reportlab.lib.enums import TA_LEFT, TA_CENTER, TA_RIGHT

from app.core.config import settings


def _ensure_upload_dir():
    pdf_dir = os.path.join(settings.UPLOAD_DIR, "pdfs")
    os.makedirs(pdf_dir, exist_ok=True)
    return pdf_dir


def _fmt_currency(val) -> str:
    if val is None:
        return "$0.00"
    return f"${float(val):,.2f}"


def _fmt_date(val) -> str:
    if val is None:
        return ""
    if isinstance(val, str):
        return val[:10]
    return val.strftime("%m/%d/%Y")


def _fmt_qty(val) -> str:
    if val is None:
        return "0"
    v = float(val)
    return f"{v:,.2f}" if v != int(v) else f"{int(v):,}"


def _build_header(branding, title: str) -> list:
    """Build a standard document header with company branding."""
    styles = getSampleStyleSheet()
    elements = []

    company_style = ParagraphStyle("company", parent=styles["Heading1"], fontSize=16, textColor=colors.HexColor("#1e40af"))
    title_style = ParagraphStyle("doctitle", parent=styles["Heading2"], fontSize=14, spaceAfter=6)
    addr_style = ParagraphStyle("addr", parent=styles["Normal"], fontSize=9, textColor=colors.grey)

    company_name = branding.company_name if branding else "My Company"
    elements.append(Paragraph(company_name, company_style))

    if branding:
        addr_parts = []
        if branding.address_line1:
            addr_parts.append(branding.address_line1)
        city_state = ", ".join(filter(None, [branding.city, branding.state]))
        if city_state or branding.postal_code:
            addr_parts.append(f"{city_state} {branding.postal_code or ''}".strip())
        if branding.phone:
            addr_parts.append(f"Phone: {branding.phone}")
        if branding.email:
            addr_parts.append(f"Email: {branding.email}")
        if addr_parts:
            elements.append(Paragraph("<br/>".join(addr_parts), addr_style))

    elements.append(Spacer(1, 12))
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor("#1e40af")))
    elements.append(Spacer(1, 8))
    elements.append(Paragraph(title, title_style))
    elements.append(Spacer(1, 8))
    return elements


def _info_table(rows: list[tuple[str, str]]) -> Table:
    """Build a two-column info table."""
    styles = getSampleStyleSheet()
    label_style = ParagraphStyle("lbl", parent=styles["Normal"], fontSize=9, textColor=colors.grey)
    val_style = ParagraphStyle("val", parent=styles["Normal"], fontSize=10)
    data = [[Paragraph(r[0], label_style), Paragraph(str(r[1]), val_style)] for r in rows]
    t = Table(data, colWidths=[1.5 * inch, 3 * inch])
    t.setStyle(TableStyle([
        ("VALIGN", (0, 0), (-1, -1), "TOP"),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
    ]))
    return t


def generate_invoice_pdf(invoice, customer, branding) -> str:
    """Generate an Invoice PDF and return the file path."""
    pdf_dir = _ensure_upload_dir()
    filename = f"invoice_{invoice.invoice_number}.pdf"
    filepath = os.path.join(pdf_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    elements = _build_header(branding, f"INVOICE #{invoice.invoice_number}")

    # Invoice info
    info_rows = [
        ("Invoice Date:", _fmt_date(invoice.invoice_date)),
        ("Due Date:", _fmt_date(invoice.due_date)),
        ("Status:", (invoice.status or "draft").upper()),
    ]
    if customer:
        info_rows.insert(0, ("Bill To:", customer.name))
        addr = ", ".join(filter(None, [
            customer.billing_address_line1 or customer.address_line1,
            customer.billing_city or customer.city,
            customer.billing_state or customer.state,
            customer.billing_postal_code or customer.postal_code,
        ]))
        if addr:
            info_rows.insert(1, ("", addr))

    elements.append(_info_table(info_rows))
    elements.append(Spacer(1, 16))

    # Line items table
    header = ["#", "Item", "Description", "Qty", "Unit Price", "Total"]
    data = [header]
    for i, line in enumerate(invoice.lines, 1):
        item_name = line.item.name if line.item else ""
        data.append([
            str(i),
            item_name,
            line.description or "",
            _fmt_qty(line.quantity),
            _fmt_currency(line.unit_price),
            _fmt_currency(line.line_total),
        ])

    col_widths = [0.4 * inch, 1.2 * inch, 2.2 * inch, 0.8 * inch, 1 * inch, 1 * inch]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, 0), 9),
        ("FONTSIZE", (0, 1), (-1, -1), 9),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    # Totals
    totals_data = [
        ["", "", "", "", "Subtotal:", _fmt_currency(invoice.subtotal)],
        ["", "", "", "", "Tax:", _fmt_currency(invoice.tax_amount)],
        ["", "", "", "", "Total:", _fmt_currency(invoice.total_amount)],
    ]
    tt = Table(totals_data, colWidths=col_widths)
    tt.setStyle(TableStyle([
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (4, 2), (-1, 2), "Helvetica-Bold"),
        ("LINEABOVE", (4, 2), (-1, 2), 1, colors.black),
    ]))
    elements.append(tt)

    doc.build(elements)
    return filepath


def generate_purchase_order_pdf(po, vendor, branding) -> str:
    """Generate a Purchase Order PDF and return the file path."""
    pdf_dir = _ensure_upload_dir()
    filename = f"po_{po.po_number}.pdf"
    filepath = os.path.join(pdf_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    elements = _build_header(branding, f"PURCHASE ORDER #{po.po_number}")

    info_rows = [
        ("Vendor:", vendor.name if vendor else ""),
        ("Order Date:", _fmt_date(po.order_date)),
        ("Expected Delivery:", _fmt_date(po.expected_delivery_date)),
        ("Status:", (po.status or "draft").upper()),
    ]
    if vendor:
        addr = ", ".join(filter(None, [vendor.address_line1, vendor.city, vendor.state, vendor.postal_code]))
        if addr:
            info_rows.insert(1, ("", addr))

    elements.append(_info_table(info_rows))
    elements.append(Spacer(1, 16))

    header = ["#", "Item", "Qty Ordered", "Qty Received", "Unit Price", "Total"]
    data = [header]
    for i, line in enumerate(po.lines, 1):
        item_name = line.item.name if line.item else ""
        data.append([
            str(i), item_name,
            _fmt_qty(line.quantity_ordered),
            _fmt_qty(line.quantity_received),
            _fmt_currency(line.unit_price),
            _fmt_currency(line.line_total),
        ])

    col_widths = [0.4 * inch, 1.8 * inch, 1 * inch, 1 * inch, 1 * inch, 1 * inch]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (2, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 12))

    totals_data = [
        ["", "", "", "", "Subtotal:", _fmt_currency(po.subtotal)],
        ["", "", "", "", "Tax:", _fmt_currency(po.tax_amount)],
        ["", "", "", "", "Total:", _fmt_currency(po.total_amount)],
    ]
    tt = Table(totals_data, colWidths=col_widths)
    tt.setStyle(TableStyle([
        ("ALIGN", (4, 0), (-1, -1), "RIGHT"),
        ("FONTSIZE", (0, 0), (-1, -1), 10),
        ("FONTNAME", (4, 2), (-1, 2), "Helvetica-Bold"),
        ("LINEABOVE", (4, 2), (-1, 2), 1, colors.black),
    ]))
    elements.append(tt)

    if po.notes:
        styles = getSampleStyleSheet()
        elements.append(Spacer(1, 16))
        elements.append(Paragraph(f"<b>Notes:</b> {po.notes}", styles["Normal"]))

    doc.build(elements)
    return filepath


def generate_packing_list_pdf(packing_list, sales_order, customer, shipment, shipment_lines, branding) -> str:
    """Generate a Packing List PDF and return the file path."""
    pdf_dir = _ensure_upload_dir()
    filename = f"packing_list_{packing_list.packing_list_number}.pdf"
    filepath = os.path.join(pdf_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    elements = _build_header(branding, f"PACKING LIST #{packing_list.packing_list_number}")

    info_rows = [
        ("Customer:", customer.name if customer else ""),
        ("Sales Order:", sales_order.order_number if sales_order else ""),
        ("Ship Date:", _fmt_date(shipment.ship_date) if shipment else _fmt_date(packing_list.created_date)),
    ]
    if shipment:
        if shipment.carrier:
            info_rows.append(("Carrier:", shipment.carrier))
        if shipment.tracking_number:
            info_rows.append(("Tracking #:", shipment.tracking_number))

    elements.append(_info_table(info_rows))
    elements.append(Spacer(1, 16))

    header = ["#", "Item", "Lot #", "Qty Shipped"]
    data = [header]
    for i, sl in enumerate(shipment_lines or [], 1):
        item_name = sl.item.name if sl.item else ""
        lot_num = sl.lot.lot_number if sl.lot else ""
        data.append([str(i), item_name, lot_num, _fmt_qty(sl.quantity_shipped)])

    col_widths = [0.5 * inch, 2.5 * inch, 2 * inch, 1.5 * inch]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("ALIGN", (3, 0), (-1, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)

    doc.build(elements)
    return filepath


def generate_batch_ticket_pdf(production_order, formula, formula_version, ingredients, branding) -> str:
    """Generate a Batch Ticket (manufacturing work order) PDF."""
    pdf_dir = _ensure_upload_dir()
    filename = f"batch_ticket_{production_order.order_number}.pdf"
    filepath = os.path.join(pdf_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    elements = _build_header(branding, f"BATCH TICKET #{production_order.order_number}")

    info_rows = [
        ("Formula:", f"{formula.code} - {formula.name}" if formula else ""),
        ("Version:", str(formula_version.version_number) if formula_version else ""),
        ("Planned Qty:", _fmt_qty(production_order.planned_quantity)),
        ("Status:", (production_order.status or "planned").upper()),
        ("Planned Start:", _fmt_date(production_order.planned_start_date)),
        ("Planned End:", _fmt_date(production_order.planned_end_date)),
    ]
    if production_order.actual_quantity:
        info_rows.append(("Actual Qty:", _fmt_qty(production_order.actual_quantity)))
    if production_order.yield_percent:
        info_rows.append(("Yield:", f"{float(production_order.yield_percent):.1f}%"))

    elements.append(_info_table(info_rows))
    elements.append(Spacer(1, 16))

    # Instructions
    if formula_version and formula_version.instructions:
        elements.append(Paragraph("<b>Instructions:</b>", styles["Normal"]))
        elements.append(Spacer(1, 4))
        elements.append(Paragraph(formula_version.instructions, styles["Normal"]))
        elements.append(Spacer(1, 12))

    # Ingredients table
    elements.append(Paragraph("<b>Bill of Materials / Ingredients:</b>", styles["Normal"]))
    elements.append(Spacer(1, 6))

    scale_factor = float(production_order.planned_quantity) / float(formula_version.batch_size) if formula_version and formula_version.batch_size else 1

    header = ["Seq", "Item", "Formula Qty", "Scaled Qty", "UOM", "%", "Actual Qty", "Lot #"]
    data = [header]
    for ing in ingredients:
        item_name = ing.item.name if ing.item else ""
        uom_name = ing.uom.abbreviation if ing.uom else ""
        scaled = float(ing.quantity) * scale_factor
        data.append([
            str(ing.sequence),
            item_name,
            _fmt_qty(ing.quantity),
            _fmt_qty(scaled),
            uom_name,
            f"{float(ing.percentage):.1f}" if ing.percentage else "",
            "________",  # blank for manual fill-in
            "________",
        ])

    col_widths = [0.4 * inch, 1.5 * inch, 0.8 * inch, 0.8 * inch, 0.5 * inch, 0.5 * inch, 0.9 * inch, 0.9 * inch]
    t = Table(data, colWidths=col_widths)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 0), (5, -1), "RIGHT"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(t)
    elements.append(Spacer(1, 20))

    # Sign-off section
    elements.append(Paragraph("<b>Production Sign-Off:</b>", styles["Normal"]))
    elements.append(Spacer(1, 8))
    signoff_data = [
        ["Prepared By:", "________________________", "Date:", "____________"],
        ["Verified By:", "________________________", "Date:", "____________"],
        ["QC Approved:", "________________________", "Date:", "____________"],
    ]
    st = Table(signoff_data, colWidths=[1.2 * inch, 2.3 * inch, 0.6 * inch, 1.5 * inch])
    st.setStyle(TableStyle([
        ("FONTSIZE", (0, 0), (-1, -1), 9),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    elements.append(st)

    doc.build(elements)
    return filepath


def generate_coa_pdf(lot, item, qc_spec, qc_results, branding, customer=None) -> str:
    """Generate a Certificate of Analysis (COA) PDF."""
    pdf_dir = _ensure_upload_dir()
    filename = f"coa_{lot.lot_number}.pdf"
    filepath = os.path.join(pdf_dir, filename)

    doc = SimpleDocTemplate(filepath, pagesize=letter,
                            leftMargin=0.75 * inch, rightMargin=0.75 * inch,
                            topMargin=0.75 * inch, bottomMargin=0.75 * inch)
    styles = getSampleStyleSheet()
    elements = _build_header(branding, "CERTIFICATE OF ANALYSIS")

    info_rows = [
        ("Product:", f"{item.item_code} - {item.name}" if item else ""),
        ("Lot Number:", lot.lot_number),
        ("Manufacture Date:", _fmt_date(lot.received_date)),
        ("Expiration Date:", _fmt_date(lot.expiration_date)),
    ]
    if customer:
        info_rows.insert(0, ("Customer:", customer.name))
    if qc_spec:
        info_rows.append(("Specification:", qc_spec.name))

    elements.append(_info_table(info_rows))
    elements.append(Spacer(1, 16))

    # QC Results table
    header = ["Test", "Method", "Target", "Min", "Max", "Result", "UOM", "Pass/Fail"]
    data = [header]
    all_passed = True
    for result in qc_results:
        test = result.test
        passed_text = "PASS" if result.passed else "FAIL"
        if not result.passed:
            all_passed = False
        data.append([
            test.test_name if test else "",
            test.test_method if test else "",
            _fmt_qty(test.target_value) if test and test.target_value else "",
            _fmt_qty(test.min_value) if test and test.min_value else "",
            _fmt_qty(test.max_value) if test and test.max_value else "",
            str(result.result_value) if result.result_value is not None else (result.result_text or ""),
            test.uom if test else "",
            passed_text,
        ])

    col_widths = [1.1 * inch, 0.9 * inch, 0.7 * inch, 0.6 * inch, 0.6 * inch, 0.8 * inch, 0.5 * inch, 0.7 * inch]
    t = Table(data, colWidths=col_widths)
    style_commands = [
        ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1e40af")),
        ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
        ("FONTSIZE", (0, 0), (-1, -1), 8),
        ("ALIGN", (2, 0), (5, -1), "CENTER"),
        ("ALIGN", (7, 0), (7, -1), "CENTER"),
        ("GRID", (0, 0), (-1, -1), 0.5, colors.lightgrey),
        ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")]),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
    ]
    # Color code pass/fail
    for i in range(1, len(data)):
        if data[i][7] == "FAIL":
            style_commands.append(("TEXTCOLOR", (7, i), (7, i), colors.red))
        else:
            style_commands.append(("TEXTCOLOR", (7, i), (7, i), colors.HexColor("#16a34a")))
    t.setStyle(TableStyle(style_commands))
    elements.append(t)
    elements.append(Spacer(1, 16))

    # Overall disposition
    disposition = "RELEASED" if all_passed else "HOLD / REVIEW REQUIRED"
    disp_color = "#16a34a" if all_passed else "#dc2626"
    disp_style = ParagraphStyle("disp", parent=styles["Heading3"], textColor=colors.HexColor(disp_color))
    elements.append(Paragraph(f"Disposition: {disposition}", disp_style))
    elements.append(Spacer(1, 20))

    # Sign-off
    elements.append(Paragraph("<b>Quality Assurance Sign-Off:</b>", styles["Normal"]))
    elements.append(Spacer(1, 8))
    signoff_data = [
        ["QA Manager:", "________________________", "Date:", "____________"],
    ]
    st = Table(signoff_data, colWidths=[1.2 * inch, 2.3 * inch, 0.6 * inch, 1.5 * inch])
    st.setStyle(TableStyle([("FONTSIZE", (0, 0), (-1, -1), 9), ("BOTTOMPADDING", (0, 0), (-1, -1), 12)]))
    elements.append(st)

    doc.build(elements)
    return filepath
