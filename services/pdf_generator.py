import io
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, HRFlowable
from reportlab.lib.enums import TA_LEFT, TA_RIGHT, TA_CENTER
from services.tax_calculator import format_currency


# Color palette
DARK   = colors.HexColor("#1a1a2e")
ACCENT = colors.HexColor("#2563eb")
GRAY   = colors.HexColor("#6b7280")
LIGHT_GRAY = colors.HexColor("#f3f4f6")
BORDER = colors.HexColor("#e5e7eb")
WHITE  = colors.white
GREEN  = colors.HexColor("#16a34a")
ORANGE = colors.HexColor("#d97706")
RED    = colors.HexColor("#dc2626")

STATUS_COLORS = {"paid": GREEN, "pending": ORANGE, "unpaid": RED}

# Usable page width: A4 210mm - 2×20mm margins = 170mm
PAGE_W = 170 * mm


def _style(name, **kw):
    base = dict(fontName="Helvetica", fontSize=9, textColor=DARK, spaceAfter=0, spaceBefore=0, leading=13)
    base.update(kw)
    return ParagraphStyle(name, **base)


def generate_invoice_pdf(invoice, user, customer) -> bytes:
    """Generate a professional PDF invoice and return bytes."""
    buffer = io.BytesIO()

    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=15 * mm,
        bottomMargin=20 * mm,
    )

    story = []

    # ── Shared styles ──────────────────────────────────────────────────────────
    s_normal   = _style("normal")
    s_muted    = _style("muted",   textColor=GRAY, fontSize=8, leading=11)
    s_bold     = _style("bold",    fontName="Helvetica-Bold")
    s_company  = _style("company", fontName="Helvetica-Bold", fontSize=15, textColor=DARK, leading=18)
    s_r_head   = _style("rhead",   fontName="Helvetica-Bold", fontSize=20, textColor=ACCENT,
                         alignment=TA_RIGHT, leading=24)
    s_r_num    = _style("rnum",    fontName="Helvetica-Bold", fontSize=13, textColor=DARK,
                         alignment=TA_RIGHT, leading=16)
    s_r_label  = _style("rlbl",    fontSize=8,  textColor=GRAY, alignment=TA_RIGHT, leading=11)
    s_r_value  = _style("rval",    fontSize=9,  textColor=DARK, alignment=TA_RIGHT, leading=13)
    s_r_status = _style("rstat",   fontName="Helvetica-Bold", fontSize=9,
                         textColor=STATUS_COLORS.get(invoice.status, GRAY),
                         alignment=TA_RIGHT, leading=13)

    # ── Header: left = company info, right = invoice meta ─────────────────────
    # Build left cell content
    left_lines = [Paragraph(user.company_name or user.full_name, s_company)]
    if user.company_address:
        for ln in user.company_address.replace("\r", "").split("\n"):
            ln = ln.strip()
            if ln:
                left_lines.append(Paragraph(ln, s_normal))
    if user.company_vat_id:
        left_lines.append(Paragraph(f"USt-IdNr.: {user.company_vat_id}", s_muted))
    if user.company_email:
        left_lines.append(Paragraph(user.company_email, s_muted))
    if user.company_phone:
        left_lines.append(Paragraph(user.company_phone, s_muted))

    # Build right cell content
    right_lines = [
        Paragraph("RECHNUNG", s_r_head),
        Paragraph(invoice.invoice_number, s_r_num),
        Spacer(1, 3 * mm),
        Paragraph("Rechnungsdatum / Invoice Date", s_r_label),
        Paragraph(invoice.issue_date, s_r_value),
        Paragraph("Fälligkeitsdatum / Due Date", s_r_label),
        Paragraph(invoice.due_date, s_r_value),
        Paragraph("Status", s_r_label),
        Paragraph(invoice.status.upper(), s_r_status),
    ]

    # Left col = 55% of usable width, right col = 45%
    col_l = PAGE_W * 0.55
    col_r = PAGE_W * 0.45

    header_table = Table([[left_lines, right_lines]], colWidths=[col_l, col_r])
    header_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "TOP"),
        ("LEFTPADDING",  (0, 0), (-1, -1), 0),
        ("RIGHTPADDING", (0, 0), (-1, -1), 0),
        ("TOPPADDING",   (0, 0), (-1, -1), 0),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 0),
    ]))
    story.append(header_table)
    story.append(Spacer(1, 6 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 5 * mm))

    # ── Bill To ────────────────────────────────────────────────────────────────
    s_section  = _style("sect", fontName="Helvetica-Bold", fontSize=8,
                          textColor=ACCENT, leading=10, spaceAfter=4)
    s_cust     = _style("cust", fontName="Helvetica-Bold", fontSize=11,
                          textColor=DARK, leading=14, spaceAfter=2)

    story.append(Paragraph("RECHNUNGSEMPFÄNGER / BILL TO", s_section))
    story.append(Paragraph(customer.name, s_cust))
    if customer.address:
        story.append(Paragraph(customer.address, s_normal))
    addr = " ".join(filter(None, [customer.postal_code, customer.city]))
    if addr:
        story.append(Paragraph(addr, s_normal))
    if customer.country:
        story.append(Paragraph(customer.country, s_normal))
    if customer.vat_id:
        story.append(Paragraph(f"USt-IdNr.: {customer.vat_id}", s_muted))
    if customer.email:
        story.append(Paragraph(customer.email, s_muted))

    story.append(Spacer(1, 7 * mm))

    # ── Items table ────────────────────────────────────────────────────────────
    s_col_hdr = _style("colhdr", fontName="Helvetica-Bold", fontSize=8,
                        textColor=WHITE, leading=10)
    s_item    = _style("itm",  fontSize=9, textColor=DARK, leading=12)
    s_item_r  = _style("itmr", fontSize=9, textColor=DARK, alignment=TA_RIGHT, leading=12)
    s_item_c  = _style("itmc", fontSize=9, textColor=DARK, alignment=TA_CENTER, leading=12)

    # Column widths must sum to PAGE_W (170mm)
    # Desc | VAT% | Qty | Unit Price | VAT Amt | Total
    col_w = [72*mm, 14*mm, 16*mm, 24*mm, 22*mm, 22*mm]  # sum = 170mm

    table_data = [[
        Paragraph("BESCHREIBUNG / DESCRIPTION", s_col_hdr),
        Paragraph("MwSt.", s_col_hdr),
        Paragraph("Menge", s_col_hdr),
        Paragraph("Preis", s_col_hdr),
        Paragraph("MwSt.€", s_col_hdr),
        Paragraph("Gesamt", s_col_hdr),
    ]]

    for idx, item in enumerate(invoice.items):
        vat_r = item.vat_rate if not invoice.tax_free else "0"
        table_data.append([
            Paragraph(item.description or "—", s_item),
            Paragraph(f"{vat_r}%", s_item_c),
            Paragraph(f"{item.quantity:g}", s_item_c),
            Paragraph(format_currency(item.unit_price), s_item_r),
            Paragraph(format_currency(item.vat_amount), s_item_r),
            Paragraph(format_currency(item.line_total + item.vat_amount), s_item_r),
        ])

    items_table = Table(table_data, colWidths=col_w, repeatRows=1)
    items_table.setStyle(TableStyle([
        # Header row
        ("BACKGROUND",    (0, 0), (-1, 0),  ACCENT),
        ("TEXTCOLOR",     (0, 0), (-1, 0),  WHITE),
        ("FONTNAME",      (0, 0), (-1, 0),  "Helvetica-Bold"),
        ("FONTSIZE",      (0, 0), (-1, 0),  8),
        # Alternating rows
        ("ROWBACKGROUNDS",(0, 1), (-1, -1), [WHITE, LIGHT_GRAY]),
        # Padding
        ("TOPPADDING",    (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING",   (0, 0), (-1, -1), 7),
        ("RIGHTPADDING",  (0, 0), (-1, -1), 7),
        # Alignment: cols 1-5 center/right
        ("ALIGN",         (1, 0), (2, -1),  "CENTER"),
        ("ALIGN",         (3, 0), (5, -1),  "RIGHT"),
        ("VALIGN",        (0, 0), (-1, -1), "MIDDLE"),
        # Grid
        ("LINEBELOW",     (0, 0), (-1, -1), 0.3, BORDER),
        ("LINEABOVE",     (0, 0), (-1,  0), 0,   WHITE),
    ]))
    story.append(items_table)
    story.append(Spacer(1, 6 * mm))

    # ── Totals ─────────────────────────────────────────────────────────────────
    s_tot_lbl   = _style("totlbl", fontSize=9, textColor=GRAY, alignment=TA_RIGHT)
    s_tot_val   = _style("totval", fontSize=9, textColor=DARK, alignment=TA_RIGHT,
                          fontName="Helvetica-Bold")
    s_grand_lbl = _style("grlbl",  fontSize=11, fontName="Helvetica-Bold",
                          textColor=WHITE, alignment=TA_RIGHT)
    s_grand_val = _style("grval",  fontSize=11, fontName="Helvetica-Bold",
                          textColor=WHITE, alignment=TA_RIGHT)

    # Collect VAT by rate
    vat_rates_seen = {}
    for item in invoice.items:
        r = item.vat_rate if not invoice.tax_free else "0"
        vat_rates_seen[r] = vat_rates_seen.get(r, 0) + item.vat_amount

    totals_data = [
        [Paragraph("Nettobetrag (Subtotal):", s_tot_lbl),
         Paragraph(format_currency(invoice.subtotal), s_tot_val)],
    ]
    if invoice.tax_free:
        totals_data.append([
            Paragraph("Gemäß §19 UStG keine MwSt.", s_tot_lbl),
            Paragraph("€0,00", s_tot_val),
        ])
    else:
        for rate, amt in sorted(vat_rates_seen.items()):
            totals_data.append([
                Paragraph(f"MwSt. {rate}%:", s_tot_lbl),
                Paragraph(format_currency(round(amt, 2)), s_tot_val),
            ])

    totals_data.append([
        Paragraph("GESAMTBETRAG (TOTAL):", s_grand_lbl),
        Paragraph(format_currency(invoice.total), s_grand_val),
    ])

    # Totals sit right-aligned: spacer col + label col + value col
    totals_table = Table(totals_data, colWidths=[PAGE_W - 110*mm, 70*mm, 40*mm])
    grand_row = len(totals_data) - 1
    totals_table.setStyle(TableStyle([
        ("VALIGN",       (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING",   (0, 0), (-1, -1), 4),
        ("BOTTOMPADDING",(0, 0), (-1, -1), 4),
        ("LEFTPADDING",  (0, 0), (-1, -1), 6),
        ("RIGHTPADDING", (0, 0), (-1, -1), 6),
        # Grand total row — blue background
        ("BACKGROUND",   (0, grand_row), (-1, grand_row), ACCENT),
        ("TOPPADDING",   (0, grand_row), (-1, grand_row), 7),
        ("BOTTOMPADDING",(0, grand_row), (-1, grand_row), 7),
        # Thin divider above grand total
        ("LINEABOVE",    (0, grand_row), (-1, grand_row), 0.5, ACCENT),
    ]))
    story.append(totals_table)

    # ── Notes ──────────────────────────────────────────────────────────────────
    if invoice.notes:
        story.append(Spacer(1, 6 * mm))
        story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
        story.append(Spacer(1, 3 * mm))
        story.append(Paragraph("ANMERKUNGEN / NOTES", s_section))
        story.append(Paragraph(invoice.notes, s_normal))

    # ── Footer ─────────────────────────────────────────────────────────────────
    story.append(Spacer(1, 10 * mm))
    story.append(HRFlowable(width="100%", thickness=0.5, color=BORDER))
    story.append(Spacer(1, 3 * mm))
    s_footer = _style("footer", fontSize=8, textColor=GRAY, alignment=TA_CENTER, leading=12)
    addr_oneline = " · ".join(
        ln.strip() for ln in (user.company_address or "").replace("\r", "").split("\n") if ln.strip()
    )
    story.append(Paragraph(
        f"Vielen Dank für Ihr Vertrauen! · Thank you for your business! · {user.company_name}",
        s_footer,
    ))
    if addr_oneline:
        story.append(Paragraph(addr_oneline, s_footer))

    doc.build(story)
    buffer.seek(0)
    return buffer.read()
