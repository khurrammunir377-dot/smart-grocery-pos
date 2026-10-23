import os
import re
import json
import datetime
import requests
from decimal import Decimal
from django.shortcuts import render, get_object_or_404
from django.http import JsonResponse
from django.db import transaction
from django.db.models import F, Sum, Q, Count
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.clickjacking import xframe_options_exempt
from django.contrib.auth.models import User

from .models import (
    Invoice, InvoiceRefund, Product, StockAdjustment,
    Supplier, PurchaseBill, SupplierPayment,
    CustomerKhata, KhataPayment,
    ExpenseCategory, Expense, CashRegisterSession, UserProfile
)

# Read WA gateway base URL from Vercel service binding if provided, fallback to local port 5005
WA_BASE_URL = os.environ.get("WA_GATEWAY_URL", "http://127.0.0.1:5005").rstrip('/')
GATEWAY_URL = f"{WA_BASE_URL}/send-message"

def normalize_whatsapp_phone(raw_phone):
    clean = "".join(filter(str.isdigit, raw_phone or ""))
    if not clean:
        return ""
    if clean.startswith("00"):
        clean = clean[2:]
    if clean.startswith("05") and len(clean) == 10:
        clean = "971" + clean[1:]
    elif clean.startswith("5") and len(clean) == 9:
        clean = "971" + clean
    elif clean.startswith("03") and len(clean) == 11:
        clean = "92" + clean[1:]
    return clean

KNOWN_DEFAULTS = {
    'onion': ('Onion', 3.5, 2.2, '1 Kg'), 'pyaz': ('Onion', 3.5, 2.2, '1 Kg'),
    'tomato': ('Tomato', 4.0, 2.5, '1 Kg'), 'tamatar': ('Tomato', 4.0, 2.5, '1 Kg'),
    'potato': ('Potato', 2.5, 1.6, '1 Kg'), 'aloo': ('Potato', 2.5, 1.6, '1 Kg'),
    'garlic': ('Garlic', 6.0, 3.8, '500g'), 'milk': ('Fresh Milk', 6.0, 4.5, '1 L'),
    'bread': ('Bread', 4.5, 3.2, '1 Pc'), 'eggs': ('Eggs', 5.0, 3.6, '6 Pcs'),
    'sugar': ('White Sugar', 4.0, 2.9, '1 Kg'), 'rice': ('Basmati Rice', 7.5, 5.3, '1 Kg'),
    'oil': ('Cooking Oil', 14.0, 10.5, '1 L'), 'water': ('Water Bottle', 1.5, 0.85, '1.5 L'),
    'drink': ('Soft Drink', 2.5, 1.7, '1.5 L'), 'tea': ('Tea Dust', 12.0, 8.8, '400g'),
    'chicken': ('Fresh Chicken', 15.0, 11.5, '1 Kg'), 'apple': ('Red Apples', 6.5, 4.2, '1 Kg')
}

def parse_grocery_text_advanced(raw_text):
    if not raw_text: return []
    text = raw_text.replace(',', '\n')
    text = re.sub(r'\bi\s*kg\b', '1kg', text, flags=re.IGNORECASE)
    tokens = [p.strip() for p in re.split(r'\n|\band\b|&', text) if p.strip()]

    items = []
    for token in tokens:
        m = re.match(r'^(?:(\d+(?:\.\d+)?)\s*(?:x|\*|pcs|pc)?\s+)?(.*?)(?:\s+(\d+(?:\.\d+)?))?$', token, re.IGNORECASE)
        qty, unit, name, price, cost = 1.0, '1 Pc', token, 0.0, 0.0
        if m:
            if m.group(1): qty = float(m.group(1))
            if m.group(2): name = m.group(2).strip()
            if m.group(3): price = float(m.group(3))

        clean_key = re.sub(r'[^a-zA-Z0-9\u0600-\u06FF]', '', name.lower())
        found_key = next((k for k in KNOWN_DEFAULTS if k in clean_key), None)
        if found_key:
            name, def_price, def_cost, unit = KNOWN_DEFAULTS[found_key]
            if price <= 0.0: price = def_price
            cost = def_cost
        else:
            prod = Product.objects.filter(Q(name__icontains=name) | Q(name__icontains=clean_key)).first()
            if prod:
                if price <= 0.0: price = float(prod.unit_price)
                cost = float(prod.cost_price or Decimal('0.00'))

        items.append({
            'name': name,
            'qty': qty,
            'unit': unit,
            'unit_price': price,
            'cost_price': cost,
            'line_total': round(qty * price, 2),
            'line_cost': round(qty * cost, 2)
        })
    return items

