from fastapi import APIRouter, Depends, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy.orm import Session
from database import get_db
import models
import auth

router = APIRouter(prefix="/auth", tags=["auth"])
templates = Jinja2Templates(directory="templates")


@router.get("/login", response_class=HTMLResponse)
async def login_page(request: Request):
    return templates.TemplateResponse("login.html", {"request": request, "error": None})


@router.post("/login")
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    user = auth.authenticate_user(db, username, password)
    if not user:
        return templates.TemplateResponse(
            "login.html",
            {"request": request, "error": "Ungültige Anmeldedaten / Invalid credentials"},
            status_code=401,
        )
    token = auth.create_access_token(data={"sub": user.username})
    response = RedirectResponse(url="/dashboard", status_code=302)
    response.set_cookie(key="access_token", value=token, httponly=True, max_age=60 * 60 * 8)
    return response


@router.get("/register", response_class=HTMLResponse)
async def register_page(request: Request):
    return templates.TemplateResponse("register.html", {"request": request, "error": None})


@router.post("/register")
async def register(
    request: Request,
    username: str = Form(...),
    email: str = Form(...),
    full_name: str = Form(...),
    company_name: str = Form(...),
    company_address: str = Form(""),
    company_vat_id: str = Form(""),
    company_email: str = Form(""),
    company_phone: str = Form(""),
    password: str = Form(...),
    db: Session = Depends(get_db),
):
    existing = db.query(models.User).filter(
        (models.User.username == username) | (models.User.email == email)
    ).first()
    if existing:
        return templates.TemplateResponse(
            "register.html",
            {"request": request, "error": "Username or email already registered."},
            status_code=400,
        )
    user = models.User(
        username=username,
        email=email,
        full_name=full_name,
        company_name=company_name,
        company_address=company_address,
        company_vat_id=company_vat_id,
        company_email=company_email,
        company_phone=company_phone,
        hashed_password=auth.get_password_hash(password),
    )
    db.add(user)
    db.commit()
    response = RedirectResponse(url="/auth/login?registered=1", status_code=302)
    return response


@router.get("/logout")
async def logout():
    response = RedirectResponse(url="/auth/login", status_code=302)
    response.delete_cookie("access_token")
    return response
