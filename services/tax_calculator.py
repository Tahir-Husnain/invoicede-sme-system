from typing import List, Dict


VAT_RATES = {
    "19": 0.19,
    "7": 0.07,
    "0": 0.0,
}


def calculate_item_totals(quantity: float, unit_price: float, vat_rate_str: str) -> Dict:
    """Calculate line totals for a single invoice item."""
    vat_rate = VAT_RATES.get(vat_rate_str, 0.19)
    net_total = round(quantity * unit_price, 2)
    vat_amount = round(net_total * vat_rate, 2)
    gross_total = round(net_total + vat_amount, 2)
    return {
        "net_total": net_total,
        "vat_amount": vat_amount,
        "gross_total": gross_total,
        "vat_rate": vat_rate_str,
    }


def calculate_invoice_totals(items: List[Dict], tax_free: bool = False) -> Dict:
    """Calculate subtotal, total VAT, and grand total for all items."""
    subtotal = 0.0
    total_vat = 0.0
    vat_breakdown = {}  # vat_rate -> amount

    for item in items:
        vat_rate_str = item.get("vat_rate", "19") if not tax_free else "0"
        result = calculate_item_totals(
            quantity=item["quantity"],
            unit_price=item["unit_price"],
            vat_rate_str=vat_rate_str,
        )
        subtotal += result["net_total"]
        total_vat += result["vat_amount"]

        if vat_rate_str not in vat_breakdown:
            vat_breakdown[vat_rate_str] = 0.0
        vat_breakdown[vat_rate_str] += result["vat_amount"]

    subtotal = round(subtotal, 2)
    total_vat = round(total_vat, 2)
    grand_total = round(subtotal + total_vat, 2)

    return {
        "subtotal": subtotal,
        "vat_amount": total_vat,
        "total": grand_total,
        "vat_breakdown": {k: round(v, 2) for k, v in vat_breakdown.items()},
    }


def format_currency(amount: float, currency: str = "EUR") -> str:
    """Format amount as currency string."""
    if currency == "EUR":
        return f"€{amount:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    return f"{currency} {amount:,.2f}"