def laptop_pos_view(request):
    store_name = 'Al Madina Grocery'
    currency = 'AED'
    language = 'ur'
    user_name = 'admin'
    is_authenticated = request.user.is_authenticated

    if is_authenticated:
        user_name = request.user.username
        # Check RegisteredMerchant profile
        merchant = getattr(request.user, 'merchant_profile', None)
        if merchant:
            store_name = merchant.store_name or store_name
            currency = merchant.currency or currency
            language = getattr(merchant, 'language', 'ur') or 'ur'

    context = {
        'store_name': store_name,
        'currency': currency,
        'language': language,
        'user_name': user_name,
        'is_logged_in': is_authenticated,
    }
    return render(request, 'laptop_pos.html', context)

# ==========================================
# 1. SALES & BILLING APIs
# ==========================================

@csrf_exempt
def parse_preview_api(request):
    raw_text = request.POST.get('raw_text', '')
    return JsonResponse({'items': parse_grocery_text_advanced(raw_text)})

@csrf_exempt
@transaction.atomic
def create_invoice_api(request):
    if request.method != 'POST': return JsonResponse({'error': 'POST only'}, status=405)

    phone = request.POST.get('customer_phone', '').strip()
    cust_name = request.POST.get('customer_name', '').strip() or 'Walk-in'
    payment_mode = request.POST.get('payment_mode', 'paid_cash')
    raw_text = request.POST.get('raw_text', '').strip()
    discount = Decimal(str(request.POST.get('discount', '0.0') or '0.0'))
    round_off = Decimal(str(request.POST.get('round_off', '0.0') or '0.0'))
    cashier_name = request.POST.get('cashier_name', 'Cashier').strip() or 'Cashier'

    split_cash = Decimal(str(request.POST.get('split_cash', '0.0') or '0.0'))
    split_card = Decimal(str(request.POST.get('split_card', '0.0') or '0.0'))

    items = parse_grocery_text_advanced(raw_text)
    subtotal = sum(Decimal(str(item['line_total'])) for item in items)
    cost_total = sum(Decimal(str(item.get('line_cost', 0))) for item in items)
    grand_total = max(Decimal('0.0'), subtotal - discount - round_off)
    profit = grand_total - cost_total

    invoice = Invoice.objects.create(
        customer_phone=phone,
        customer_name=cust_name,
        parsed_items=items,
        raw_input=raw_text,
        subtotal=subtotal,
        discount=discount,
        round_off=round_off,
        grand_total=grand_total,
        cost_total=cost_total,
        profit=profit,
        payment_mode=payment_mode,
        split_cash=split_cash,
        split_card=split_card,
        cashier_name=cashier_name,
        status='completed'
    )

    # Stock decrement
    for item in items:
        p_name = item['name'].strip()
        prod = Product.objects.filter(Q(name__icontains=p_name) | Q(name__iexact=p_name)).first()
        if prod:
            Product.objects.filter(id=prod.id).update(current_stock=F('current_stock') - int(item['qty']))

    # Customer Khata & Loyalty
    if phone or (cust_name and cust_name.lower() != 'walk-in'):
        khata, _ = CustomerKhata.objects.get_or_create(phone=phone or cust_name, defaults={'name': cust_name})
        if payment_mode == 'khata':
            khata.outstanding_balance = Decimal(str(khata.outstanding_balance or '0.00')) + grand_total
        # Award loyalty points: 1 point per 10 AED
        earned_points = int(grand_total // Decimal('10.0'))
        khata.loyalty_points += earned_points
        khata.save()

    share_url = request.build_absolute_uri(f"/bill/view/{invoice.access_token}/")
    
    # WhatsApp Silent Delivery
    norm_phone = normalize_whatsapp_phone(phone)
    wa_sent = False
    if norm_phone:
        mode_label = {
            'paid_cash': 'کیش (Cash)',
            'paid_card': 'کارڈ (Card)',
            'khata': 'کھاتہ ادھار (Khata)',
            'split': f'مکس (کیش: {split_cash} + کارڈ: {split_card})'
        }.get(payment_mode, 'کیش (Cash)')

        msg = (
            f"محترم {cust_name}!\n"
            f"آپ کا گروسری بل تیار ہے (#{invoice.id})\n"
            f"صافی رقم: AED {grand_total}\n"
            f"طریقہ ادائیگی: {mode_label}\n\n"
            f"آن لائن رسید اور آئٹمز دیکھنے کے لیے لنک کھولیں:\n{share_url}\n\n"
            f"خریداری کا شکریہ! (Al Madina Smart POS)"
        )
        try:
            r = requests.post(GATEWAY_URL, json={"phone": norm_phone, "message": msg}, timeout=4)
            if r.status_code == 200 and r.json().get('success'):
                wa_sent = True
        except Exception:
            pass

    import urllib.parse
    wa_direct_link = ""
    if norm_phone and msg:
        wa_direct_link = f"https://api.whatsapp.com/send?phone={norm_phone}&text={urllib.parse.quote(msg)}"

    return JsonResponse({
        'success': True,
        'invoice_id': invoice.id,
        'token': str(invoice.access_token),
        'grand_total': str(grand_total),
        'profit': str(profit),
        'share_url': share_url,
        'wa_sent': wa_sent,
        'wa_direct_link': wa_direct_link
    })

@csrf_exempt
@transaction.atomic
def refund_invoice_api(request):
    if request.method != 'POST': return JsonResponse({'error': 'POST only'}, status=405)
    
    invoice_id = request.POST.get('invoice_id')
    reason = request.POST.get('reason', 'Customer Return').strip()
    refunded_by = request.POST.get('refunded_by', 'Manager').strip()
    
    invoice = get_object_or_404(Invoice, id=invoice_id)
    if invoice.status == 'refunded':
        return JsonResponse({'success': False, 'error': 'Invoice already refunded'})

    # Restock products
    for item in invoice.parsed_items:
        p_name = item.get('name', '').strip()
        qty = int(item.get('qty', 1))
        prod = Product.objects.filter(Q(name__icontains=p_name) | Q(name__iexact=p_name)).first()
        if prod:
            Product.objects.filter(id=prod.id).update(current_stock=F('current_stock') + qty)
            StockAdjustment.objects.create(
                product=prod,
                adjustment_type='in',
                quantity=qty,
                reason=f"Refund INV #{invoice.id}: {reason}",
                adjusted_by=refunded_by
            )

    # If khata, reverse outstanding balance
    if invoice.payment_mode == 'khata' and invoice.customer_phone:
        khata = CustomerKhata.objects.filter(Q(phone=invoice.customer_phone) | Q(name=invoice.customer_name)).first()
        if khata:
            khata.outstanding_balance = max(Decimal('0.00'), khata.outstanding_balance - invoice.grand_total)
            khata.save()

    invoice.status = 'refunded'
    invoice.save()

    InvoiceRefund.objects.create(
        invoice=invoice,
        refund_amount=invoice.grand_total,
        reason=reason,
        restocked=True,
        refunded_by=refunded_by
    )

    return JsonResponse({'success': True, 'invoice_id': invoice.id, 'refund_amount': str(invoice.grand_total)})

def invoice_detail_api(request, token):
    inv = get_object_or_404(Invoice, access_token=token) if not str(token).isdigit() else get_object_or_404(Invoice, id=int(token))
    return JsonResponse({
        'id': inv.id,
        'token': str(inv.access_token),
        'store_name': inv.store_name,
        'customer_name': inv.customer_name or 'Walk-in',
        'customer_phone': inv.customer_phone or '',
        'created_at': inv.created_at.isoformat(),
        'status': inv.status,
        'cashier_name': inv.cashier_name,
        'payment_mode': inv.get_payment_mode_display(),
        'items': inv.parsed_items,
        'subtotal': str(inv.subtotal),
        'discount': str(inv.discount),
        'round_off': str(inv.round_off),
        'grand_total': str(inv.grand_total),
        'share_url': request.build_absolute_uri(f"/bill/view/{inv.access_token}/")
    })

# ==========================================
# 2. INVENTORY & STOCK APIs
# ==========================================

def inventory_list_api(request):
    prods = Product.objects.all().order_by('name')
    data = []
    for p in prods:
        data.append({
            'id': p.id,
            'name': p.name,
            'barcode': p.barcode or '',
            'category': p.category,
            'unit_price': str(p.unit_price),
            'cost_price': str(p.cost_price),
            'margin': str(p.margin),
            'stock': p.current_stock,
            'min_alert_stock': p.min_alert_stock,
            'expiry_date': p.expiry_date.isoformat() if p.expiry_date else None,
            'is_expired': p.is_expired,
            'is_near_expiry': p.is_near_expiry,
            'batch_number': p.batch_number or '',
            'status_class': 'danger' if p.current_stock <= 0 or p.is_expired else ('warning' if p.current_stock <= p.min_alert_stock or p.is_near_expiry else 'success'),
            'status_text': 'Expired / تلف' if p.is_expired else ('Critical / ختم' if p.current_stock <= 0 else ('Low / کم' if p.current_stock <= p.min_alert_stock else 'OK'))
        })
    return JsonResponse({'products': data, 'total_count': len(data)})

@csrf_exempt
@transaction.atomic
def stock_adjust_api(request):
    if request.method != 'POST': return JsonResponse({'error': 'POST only'}, status=405)

    prod_id = request.POST.get('product_id')
    adj_type = request.POST.get('adjustment_type', 'audit') # in, out, damage, expired, audit
    qty = int(request.POST.get('quantity', 0))
    reason = request.POST.get('reason', '').strip()
    adjusted_by = request.POST.get('adjusted_by', 'Admin').strip()

    prod = get_object_or_404(Product, id=prod_id)
    prev_stock = prod.current_stock

    if adj_type in ['in']:
        new_stock = prev_stock + qty
    elif adj_type in ['out', 'damage', 'expired']:
        new_stock = max(0, prev_stock - qty)
    else: # audit replaces
        new_stock = qty

    prod.current_stock = new_stock
    prod.save()

    adj = StockAdjustment.objects.create(
        product=prod,
        adjustment_type=adj_type,
        quantity=qty,
        previous_stock=prev_stock,
        new_stock=new_stock,
        reason=reason,
        adjusted_by=adjusted_by
    )

    return JsonResponse({'success': True, 'product_id': prod.id, 'previous_stock': prev_stock, 'new_stock': new_stock})

@csrf_exempt
@transaction.atomic
def quick_stock_in_api(request):
    raw_text = request.POST.get('raw_text', '').strip()
    items = parse_grocery_text_advanced(raw_text)
    updated_records = []
    for it in items:
        p_name = it['name'].strip()
        add_qty = int(float(it['qty']))
        clean_token = p_name.split('/')[0].strip()
        prod = Product.objects.filter(Q(name__icontains=clean_token) | Q(name__icontains=p_name)).first()
        if not prod:
            prod = Product.objects.create(
                name=f"{clean_token} / {clean_token}",
                unit_price=Decimal(str(it['unit_price'] or '0.00')),
                cost_price=Decimal(str(it.get('cost_price', 0.0) or '0.00')),
                current_stock=add_qty
            )
        else:
            Product.objects.filter(id=prod.id).update(current_stock=F('current_stock') + add_qty)
            prod.refresh_from_db()
        updated_records.append({'name': prod.name, 'added': add_qty, 'new_stock': prod.current_stock})
    return JsonResponse({'success': True, 'count': len(updated_records), 'records': updated_records})

@csrf_exempt
def update_product_api(request):
    if request.method == 'POST':
        p = get_object_or_404(Product, id=request.POST.get('product_id'))
        if request.POST.get('name'): p.name = request.POST.get('name')
        if request.POST.get('unit_price'): p.unit_price = Decimal(request.POST.get('unit_price'))
        if request.POST.get('cost_price'): p.cost_price = Decimal(request.POST.get('cost_price'))
        if request.POST.get('stock'): p.current_stock = int(request.POST.get('stock'))
        if request.POST.get('category'): p.category = request.POST.get('category')
        if request.POST.get('expiry_date'):
            try: p.expiry_date = datetime.datetime.strptime(request.POST.get('expiry_date'), '%Y-%m-%d').date()
            except Exception: pass
        if request.POST.get('batch_number'): p.batch_number = request.POST.get('batch_number')
        p.barcode = request.POST.get('barcode') or None
        p.save()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'POST only'}, status=400)

