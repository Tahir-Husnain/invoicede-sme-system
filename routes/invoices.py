import json
from datetime import date, timedelta
from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, Response
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user_from_cookie
from services.tax_calculator import calculate_item_totals, calculate_invoice_totals
from services.pdf_generator import generate_invoice_pdf
import models

router = APIRouter(prefix="/invoices", tags=["invoices"])
templates = Jinja2Templates(directory="templates")


def generate_invoice_number(db: Session, user_id: int) -> str:
    year = date.today().year
    count = db.query(models.Invoice).filter(
        models.Invoice.owner_id == user_id,
        models.Invoice.invoice_number.like(f"INV-{year}-%"),
    ).count()
    return f"INV-{year}-{str(count + 1).zfill(4)}"


@router.get("", response_class=HTMLResponse)
async def list_invoices(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
    status: str = "",
    search: str = "",
):
    query = (
        db.query(models.Invoice)
        .filter(models.Invoice.owner_id == current_user.id)
        .join(models.Customer)
    )
    if status:
        query = query.filter(models.Invoice.status == status)
    if search:
        query = query.filter(models.Customer.name.ilike(f"%{search}%"))
    invoices = query.order_by(models.Invoice.created_at.desc()).all()
    return templates.TemplateResponse(
        "invoices.html",
        {
            "request": request, "user": current_user,
            "invoices": invoices, "status_filter": status, "search": search,
        },
    )


@router.get("/new", response_class=HTMLResponse)
async def new_invoice_form(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    customers = db.query(models.Customer).filter(
        models.Customer.owner_id == current_user.id
    ).order_by(models.Customer.name).all()
    today = date.today().isoformat()
    due = (date.today() + timedelta(days=30)).isoformat()
    inv_number = generate_invoice_number(db, current_user.id)
    return templates.TemplateResponse(
        "invoice_form.html",
        {
            "request": request, "user": current_user,
            "customers": customers, "invoice": None,
            "today": today, "due_date": due,
            "inv_number": inv_number,
        },
    )


@router.post("/new")
async def create_invoice(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    form = await request.form()
    customer_id = int(form["customer_id"])
    invoice_number = form["invoice_number"]
    issue_date = form["issue_date"]
    due_date = form["due_date"]
    notes = form.get("notes", "")
    tax_free = form.get("tax_free") == "on"

    # Parse items from form
    items_json = form.get("items_json", "[]")
    items = json.loads(items_json)

    totals = calculate_invoice_totals(items, tax_free)

    invoice = models.Invoice(
        owner_id=current_user.id,
        customer_id=customer_id,
        invoice_number=invoice_number,
        issue_date=issue_date,
        due_date=due_date,
        notes=notes,
        tax_free=tax_free,
        subtotal=totals["subtotal"],
        vat_amount=totals["vat_amount"],
        total=totals["total"],
    )
    db.add(invoice)
    db.flush()

    for item in items:
        vat_rate = item.get("vat_rate", "19") if not tax_free else "0"
        calc = calculate_item_totals(item["quantity"], item["unit_price"], vat_rate)
        db_item = models.InvoiceItem(
            invoice_id=invoice.id,
            description=item["description"],
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            vat_rate=vat_rate,
            line_total=calc["net_total"],
            vat_amount=calc["vat_amount"],
        )
        db.add(db_item)

    db.commit()
    return RedirectResponse(url=f"/invoices/{invoice.id}", status_code=302)


@router.get("/{invoice_id}", response_class=HTMLResponse)
async def view_invoice(
    request: Request,
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.owner_id == current_user.id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "invoice_detail.html",
        {"request": request, "user": current_user, "invoice": invoice},
    )


@router.post("/{invoice_id}/status")
async def update_invoice_status(
    invoice_id: int,
    status: str = Form(...),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.owner_id == current_user.id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=404)
    invoice.status = status
    db.commit()
    return RedirectResponse(url=f"/invoices/{invoice_id}", status_code=302)


@router.get("/{invoice_id}/pdf")
async def download_pdf(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.owner_id == current_user.id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=404)
    pdf_bytes = generate_invoice_pdf(invoice, current_user, invoice.customer)
    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{invoice.invoice_number}.pdf"'
        },
    )


@router.post("/{invoice_id}/delete")
async def delete_invoice(
    invoice_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    invoice = db.query(models.Invoice).filter(
        models.Invoice.id == invoice_id,
        models.Invoice.owner_id == current_user.id,
    ).first()
    if not invoice:
        raise HTTPException(status_code=404)
    db.delete(invoice)
    db.commit()
    return RedirectResponse(url="/invoices", status_code=302)
