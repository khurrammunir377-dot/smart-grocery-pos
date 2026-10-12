import uuid
from decimal import Decimal
from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

# ==========================================
# 1. INVENTORY & PRODUCTS MODULE
# ==========================================
class Product(models.Model):
    name = models.CharField(max_length=150, unique=True)
    barcode = models.CharField(max_length=50, blank=True, null=True, unique=True)
    category = models.CharField(max_length=100, default='General Grocery')
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    cost_price = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    current_stock = models.IntegerField(default=0)
    min_alert_stock = models.IntegerField(default=5)
    is_loose = models.BooleanField(default=False)
    expiry_date = models.DateField(null=True, blank=True)
    batch_number = models.CharField(max_length=50, blank=True, null=True)

    @property
    def margin(self):
        if self.unit_price > 0 and self.cost_price > 0:
            return round(self.unit_price - self.cost_price, 2)
        return Decimal('0.00')

    @property
    def is_expired(self):
        if self.expiry_date:
            return self.expiry_date < timezone.now().date()
        return False

    @property
    def is_near_expiry(self):
        if self.expiry_date:
            days = (self.expiry_date - timezone.now().date()).days
            return 0 <= days <= 7
        return False

    def __str__(self):
        return f"{self.name} (Stock: {self.current_stock})"

class StockAdjustment(models.Model):
    ADJUSTMENT_TYPES = [
        ('in', 'Manual Stock In / اضافہ'),
        ('out', 'Manual Stock Out / اخراج'),
        ('damage', 'Damaged / نقصان'),
        ('expired', 'Expired Waste / تلف شدہ'),
        ('audit', 'Audit Correction / پڑتال'),
    ]

    product = models.ForeignKey(Product, on_delete=models.CASCADE, related_name="stock_adjustments")
    adjustment_type = models.CharField(max_length=20, choices=ADJUSTMENT_TYPES)
    quantity = models.IntegerField()
    previous_stock = models.IntegerField(default=0)
    new_stock = models.IntegerField(default=0)
    reason = models.CharField(max_length=255, blank=True)
    adjusted_by = models.CharField(max_length=100, default="Admin")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.product.name} ({self.adjustment_type}: {self.quantity})"

# ==========================================
# 2. PURCHASE & SUPPLIERS MODULE
# ==========================================
class Supplier(models.Model):
    name = models.CharField(max_length=150)
    company_name = models.CharField(max_length=150, blank=True)
    phone = models.CharField(max_length=30)
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True)
    outstanding_payable = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.name} - Payable: {self.outstanding_payable}"

class PurchaseBill(models.Model):
    STATUS_CHOICES = [
        ('paid', 'Paid (ادا شدہ)'),
        ('partial', 'Partial (جزوی ادائیگی)'),
        ('unpaid', 'Unpaid (واجب الادا)'),
    ]

    supplier = models.ForeignKey(Supplier, on_delete=models.SET_NULL, null=True, related_name="purchases")
    bill_number = models.CharField(max_length=80)
    bill_date = models.DateField(default=timezone.now)
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=0.0)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='paid')
    items = models.JSONField(default=list)  # [{'name', 'qty', 'cost_price', 'total', 'expiry', 'batch'}]
    notes = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"PO #{self.bill_number} - {self.total_amount}"

class SupplierPayment(models.Model):
    supplier = models.ForeignKey(Supplier, on_delete=models.CASCADE, related_name="payments")
    amount = models.DecimalField(max_digits=12, decimal_places=2)
    payment_mode = models.CharField(max_length=30, default="Cash")
    reference = models.CharField(max_length=100, blank=True)
    paid_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.amount} to {self.supplier.name}"

# ==========================================
# 3. CUSTOMERS & KHATA MODULE
# ==========================================
class CustomerKhata(models.Model):
    name = models.CharField(max_length=100)
    phone = models.CharField(max_length=20, unique=True)
    address = models.TextField(blank=True)
    credit_limit = models.DecimalField(max_digits=10, decimal_places=2, default=1000.0)
    outstanding_balance = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    loyalty_points = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.phone}) - Balance: {self.outstanding_balance}"