@csrf_exempt
def delete_product_api(request):
    if request.method == 'POST':
        Product.objects.filter(id=request.POST.get('product_id')).delete()
        return JsonResponse({'success': True})
    return JsonResponse({'error': 'POST only'}, status=400)

def barcode_lookup_api(request):
    p = Product.objects.filter(barcode=request.GET.get('code', '').strip()).first()
    return JsonResponse({
        'found': bool(p),
        'name': p.name if p else '',
        'price': str(p.unit_price) if p else '0',
        'cost': str(p.cost_price) if p else '0',
        'stock': p.current_stock if p else 0
    })

# ==========================================
# 3. PURCHASES & SUPPLIERS APIs
# ==========================================

def suppliers_list_api(request):
    sups = Supplier.objects.all().order_by('name')
    data = []
    for s in sups:
        data.append({
            'id': s.id,
            'name': s.name,
            'company_name': s.company_name,
            'phone': s.phone,
            'email': s.email or '',
            'address': s.address,
            'outstanding_payable': str(s.outstanding_payable),
            'bills_count': s.purchases.count()
        })
    return JsonResponse({'suppliers': data})

@csrf_exempt
def add_supplier_api(request):
    if request.method != 'POST': return JsonResponse({'error': 'POST only'}, status=405)
    name = request.POST.get('name', '').strip()
    company = request.POST.get('company_name', '').strip()
    phone = request.POST.get('phone', '').strip()
    email = request.POST.get('email', '').strip()
    address = request.POST.get('address', '').strip()
    payable = Decimal(str(request.POST.get('outstanding_payable', '0.0') or '0.0'))

    if not name: return JsonResponse({'error': 'Supplier name required'}, status=400)

    sup = Supplier.objects.create(
        name=name, company_name=company, phone=phone, email=email or None, address=address,
        outstanding_payable=payable
    )
    return JsonResponse({'success': True, 'supplier_id': sup.id, 'name': sup.name})

