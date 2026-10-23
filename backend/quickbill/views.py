import os
import uuid
import requests
from decimal import Decimal
from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.models import User
from django.db.models import Count, Sum
from django.utils import timezone
from .models import BusinessProfile, Invoice, InvoiceItem, VisitorLog, RegisteredMerchant

# Read WA gateway base URL from Vercel service binding if provided, fallback to local port 5005
WA_BASE_URL = os.environ.get("WA_GATEWAY_URL", "http://127.0.0.1:5005").rstrip('/')
GATEWAY_URL = f"{WA_BASE_URL}/send-message"

def get_client_ip(request):
    x_forwarded_for = request.META.get('HTTP_X_FORWARDED_FOR')
    if x_forwarded_for:
        ip = x_forwarded_for.split(',')[0].strip()
    else:
        ip = request.META.get('REMOTE_ADDR', '127.0.0.1')
    return ip

def detect_device(ua_string):
    ua = (ua_string or '').lower()
    if 'mobile' in ua or 'android' in ua or 'iphone' in ua:
        return 'Mobile Phone'
    elif 'tablet' in ua or 'ipad' in ua:
        return 'Tablet'
    return 'Desktop PC'

def landing_page(request):
    # Log visitor
    try:
        ip = get_client_ip(request)
        ua = request.META.get('HTTP_USER_AGENT', '')
        ref = request.META.get('HTTP_REFERER', '')[:250] if request.META.get('HTTP_REFERER') else ''
        dev = detect_device(ua)
        user = request.user if request.user.is_authenticated else None
        
        VisitorLog.objects.create(
            ip_address=ip,
            user_agent=ua[:400],
            path=request.path[:250],
            referrer=ref,
            device_type=dev,
            user=user
        )
    except Exception as e:
        pass

    is_logged_in = request.user.is_authenticated
    return render(request, "quickbill/landing.html", {
        "is_logged_in": is_logged_in,
        "username": request.user.username if is_logged_in else ""
    })

@csrf_exempt
def register_merchant_api(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST only"}, status=405)

    store_name = request.POST.get("store_name", "").strip()
    username = request.POST.get("username", "").strip().lower()
    phone = request.POST.get("phone", "").strip()
    password = request.POST.get("password", "").strip()
    business_type = request.POST.get("business_type", "Grocery Store").strip()
    city = request.POST.get("city", "Dubai").strip()
    currency = request.POST.get("currency", "AED").strip()
    language = request.POST.get("language", "ur").strip()

    if not store_name or not username or not password:
        return JsonResponse({"success": False, "error": "Store name, username, and password are required."})

    if User.objects.filter(username=username).exists():
        return JsonResponse({"success": False, "error": f"Username '{username}' is already taken. Please choose another or login."})

    try:
        user = User.objects.create_user(username=username, password=password)
        merchant = RegisteredMerchant.objects.create(
            user=user,
            store_name=store_name,
            phone=phone,
            business_type=business_type,
            city=city,
            currency=currency,
            language=language
        )
        login(request, user)

        # Log event
        ip = get_client_ip(request)
        VisitorLog.objects.create(
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:400],
            path='/api/register-merchant/ (Signup Successful)',
            device_type=detect_device(request.META.get('HTTP_USER_AGENT', '')),
            user=user
        )

        return JsonResponse({
            "success": True,
            "message": "Account created successfully! Redirecting to POS Counter...",
            "redirect_url": "/pos/",
            "store_name": store_name,
            "currency": currency,
            "language": language
        })
    except Exception as e:
        return JsonResponse({"success": False, "error": str(e)})

@csrf_exempt
def login_merchant_api(request):
    if request.method != "POST":
        return JsonResponse({"success": False, "error": "POST only"}, status=405)

    username = request.POST.get("username", "").strip().lower()
    password = request.POST.get("password", "").strip()

    user = authenticate(request, username=username, password=password)
    if user is not None:
        login(request, user)
        # Log event
        ip = get_client_ip(request)
        VisitorLog.objects.create(
            ip_address=ip,
            user_agent=request.META.get('HTTP_USER_AGENT', '')[:400],
            path='/api/login-merchant/ (Login)',
            device_type=detect_device(request.META.get('HTTP_USER_AGENT', '')),
            user=user
        )
        merchant = getattr(user, 'merchant_profile', None)
        return JsonResponse({
            "success": True,
            "message": "Logged in successfully!",
            "redirect_url": "/pos/",
            "store_name": merchant.store_name if merchant else "Al Madina Grocery",
            "currency": merchant.currency if merchant else "AED",
            "language": getattr(merchant, 'language', 'ur') if merchant else "ur"
        })
    else:
        return JsonResponse({"success": False, "error": "Invalid username or password. Please try again."})

def logout_merchant_view(request):
    logout(request)
    return redirect("/")

def normalize_whatsapp_phone(raw_phone, default_country="971"):
    clean = "".join(filter(str.isdigit, raw_phone))
    if not clean:
        return ""
    if clean.startswith("00"):
        clean = clean[2:]
    if clean.startswith("05") and len(clean) == 10:
        clean = "971" + clean[1:]
    elif clean.startswith("03") and len(clean) == 11:
        clean = "92" + clean[1:]
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
        f"Hello {cust_name}!\n\n"
        f"Your receipt #{invoice.invoice_number} ({business_name}) is ready.\n"
        f"Total: {currency} {amount}\n\n"
        f"View digital receipt & PDF:\n"
        f"{view_url}\n\n"
        f"— Powered by Smart Grocery POS"
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
    import urllib.parse
    wa_direct_link = ""
    if phone:
        encoded_msg = urllib.parse.quote(wa_text)
        wa_direct_link = f"https://api.whatsapp.com/send?phone={phone}&text={encoded_msg}"

    return JsonResponse({
        "success": True,
        "invoice_number": invoice.invoice_number,
        "phone_used": phone,
        "token": str(invoice.access_token),
        "view_url": view_url,
        "sent_silently": sent_silently,
        "wa_direct_link": wa_direct_link,
        "gateway_response": gateway_response
    })

def guest_invoice_view(request, token):
    invoice = get_object_or_404(Invoice, access_token=token)
    return render(request, "quickbill/receipt_view.html", {"invoice": invoice})

# ==========================================
# ADMIN & VISITOR CONTROL PANEL
# ==========================================
def dashboard_view(request):
    invoices = Invoice.objects.all().order_by("-created_at")
    total_billed = sum(i.total_amount for i in invoices)
    total_paid = sum(i.paid_amount for i in invoices)
    total_pending = total_billed - total_paid

    # Visitor and Merchant analytics
    recent_visitors = VisitorLog.objects.all().order_by("-visited_at")[:60]
    total_visitors_count = VisitorLog.objects.count()
    unique_ips_count = VisitorLog.objects.values('ip_address').distinct().count()
    
    device_breakdown = VisitorLog.objects.values('device_type').annotate(count=Count('id')).order_by('-count')
    registered_merchants = RegisteredMerchant.objects.all().order_by("-created_at")

    context = {
        "invoices": invoices[:30],
        "total_billed": total_billed,
        "total_paid": total_paid,
        "total_pending": total_pending,
        "invoice_count": invoices.count(),
        "recent_visitors": recent_visitors,
        "total_visitors_count": total_visitors_count,
        "unique_ips_count": unique_ips_count,
        "device_breakdown": device_breakdown,
        "registered_merchants": registered_merchants,
        "merchants_count": registered_merchants.count(),
    }
    return render(request, "quickbill/dashboard.html", context)
