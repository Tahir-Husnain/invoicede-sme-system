from fastapi import FastAPI, Depends, Request, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from datetime import date

import models
from database import engine, get_db
from auth import get_current_user_from_cookie, get_password_hash
from routes import auth as auth_router
from routes import customers as customers_router
from routes import invoices as invoices_router
from routes import reports as reports_router

# Create tables
models.Base.metadata.create_all(bind=engine)

app = FastAPI(title="SME Invoice System", version="1.0.0")

app.mount("/static", StaticFiles(directory="static"), name="static")
templates = Jinja2Templates(directory="templates")

app.include_router(auth_router.router)
app.include_router(customers_router.router)
app.include_router(invoices_router.router)
app.include_router(reports_router.router)


@app.get("/", response_class=HTMLResponse)
async def root():
    return RedirectResponse(url="/dashboard")


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    invoices = db.query(models.Invoice).filter(
        models.Invoice.owner_id == current_user.id
    ).all()

    total = len(invoices)
    paid = sum(1 for i in invoices if i.status == "paid")
    unpaid = sum(1 for i in invoices if i.status == "unpaid")
    pending = sum(1 for i in invoices if i.status == "pending")

    total_revenue = sum(i.subtotal for i in invoices if i.status == "paid")
    total_vat = sum(i.vat_amount for i in invoices if i.status == "paid")
    outstanding = sum(i.total for i in invoices if i.status != "paid")

    current_month = date.today().month
    current_year = date.today().year
    monthly_invoices = [
        i for i in invoices
        if i.issue_date.startswith(f"{current_year}-{str(current_month).zfill(2)}")
    ]
    monthly_revenue = sum(i.total for i in monthly_invoices)

    recent_invoices = sorted(invoices, key=lambda x: x.created_at, reverse=True)[:5]
    customers_count = db.query(models.Customer).filter(
        models.Customer.owner_id == current_user.id
    ).count()

    return templates.TemplateResponse(
        "dashboard.html",
        {
            "request": request,
            "user": current_user,
            "total_invoices": total,
            "paid_invoices": paid,
            "unpaid_invoices": unpaid,
            "pending_invoices": pending,
            "total_revenue": round(total_revenue, 2),
            "total_vat": round(total_vat, 2),
            "outstanding": round(outstanding, 2),
            "monthly_revenue": round(monthly_revenue, 2),
            "recent_invoices": recent_invoices,
            "customers_count": customers_count,
        },
    )


def seed_demo_data(db: Session):
    """Seed a demo user and sample data if DB is empty."""
    if db.query(models.User).count() > 0:
        return

    user = models.User(
        username="demo",
        email="demo@musterunternehmen.de",
        full_name="Max Mustermann",
        company_name="Mustermann GmbH",
        company_address="Musterstraße 42\n10115 Berlin",
        company_vat_id="DE123456789",
        company_email="info@musterunternehmen.de",
        company_phone="+49 30 12345678",
        hashed_password=get_password_hash("demo1234"),
    )
    db.add(user)
    db.flush()

    customers_data = [
        {"name": "Technik AG", "email": "kontakt@technik-ag.de", "address": "Innovationsweg 5",
         "city": "München", "postal_code": "80333", "vat_id": "DE987654321"},
        {"name": "Handel GmbH", "email": "info@handel-gmbh.de", "address": "Handelsplatz 12",
         "city": "Hamburg", "postal_code": "20095"},
        {"name": "Kreativ Studio", "email": "hallo@kreativ-studio.de", "address": "Kreativgasse 7",
         "city": "Berlin", "postal_code": "10178"},
    ]
    customers = []
    for c in customers_data:
        cust = models.Customer(owner_id=user.id, country="Germany", **c)
        db.add(cust)
        db.flush()
        customers.append(cust)

    invoices_data = [
        {"customer": customers[0], "issue_date": "2026-01-15", "due_date": "2026-02-14",
         "status": "paid", "items": [
             {"desc": "Webentwicklung (40h)", "qty": 40, "price": 95.00, "vat": "19"},
             {"desc": "Projektmanagement", "qty": 1, "price": 500.00, "vat": "19"},
         ]},
        {"customer": customers[1], "issue_date": "2026-02-01", "due_date": "2026-03-02",
         "status": "paid", "items": [
             {"desc": "Logo Design", "qty": 1, "price": 1200.00, "vat": "19"},
             {"desc": "Visitenkarten Design", "qty": 1, "price": 300.00, "vat": "7"},
         ]},
        {"customer": customers[2], "issue_date": "2026-03-10", "due_date": "2026-04-09",
         "status": "unpaid", "items": [
             {"desc": "SEO Beratung (10h)", "qty": 10, "price": 120.00, "vat": "19"},
         ]},
        {"customer": customers[0], "issue_date": "2026-04-01", "due_date": "2026-05-01",
         "status": "pending", "items": [
             {"desc": "Monatliches Hosting", "qty": 3, "price": 49.00, "vat": "19"},
             {"desc": "E-Mail Support", "qty": 5, "price": 80.00, "vat": "19"},
         ]},
    ]

    for idx, inv_data in enumerate(invoices_data):
        year = inv_data["issue_date"].split("-")[0]
        num = f"INV-{year}-{str(idx + 1).zfill(4)}"
        items = [
            {"description": i["desc"], "quantity": i["qty"],
             "unit_price": i["price"], "vat_rate": i["vat"]}
            for i in inv_data["items"]
        ]
        from services.tax_calculator import calculate_invoice_totals, calculate_item_totals
        totals = calculate_invoice_totals(items)
        invoice = models.Invoice(
            owner_id=user.id,
            customer_id=inv_data["customer"].id,
            invoice_number=num,
            issue_date=inv_data["issue_date"],
            due_date=inv_data["due_date"],
            status=inv_data["status"],
            subtotal=totals["subtotal"],
            vat_amount=totals["vat_amount"],
            total=totals["total"],
        )
        db.add(invoice)
        db.flush()
        for item in items:
            calc = calculate_item_totals(item["quantity"], item["unit_price"], item["vat_rate"])
            db.add(models.InvoiceItem(
                invoice_id=invoice.id,
                description=item["description"],
                quantity=item["quantity"],
                unit_price=item["unit_price"],
                vat_rate=item["vat_rate"],
                line_total=calc["net_total"],
                vat_amount=calc["vat_amount"],
            ))

    db.commit()
    print("✅ Demo data seeded. Login: demo / demo1234")


# Seed on startup
@app.on_event("startup")
def startup_event():
    db = next(get_db())
    seed_demo_data(db)