@csrf_exempt
@transaction.atomic
def create_purchase_bill_api(request):
    if request.method != 'POST': return JsonResponse({'error': 'POST only'}, status=405)

    supplier_id = request.POST.get('supplier_id')
    bill_no = request.POST.get('bill_number', f"PB-{int(timezone.now().timestamp())}")
    total_amount = Decimal(str(request.POST.get('total_amount', '0.0') or '0.0'))
    paid_amount = Decimal(str(request.POST.get('paid_amount', '0.0') or '0.0'))
    notes = request.POST.get('notes', '').strip()
    raw_items = request.POST.get('items', '[]')

    try:
        items = json.loads(raw_items)
    except Exception:
        items = []

    supplier = get_object_or_404(Supplier, id=supplier_id)
    balance_due = max(Decimal('0.00'), total_amount - paid_amount)
    status = 'paid' if balance_due == 0 else ('partial' if paid_amount > 0 else 'unpaid')

    # Update supplier payable
    supplier.outstanding_payable += balance_due
    supplier.save()

    # Update product stock & cost
    for it in items:
        p_name = it.get('name', '').strip()
        qty = int(it.get('qty', 0))
        cost = Decimal(str(it.get('cost_price', 0.0) or '0.0'))
        expiry = it.get('expiry_date')
        batch = it.get('batch_number')

        prod = Product.objects.filter(name__iexact=p_name).first()
        if not prod:
            prod = Product.objects.create(
                name=p_name,
                cost_price=cost,
                unit_price=cost * Decimal('1.25'), # 25% default markup
                current_stock=qty,
                batch_number=batch
            )
        else:
            prod.current_stock += qty
            if cost > 0: prod.cost_price = cost
            if batch: prod.batch_number = batch
            if expiry:
                try: prod.expiry_date = datetime.datetime.strptime(expiry, '%Y-%m-%d').date()
                except Exception: pass
            prod.save()

    pb = PurchaseBill.objects.create(
        supplier=supplier,
        bill_number=bill_no,
        total_amount=total_amount,
        paid_amount=paid_amount,
        payment_status=status,
        items=items,
        notes=notes
    )

    return JsonResponse({'success': True, 'purchase_id': pb.id, 'bill_number': pb.bill_number})

