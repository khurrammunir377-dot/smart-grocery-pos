import uuid
import requests
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from .models import BusinessProfile, Invoice, InvoiceItem

GATEWAY_URL = "http://127.0.0.1:5005/send-message"

def landing_page(request):
    return render(request, "quickbill/landing.html")

def normalize_whatsapp_phone(raw_phone, default_country="971"):
    """نمبر کو درست بین الاقوامی واٹس ایپ فارمیٹ میں تبدیل کرنا"""
    clean = "".join(filter(str.isdigit, raw_phone))
    if not clean:
        return ""
    if clean.startswith("00"):
        clean = clean[2:]
    
    # اگر 050 یا 055 وغیرہ ہے (UAE)
    if clean.startswith("05") and len(clean) == 10:
        clean = "971" + clean[1:]
    # اگر 03xx ہے (Pakistan)
    elif clean.startswith("03") and len(clean) == 11:
        clean = "92" + clean[1:]
    # اگر صرف 50 سے شروع ہو اور 9 ہندسے ہوں
    elif clean.startswith("5") and len(clean) == 9:
        clean = "971" + clean
        
    return clean

@csrf_exempt
def instant_invoice_create_api(request):
    if request.method != "POST":
        return JsonResponse({"error": "POST only"}, status=405)

    business_name = request.POST.get("business_name", "My Services").strip()
    currency = request.POST.get("currency", "AED").strip()
    cust_name = request.POST.get("customer_name", "Valued Client").strip()
    raw_phone = request.POST.get("customer_phone", "").strip()
    item_desc = request.POST.get("item_description", "General Service").strip()
    amount = Decimal(str(request.POST.get("amount", "0.00") or "0.00"))
    paid_amount = Decimal(str(request.POST.get("paid_amount", "0.00") or "0.00"))
    status = "paid" if paid_amount >= amount and amount > 0 else ("partial" if paid_amount > 0 else "unpaid")

    phone = normalize_whatsapp_phone(raw_phone)

    biz, _ = BusinessProfile.objects.get_or_create(
        name=business_name,
        defaults={"currency": currency, "phone": phone}
    )

    inv_count = Invoice.objects.count() + 101
    invoice = Invoice.objects.create(
        business=biz,
        invoice_number=f"QB-{inv_count}",
        customer_name=cust_name,
        customer_phone=phone or raw_phone,
        total_amount=amount,
        paid_amount=paid_amount,
        status=status
    )

    InvoiceItem.objects.create(
        invoice=invoice,
        description=item_desc,
        quantity=Decimal("1.00"),
        unit_price=amount
    )

    view_url = request.build_absolute_uri(f"/quickbill/view/{invoice.access_token}/")
    
    wa_text = (
        f"السلام علیکم {cust_name}!\n\n"
        f"آپ کی رسید #{invoice.invoice_number} ({business_name}) تیار ہے۔\n"
        f"کل رقم: {currency} {amount}\n\n"
        f"آن لائن رسید اور پی ڈی ایف کے لیے لنک کھولیں:\n"
        f"{view_url}\n\n"
        f"— Powered by QuickBill"
    )

    sent_silently = False
    gateway_response = ""

    if phone:
        try:
            resp = requests.post(
                GATEWAY_URL,
                json={"phone": phone, "message": wa_text},
                timeout=12
            )
            gateway_response = resp.text
            if resp.status_code == 200 and resp.json().get("success"):
                sent_silently = True
        except Exception as e:
            gateway_response = f"Connection failed to 127.0.0.1:5005: {str(e)}"
    else:
        gateway_response = "No valid phone number provided."

    return JsonResponse({
        "success": True,
        "invoice_number": invoice.invoice_number,
        "phone_used": phone,
        "token": str(invoice.access_token),
        "view_url": view_url,
        "sent_silently": sent_silently,
        "gateway_response": gateway_response
    })

def guest_invoice_view(request, token):
    invoice = get_object_or_404(Invoice, access_token=token)
    return render(request, "quickbill/receipt_view.html", {"invoice": invoice})

def dashboard_view(request):
    invoices = Invoice.objects.all().order_by("-created_at")
    total_billed = sum(i.total_amount for i in invoices)
    total_paid = sum(i.paid_amount for i in invoices)
    total_pending = total_billed - total_paid

    context = {
        "invoices": invoices,
        "total_billed": total_billed,
        "total_paid": total_paid,
        "total_pending": total_pending,
        "invoice_count": invoices.count(),
    }
    return render(request, "quickbill/dashboard.html", context)

