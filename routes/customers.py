from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
from auth import get_current_user_from_cookie
import models

router = APIRouter(prefix="/customers", tags=["customers"])
templates = Jinja2Templates(directory="templates")


@router.get("", response_class=HTMLResponse)
async def list_customers(
    request: Request,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
    search: str = "",
):
    query = db.query(models.Customer).filter(models.Customer.owner_id == current_user.id)
    if search:
        query = query.filter(models.Customer.name.ilike(f"%{search}%"))
    customers = query.order_by(models.Customer.name).all()
    return templates.TemplateResponse(
        "customers.html",
        {"request": request, "user": current_user, "customers": customers, "search": search},
    )


@router.get("/new", response_class=HTMLResponse)
async def new_customer_form(
    request: Request,
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    return templates.TemplateResponse(
        "customer_form.html",
        {"request": request, "user": current_user, "customer": None, "error": None},
    )


@router.post("/new")
async def create_customer(
    request: Request,
    name: str = Form(...),
    email: str = Form(""),
    address: str = Form(""),
    city: str = Form(""),
    postal_code: str = Form(""),
    country: str = Form("Germany"),
    vat_id: str = Form(""),
    phone: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    customer = models.Customer(
        owner_id=current_user.id,
        name=name, email=email, address=address,
        city=city, postal_code=postal_code,
        country=country, vat_id=vat_id, phone=phone,
    )
    db.add(customer)
    db.commit()
    return RedirectResponse(url="/customers", status_code=302)


@router.get("/{customer_id}/edit", response_class=HTMLResponse)
async def edit_customer_form(
    request: Request,
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    customer = db.query(models.Customer).filter(
        models.Customer.id == customer_id,
        models.Customer.owner_id == current_user.id,
    ).first()
    if not customer:
        raise HTTPException(status_code=404)
    return templates.TemplateResponse(
        "customer_form.html",
        {"request": request, "user": current_user, "customer": customer, "error": None},
    )


@router.post("/{customer_id}/edit")
async def update_customer(
    customer_id: int,
    name: str = Form(...),
    email: str = Form(""),
    address: str = Form(""),
    city: str = Form(""),
    postal_code: str = Form(""),
    country: str = Form("Germany"),
    vat_id: str = Form(""),
    phone: str = Form(""),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    customer = db.query(models.Customer).filter(
        models.Customer.id == customer_id,
        models.Customer.owner_id == current_user.id,
    ).first()
    if not customer:
        raise HTTPException(status_code=404)
    customer.name = name
    customer.email = email
    customer.address = address
    customer.city = city
    customer.postal_code = postal_code
    customer.country = country
    customer.vat_id = vat_id
    customer.phone = phone
    db.commit()
    return RedirectResponse(url="/customers", status_code=302)


@router.post("/{customer_id}/delete")
async def delete_customer(
    customer_id: int,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user_from_cookie),
):
    customer = db.query(models.Customer).filter(
        models.Customer.id == customer_id,
        models.Customer.owner_id == current_user.id,
    ).first()
    if not customer:
        raise HTTPException(status_code=404)
    db.delete(customer)
    db.commit()
    return RedirectResponse(url="/customers", status_code=302)