@csrf_exempt
@transaction.atomic
def pay_supplier_api(request):
    if request.method != 'POST': return JsonResponse({'error': 'POST only'}, status=405)

    supplier_id = request.POST.get('supplier_id')
    amount = Decimal(str(request.POST.get('amount', '0.0') or '0.0'))
    mode = request.POST.get('payment_mode', 'Cash')
    ref = request.POST.get('reference', '').strip()

    supplier = get_object_or_404(Supplier, id=supplier_id)
    supplier.outstanding_payable = max(Decimal('0.00'), supplier.outstanding_payable - amount)
    supplier.save()

    sp = SupplierPayment.objects.create(
        supplier=supplier,
        amount=amount,
        payment_mode=mode,
        reference=ref
    )

    # Automatically record as expense in accounts
    sup_cat, _ = ExpenseCategory.objects.get_or_create(name="Supplier Payments / سپلائر ادائیگی")
    Expense.objects.create(
        category=sup_cat,
        title=f"Supplier Payout: {supplier.name}",
        amount=amount,
        payment_mode=mode,
        notes=ref or f"Payment to {supplier.name}"
    )

    return JsonResponse({'success': True, 'supplier_id': supplier.id, 'new_balance': str(supplier.outstanding_payable)})

# ==========================================
# 4. CUSTOMERS & KHATA APIs
# ==========================================

def khata_list_api(request):
    customers = CustomerKhata.objects.all().order_by('-outstanding_balance')
    return JsonResponse({
        'customers': [
            {
                'id': c.id,
                'name': c.name,
                'phone': c.phone,
                'address': c.address,
                'balance': str(c.outstanding_balance),
                'credit_limit': str(c.credit_limit),
                'loyalty_points': c.loyalty_points
            } for c in customers
        ]
    })

@csrf_exempt
def add_customer_api(request):
    if request.method != 'POST': return JsonResponse({'error': 'POST only'}, status=405)
    name = request.POST.get('name', '').strip()
    phone = request.POST.get('phone', '').strip()
    address = request.POST.get('address', '').strip()
    credit_limit = Decimal(str(request.POST.get('credit_limit', '1000.0') or '1000.0'))

    if not phone or not name: return JsonResponse({'error': 'Name and phone required'}, status=400)

    cust, _ = CustomerKhata.objects.update_or_create(
        phone=phone,
        defaults={'name': name, 'address': address, 'credit_limit': credit_limit}
    )
    return JsonResponse({'success': True, 'customer_id': cust.id, 'name': cust.name})

