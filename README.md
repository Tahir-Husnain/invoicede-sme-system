# 🧾 InvoiceDE — SME Invoice & Tax Compliance System

<p align="center">
  <img src="https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white" />
  <img src="https://img.shields.io/badge/FastAPI-0.115-009688?style=flat&logo=fastapi&logoColor=white" />
  <img src="https://img.shields.io/badge/SQLite-SQLAlchemy-003B57?style=flat&logo=sqlite&logoColor=white" />
  <img src="https://img.shields.io/badge/License-MIT-green?style=flat" />
</p>

> A fully working, production-structured invoicing web app built for German SMEs. Create invoices, auto-calculate German VAT (19% / 7%), generate downloadable PDF invoices, manage customers, and track payments — all in one clean dashboard.

---

## ✨ Features

| Feature | Details |
|---|---|
| 🧾 Invoice Management | Auto-numbered (`INV-YYYY-XXXX`), dynamic line items, due dates, notes |
| 🇩🇪 German VAT Engine | 19% standard, 7% reduced, §19 UStG tax-free (Kleinunternehmer) |
| 📄 PDF Generator | Professional A4 invoices via ReportLab, downloadable instantly |
| 👥 Customer Management | Full CRUD with VAT ID (USt-IdNr.), address, city, email |
| 💳 Payment Tracking | Mark invoices as Paid / Pending / Unpaid |
| 📊 Reports & Charts | Monthly revenue chart, VAT summary, CSV export |
| 🔐 Authentication | JWT + bcrypt, HTTP-only cookies, per-user workspace |

---

## 🚀 Quick Start

### 1. Clone the repository

```bash
git clone https://github.com/Tahir-Husnain/invoicede-sme-system.git
cd invoicede-sme-system
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS / Linux
source venv/bin/activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

> **Note for Python 3.12 users:** Run this extra line to fix a bcrypt compatibility issue:
> ```bash
> pip install bcrypt==4.0.1
> ```

### 4. Start the server

```bash
uvicorn main:app --reload
```

Then open **http://localhost:8000** in your browser.

### 5. Log in with the demo account

| Field | Value |
|---|---|
| Username | `demo` |
| Password | `demo1234` |

The app auto-seeds 3 customers and 4 sample invoices on first run.

---

## 📁 Project Structure

```
invoicede-sme-system/
│
├── main.py                  # FastAPI app entry point + demo data seeding
├── models.py                # SQLAlchemy ORM models
├── database.py              # DB engine and session configuration
├── auth.py                  # JWT auth, bcrypt hashing, cookie sessions
│
├── routes/
│   ├── auth.py              # Login / register / logout endpoints
│   ├── invoices.py          # Invoice CRUD + PDF download
│   ├── customers.py         # Customer CRUD
│   └── reports.py           # Financial reports + CSV export
│
├── services/
│   ├── tax_calculator.py    # German VAT logic (19%, 7%, §19 UStG)
│   └── pdf_generator.py     # ReportLab A4 PDF invoice generator
│
├── templates/               # Jinja2 HTML templates
│   ├── base.html            # Sidebar layout (all pages extend this)
│   ├── login.html
│   ├── register.html
│   ├── dashboard.html
│   ├── customers.html
│   ├── customer_form.html
│   ├── invoices.html
│   ├── invoice_form.html    # Dynamic JS line items + live VAT calc
│   ├── invoice_detail.html
│   └── reports.html         # Chart.js revenue + status charts
│
├── static/                  # CSS / JS static assets
├── .env.example             # Environment variable template
├── .gitignore
├── requirements.txt
└── start.sh                 # One-command startup script
```

---

## 🇩🇪 German VAT (MwSt.) Logic

The system correctly implements German tax rules:

| Rate | Type | Use Case |
|---|---|---|
| **19%** | Regelsteuersatz | Standard services, software, consulting |
| **7%** | Ermäßigter Steuersatz | Books, food, certain cultural services |
| **0%** | §19 UStG | Kleinunternehmer (small business exemption) |

Each line item has its own VAT rate. The invoice summary shows a full breakdown by rate — e.g. `MwSt. 19%: €190.00` and `MwSt. 7%: €7.00` separately.

When `§19 UStG` mode is enabled, the PDF includes the legally required note:
> *"Gemäß §19 UStG wird keine Umsatzsteuer berechnet."*

---

## 💾 Data Models

```
User
 ├── id, username, email, full_name
 ├── company_name, company_address, company_vat_id
 └── hashed_password

Customer (belongs to User)
 ├── name, email, phone
 ├── address, city, postal_code, country
 └── vat_id

Invoice (belongs to User + Customer)
 ├── invoice_number (INV-YYYY-XXXX)
 ├── issue_date, due_date
 ├── status (paid / pending / unpaid)
 ├── subtotal, vat_amount, total
 ├── tax_free (§19 UStG toggle)
 └── items → [InvoiceItem]

InvoiceItem (belongs to Invoice)
 ├── description, quantity, unit_price
 ├── vat_rate (19 / 7 / 0)
 └── line_total, vat_amount
```

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| Backend framework | FastAPI + Uvicorn |
| ORM | SQLAlchemy 2.0 |
| Database | SQLite (dev) / PostgreSQL (production) |
| Auth | python-jose (JWT) + passlib (bcrypt) |
| PDF generation | ReportLab |
| Templating | Jinja2 |
| Charts | Chart.js (CDN) |
| Fonts | DM Sans + DM Mono (Google Fonts) |

---

## ⚙️ Configuration

Copy `.env.example` to `.env` and edit:

```bash
cp .env.example .env
```

```env
SECRET_KEY=your-long-random-secret-key-here
```

**To switch to PostgreSQL**, change one line in `database.py`:

```python
# From:
SQLALCHEMY_DATABASE_URL = "sqlite:///./invoiceapp.db"

# To:
SQLALCHEMY_DATABASE_URL = "postgresql://user:password@localhost/invoicedb"
```

---

## 🧪 VAT Calculation Tests

```bash
python -c "
from services.tax_calculator import calculate_item_totals, calculate_invoice_totals

r = calculate_item_totals(10, 100, '19')
assert r['net_total'] == 1000.0
assert r['vat_amount'] == 190.0
assert r['gross_total'] == 1190.0

r = calculate_item_totals(1, 100, '7')
assert r['vat_amount'] == 7.0

items = [{'quantity': 1, 'unit_price': 500, 'vat_rate': '19'}]
t = calculate_invoice_totals(items, tax_free=True)
assert t['vat_amount'] == 0.0
assert t['total'] == 500.0

print('All VAT tests passed ✅')
"
```

---

## 🗺️ Roadmap

- [ ] SMTP email — send PDF invoice directly to customer
- [ ] DATEV export — for German accountants / Steuerberater
- [ ] Stripe integration — payment links on invoices
- [ ] Recurring invoices — monthly/yearly auto-generation
- [ ] Overdue reminders — scheduled email notifications
- [ ] ELSTER VAT pre-declaration export (Umsatzsteuervoranmeldung)
- [ ] Multi-language toggle (Deutsch / English)
- [ ] Docker / docker-compose setup

---

## 📄 License

MIT License — free to use, modify, and distribute.

---

## 👤 Author

Built by **Tahir Husnain** — feel free to open an issue or pull request!

---

<p align="center">Made with ☕ and 🇩🇪 tax law</p>
