from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse, StreamingResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from sqlalchemy import extract, func
from database import get_db
from auth import get_current_user_from_cookie
import models
import csv
import io
from datetime import date

router = APIRouter(prefix="/reports", tags=["reports"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
async def reports(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
    year: int = None,
):
    if year is None:
        year = date.today().year

    invoices = db.query(models.Invoice).filter(
        models.Invoice.owner_id == current_user.id,
        models.Invoice.issue_date.like(f"{year}-%"),
    ).all()

    monthly = {}
    for month in range(1, 13):
        monthly[month] = {"revenue": 0.0, "vat": 0.0, "count": 0}

    for inv in invoices:
        try:
            month = int(inv.issue_date.split("-")[1])
        except:
            continue
        monthly[month]["revenue"] += inv.subtotal
        monthly[month]["vat"] += inv.vat_amount
        monthly[month]["count"] += 1

    total_revenue = sum(m["revenue"] for m in monthly.values())
    total_vat = sum(m["vat"] for m in monthly.values())
    paid_total = sum(i.total for i in invoices if i.status == "paid")
    unpaid_total = sum(i.total for i in invoices if i.status != "paid")
    paid_count = sum(1 for i in invoices if i.status == "paid")
    unpaid_count = sum(1 for i in invoices if i.status != "paid")

    available_years = list(range(date.today().year, date.today().year - 5, -1))

    return templates.TemplateResponse(
        "reports.html",
        {
            "request": request,
            "user": current_user,
            "year": year,
            "monthly": monthly,
            "total_revenue": round(total_revenue, 2),
            "total_vat": round(total_vat, 2),
            "total_gross": round(total_revenue + total_vat, 2),
            "paid_total": round(paid_total, 2),
            "unpaid_total": round(unpaid_total, 2),
            "paid_count": paid_count,
            "unpaid_count": unpaid_count,
            "available_years": available_years,
        },
    )


@router.get("/export/csv")
async def export_csv(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    invoices = db.query(models.Invoice).filter(
        models.Invoice.owner_id == current_user.id
    ).order_by(models.Invoice.issue_date.desc()).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "Invoice Number", "Customer", "Issue Date", "Due Date",
        "Status", "Subtotal (EUR)", "VAT (EUR)", "Total (EUR)",
    ])
    for inv in invoices:
        writer.writerow([
            inv.invoice_number,
            inv.customer.name,
            inv.issue_date,
            inv.due_date,
            inv.status,
            f"{inv.subtotal:.2f}",
            f"{inv.vat_amount:.2f}",
            f"{inv.total:.2f}",
        ])

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=invoices_export.csv"},
    )