@csrf_exempt
@transaction.atomic
def khata_pay_api(request):
    if request.method != 'POST': return JsonResponse({'error': 'POST only'}, status=405)

    phone = request.POST.get('phone', '').strip()
    amount = Decimal(str(request.POST.get('amount', '0.0') or '0.0'))
    mode = request.POST.get('payment_mode', 'Cash')
    notes = request.POST.get('notes', 'Khata Payment').strip()

    khata = CustomerKhata.objects.filter(Q(phone=phone) | Q(name=phone)).first()
    if not khata:
        return JsonResponse({'error': 'Customer not found'}, status=404)

    khata.outstanding_balance = max(Decimal('0.00'), khata.outstanding_balance - amount)
    khata.save()

    KhataPayment.objects.create(
        customer=khata,
        amount_paid=amount,
        payment_mode=mode,
        notes=notes
    )

    # WhatsApp confirmation
    norm_phone = normalize_whatsapp_phone(khata.phone)
    if norm_phone:
        msg = (
            f"محترم {khata.name}!\n"
            f"آپ کی ادھار کھاتہ ادائیگی وصول ہو گئی ہے۔\n"
            f"وصول شدہ رقم: AED {amount}\n"
            f"باقی واجب الادا رقم: AED {khata.outstanding_balance}\n"
            f"شکریہ! (Al Madina Grocery)"
        )
        try:
            requests.post(GATEWAY_URL, json={"phone": norm_phone, "message": msg}, timeout=4)
        except Exception:
            pass

    return JsonResponse({
        'success': True,
        'customer_name': khata.name,
        'amount_paid': str(amount),
        'remaining_balance': str(khata.outstanding_balance)
    })

def customer_statement_api(request):
    phone = request.GET.get('phone', '').strip()
    invoices = Invoice.objects.filter(Q(customer_phone=phone) | Q(customer_name=phone), payment_mode='khata').order_by('-created_at')
    khata = CustomerKhata.objects.filter(Q(phone=phone) | Q(name=phone)).first()
    payments = KhataPayment.objects.filter(customer=khata).order_by('-created_at') if khata else []
    return JsonResponse({
        'name': khata.name if khata else phone,
        'phone': khata.phone if khata else phone,
        'credit_limit': str(khata.credit_limit) if khata else '1000.00',
        'loyalty_points': khata.loyalty_points if khata else 0,
        'total_outstanding': str(khata.outstanding_balance) if khata else '0.00',
        'invoices': [{'id': inv.id, 'date': inv.created_at.isoformat(), 'total': str(inv.grand_total), 'items': inv.parsed_items, 'token': str(inv.access_token)} for inv in invoices],
        'payments': [{'id': p.id, 'date': p.created_at.isoformat(), 'amount': str(p.amount_paid), 'mode': p.payment_mode, 'notes': p.notes} for p in payments]
    })

# ==========================================
# 5. ACCOUNTS & EXPENSES APIs
# ==========================================

def expenses_list_api(request):
    expenses = Expense.objects.all().order_by('-created_at')[:50]
    categories = ExpenseCategory.objects.all()
    return JsonResponse({
        'categories': [{'id': c.id, 'name': c.name} for c in categories],
        'expenses': [
            {
                'id': e.id,
                'category': e.category.name if e.category else 'General',
                'title': e.title,
                'amount': str(e.amount),
                'mode': e.payment_mode,
                'date': e.expense_date.isoformat(),
                'notes': e.notes,
                'by': e.created_by
            } for e in expenses
        ]
    })

@csrf_exempt
def add_expense_api(request):
    if request.method != 'POST': return JsonResponse({'error': 'POST only'}, status=405)

    cat_id = request.POST.get('category_id')
    title = request.POST.get('title', '').strip()
    amount = Decimal(str(request.POST.get('amount', '0.0') or '0.0'))
    mode = request.POST.get('payment_mode', 'Cash')
    notes = request.POST.get('notes', '').strip()
    created_by = request.POST.get('created_by', 'Admin').strip()

    if not title or amount <= 0:
        return JsonResponse({'error': 'Title and valid amount required'}, status=400)

    category = ExpenseCategory.objects.filter(id=cat_id).first() if cat_id else None
    exp = Expense.objects.create(
        category=category,
        title=title,
        amount=amount,
        payment_mode=mode,
        notes=notes,
        created_by=created_by
    )
    return JsonResponse({'success': True, 'expense_id': exp.id, 'title': exp.title, 'amount': str(exp.amount)})

def cash_drawer_status_api(request):
    today = timezone.now().date()
    drawer = CashRegisterSession.objects.filter(status='open').last()
    
    opening_cash = drawer.opening_cash if drawer else Decimal('0.00')
    
    # Today's cash receipts
    today_invoices = Invoice.objects.filter(created_at__date=today, status='completed')
    cash_sales = today_invoices.filter(payment_mode='paid_cash').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    split_cash = today_invoices.filter(payment_mode='split').aggregate(Sum('split_cash'))['split_cash__sum'] or Decimal('0.00')
    khata_cash_received = KhataPayment.objects.filter(created_at__date=today, payment_mode='Cash').aggregate(Sum('amount_paid'))['amount_paid__sum'] or Decimal('0.00')

    # Cash outflows
    cash_expenses = Expense.objects.filter(expense_date=today, payment_mode='Cash').aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')

    expected_cash = opening_cash + cash_sales + split_cash + khata_cash_received - cash_expenses

    return JsonResponse({
        'has_open_drawer': bool(drawer),
        'cashier_name': drawer.cashier_name if drawer else 'None',
        'opened_at': drawer.opened_at.isoformat() if drawer else None,
        'opening_cash': str(opening_cash),
        'cash_sales': str(cash_sales + split_cash),
        'khata_cash_collected': str(khata_cash_received),
        'cash_expenses': str(cash_expenses),
        'expected_cash': str(expected_cash)
    })