class KhataPayment(models.Model):
    customer = models.ForeignKey(CustomerKhata, on_delete=models.CASCADE, related_name="payments")
    amount_paid = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = models.CharField(max_length=30, default="Cash")
    notes = models.CharField(max_length=255, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Payment {self.amount_paid} by {self.customer.name}"

# ==========================================
# 4. SALES & INVOICE MODULE
# ==========================================
class Invoice(models.Model):
    STATUS_CHOICES = [
        ('paid_cash', 'Cash (نقد)'),
        ('paid_card', 'Card (کارڈ)'),
        ('khata', 'Khata / Credit (ادھار)'),
        ('split', 'Split Payment (کیش + کارڈ)'),
    ]

    INVOICE_STATUS = [
        ('completed', 'Completed / مکمل'),
        ('refunded', 'Refunded / ریفنڈ شدہ'),
        ('cancelled', 'Cancelled / منسوخ'),
    ]

    store_name = models.CharField(max_length=150, default="Al Madina Grocery")
    customer_name = models.CharField(max_length=100, blank=True)
    customer_phone = models.CharField(max_length=20)
    parsed_items = models.JSONField(default=list)
    raw_input = models.TextField(blank=True, null=True)
    bill_photo = models.ImageField(upload_to="bills/%Y/%m/", blank=True, null=True)
    subtotal = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    discount = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    round_off = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    grand_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    cost_total = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    profit = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    payment_mode = models.CharField(max_length=20, choices=STATUS_CHOICES, default='paid_cash')
    split_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    split_card = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    status = models.CharField(max_length=20, choices=INVOICE_STATUS, default='completed')
    cashier_name = models.CharField(max_length=100, default="Cashier")
    access_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"INV-{self.id} | {self.grand_total} ({self.payment_mode})"

class InvoiceRefund(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="refunds")
    refund_amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.CharField(max_length=255)
    restocked = models.BooleanField(default=True)
    refunded_by = models.CharField(max_length=100, default="Manager")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Refund #{self.id} for INV-{self.invoice.id} ({self.refund_amount})"

# ==========================================
# 5. ACCOUNTS & EXPENSES MODULE
# ==========================================
class ExpenseCategory(models.Model):
    name = models.CharField(max_length=100, unique=True)
    description = models.CharField(max_length=200, blank=True)

    def __str__(self):
        return self.name

class Expense(models.Model):
    category = models.ForeignKey(ExpenseCategory, on_delete=models.SET_NULL, null=True, related_name="expenses")
    title = models.CharField(max_length=150)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    payment_mode = models.CharField(max_length=30, default="Cash")  # Cash, Card, Bank
    expense_date = models.DateField(default=timezone.now)
    notes = models.TextField(blank=True)
    created_by = models.CharField(max_length=100, default="Admin")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.title} - {self.amount}"

class CashRegisterSession(models.Model):
    cashier_name = models.CharField(max_length=100, default="Cashier")
    opening_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    closing_cash = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    expected_cash = models.DecimalField(max_digits=10, decimal_places=2, default=0.0)
    status = models.CharField(max_length=20, choices=[('open', 'Open'), ('closed', 'Closed')], default='open')
    opened_at = models.DateTimeField(auto_now_add=True)
    closed_at = models.DateTimeField(null=True, blank=True)
    notes = models.TextField(blank=True)

    def __str__(self):
        return f"Drawer ({self.cashier_name}): {self.status}"

# ==========================================
# 6. USERS & PERMISSIONS MODULE
# ==========================================
class UserProfile(models.Model):
    ROLE_CHOICES = [
        ('admin', 'Owner / Admin (مکمل اختیارات)'),
        ('manager', 'Manager (اسٹاک، سپلائر، اکاؤنٹس)'),
        ('cashier', 'Cashier (صرف بلنگ اور سیلز)'),
    ]

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='cashier')
    pin_code = models.CharField(max_length=10, default="1234")
    phone = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.user.username} ({self.role})"