@csrf_exempt
def open_cash_drawer_api(request):
    if request.method != 'POST': return JsonResponse({'error': 'POST only'}, status=405)
    opening_cash = Decimal(str(request.POST.get('opening_cash', '0.0') or '0.0'))
    cashier = request.POST.get('cashier_name', 'Cashier').strip()
    notes = request.POST.get('notes', 'Shift open').strip()

    # Close any existing open session
    CashRegisterSession.objects.filter(status='open').update(status='closed', closed_at=timezone.now())

    drawer = CashRegisterSession.objects.create(
        cashier_name=cashier,
        opening_cash=opening_cash,
        status='open',
        notes=notes
    )
    return JsonResponse({'success': True, 'drawer_id': drawer.id, 'opening_cash': str(drawer.opening_cash)})

@csrf_exempt
def close_cash_drawer_api(request):
    if request.method != 'POST': return JsonResponse({'error': 'POST only'}, status=405)
    closing_cash = Decimal(str(request.POST.get('closing_cash', '0.0') or '0.0'))
    notes = request.POST.get('notes', 'Shift closed').strip()

    drawer = CashRegisterSession.objects.filter(status='open').last()
    if not drawer: return JsonResponse({'error': 'No open drawer session found'}, status=404)

    drawer.closing_cash = closing_cash
    drawer.status = 'closed'
    drawer.closed_at = timezone.now()
    drawer.notes = (drawer.notes + " | " + notes).strip()
    drawer.save()

    return JsonResponse({'success': True, 'drawer_id': drawer.id, 'closed_at': drawer.closed_at.isoformat()})

# ==========================================
# 6. REPORTS & ANALYTICS APIs
# ==========================================

def reports_summary_api(request):
    today = timezone.now().date()
    today_inv = Invoice.objects.filter(created_at__date=today, status='completed')
    products = Product.objects.all().order_by('name')
    return JsonResponse({
        'total_sales': str(today_inv.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')),
        'cash_sales': str(today_inv.filter(payment_mode='paid_cash').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')),
        'khata_sales': str(today_inv.filter(payment_mode='khata').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')),
        'recent_bills': [{'id': inv.id, 'token': str(inv.access_token), 'customer': inv.customer_name, 'mode': inv.payment_mode, 'amount': str(inv.grand_total), 'status': inv.status, 'time': inv.created_at.isoformat()} for inv in Invoice.objects.all().order_by('-id')[:25]],
        'inventory': [{'id': p.id, 'name': p.name, 'barcode': p.barcode or '', 'price': str(p.unit_price), 'cost': str(p.cost_price), 'stock': p.current_stock, 'expiry': p.expiry_date.isoformat() if p.expiry_date else None, 'status_class': 'danger' if p.current_stock <= 0 else ('warning' if p.current_stock <= p.min_alert_stock else 'success'), 'status_text': 'Critical' if p.current_stock <= 0 else ('Low' if p.current_stock <= p.min_alert_stock else 'OK')} for p in products]
    })

def advanced_reports_api(request):
    period = request.GET.get('period', 'today') # today, yesterday, week, month, all
    now = timezone.now()
    
    if period == 'today':
        start_date = now.date()
        inv_qs = Invoice.objects.filter(created_at__date=start_date, status='completed')
        exp_qs = Expense.objects.filter(expense_date=start_date)
    elif period == 'yesterday':
        start_date = now.date() - datetime.timedelta(days=1)
        inv_qs = Invoice.objects.filter(created_at__date=start_date, status='completed')
        exp_qs = Expense.objects.filter(expense_date=start_date)
    elif period == 'week':
        start_date = now.date() - datetime.timedelta(days=7)
        inv_qs = Invoice.objects.filter(created_at__date__gte=start_date, status='completed')
        exp_qs = Expense.objects.filter(expense_date__gte=start_date)
    elif period == 'month':
        start_date = now.date() - datetime.timedelta(days=30)
        inv_qs = Invoice.objects.filter(created_at__date__gte=start_date, status='completed')
        exp_qs = Expense.objects.filter(expense_date__gte=start_date)
    else:
        inv_qs = Invoice.objects.filter(status='completed')
        exp_qs = Expense.objects.all()

    total_revenue = inv_qs.aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    total_cost = inv_qs.aggregate(Sum('cost_total'))['cost_total__sum'] or Decimal('0.00')
    gross_profit = total_revenue - total_cost
    total_expenses = exp_qs.aggregate(Sum('amount'))['amount__sum'] or Decimal('0.00')
    net_profit = gross_profit - total_expenses

    cash_sales = inv_qs.filter(payment_mode='paid_cash').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    card_sales = inv_qs.filter(payment_mode='paid_card').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    khata_sales = inv_qs.filter(payment_mode='khata').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')
    split_sales = inv_qs.filter(payment_mode='split').aggregate(Sum('grand_total'))['grand_total__sum'] or Decimal('0.00')

    # Top selling items
    item_counts = {}
    for inv in inv_qs:
        for it in inv.parsed_items:
            name = it.get('name', 'Item')
            qty = float(it.get('qty', 1))
            line_tot = float(it.get('line_total', 0))
            if name not in item_counts:
                item_counts[name] = {'name': name, 'qty': 0, 'total': 0.0}
            item_counts[name]['qty'] += qty
            item_counts[name]['total'] += line_tot

    top_items = sorted(item_counts.values(), key=lambda x: x['total'], reverse=True)[:10]

    # Cashier breakdown
    cashier_breakdown = list(inv_qs.values('cashier_name').annotate(sales_count=Count('id'), total_sales=Sum('grand_total')).order_by('-total_sales'))

    # Low stock & Expiry items
    all_products = Product.objects.all()
    low_stock_list = [{'id': p.id, 'name': p.name, 'stock': p.current_stock, 'min_alert': p.min_alert_stock} for p in all_products if p.current_stock <= p.min_alert_stock]
    expired_list = [{'id': p.id, 'name': p.name, 'expiry': p.expiry_date.isoformat(), 'stock': p.current_stock} for p in all_products if p.is_expired]
    near_expiry_list = [{'id': p.id, 'name': p.name, 'expiry': p.expiry_date.isoformat(), 'stock': p.current_stock} for p in all_products if p.is_near_expiry]

    return JsonResponse({
        'period': period,
        'total_revenue': str(total_revenue),
        'total_cost': str(total_cost),
        'gross_profit': str(gross_profit),
        'total_expenses': str(total_expenses),
        'net_profit': str(net_profit),
        'payment_methods': {
            'cash': str(cash_sales),
            'card': str(card_sales),
            'khata': str(khata_sales),
            'split': str(split_sales),
        },
        'top_items': top_items,
        'cashiers': cashier_breakdown,
        'low_stock_count': len(low_stock_list),
        'low_stock': low_stock_list,
        'expired_count': len(expired_list),
        'expired': expired_list,
        'near_expiry_count': len(near_expiry_list),
        'near_expiry': near_expiry_list,
    })

# ==========================================
# 7. USERS & PERMISSIONS APIs
# ==========================================

@csrf_exempt
def verify_pin_api(request):
    if request.method != 'POST': return JsonResponse({'error': 'POST only'}, status=405)
    pin = request.POST.get('pin', '').strip()

    profile = UserProfile.objects.filter(pin_code=pin).first()
    if not profile:
        return JsonResponse({'success': False, 'error': 'Invalid PIN / غلط پن کوڈ'})

    role_permissions = {
        'admin': {
            'can_manage_products': True,
            'can_delete_products': True,
            'can_view_profits': True,
            'can_refund': True,
            'can_manage_suppliers': True,
            'can_manage_accounts': True,
            'can_manage_users': True,
        },
        'manager': {
            'can_manage_products': True,
            'can_delete_products': False,
            'can_view_profits': True,
            'can_refund': True,
            'can_manage_suppliers': True,
            'can_manage_accounts': True,
            'can_manage_users': False,
        },
        'cashier': {
            'can_manage_products': False,
            'can_delete_products': False,
            'can_view_profits': False,
            'can_refund': False,
            'can_manage_suppliers': False,
            'can_manage_accounts': False,
            'can_manage_users': False,
        }
    }

    return JsonResponse({
        'success': True,
        'username': profile.user.username,
        'role': profile.role,
        'permissions': role_permissions.get(profile.role, role_permissions['cashier'])
    })

def staff_list_api(request):
    profiles = UserProfile.objects.all().select_related('user')
    return JsonResponse({
        'staff': [
            {
                'id': p.id,
                'username': p.user.username,
                'role': p.get_role_display(),
                'role_code': p.role,
                'phone': p.phone
            } for p in profiles
        ]
    })

@xframe_options_exempt
def public_bill_view(request, token):
    inv = get_object_or_404(Invoice, access_token=token) if not str(token).isdigit() else get_object_or_404(Invoice, id=int(token))
    return render(request, 'public_receipt.html', {'invoice': inv})
