import uuid
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User

class BusinessProfile(models.Model):
    name = models.CharField(max_length=150, help_text="Business or Freelancer Name")
    tagline = models.CharField(max_length=200, blank=True, null=True, help_text="e.g. AC Repair & Electrical Services")
    phone = models.CharField(max_length=25, help_text="WhatsApp enabled phone number")
    email = models.EmailField(blank=True, null=True)
    address = models.TextField(blank=True, null=True)
    currency = models.CharField(max_length=10, default="AED")
    logo = models.ImageField(upload_to="business_logos/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class Invoice(models.Model):
    STATUS_CHOICES = [
        ('paid', 'Paid (مکمل ادا شدہ)'),
        ('partial', 'Partial (جزوی ادائیگی)'),
        ('unpaid', 'Unpaid (باقی / ادھار)'),
    ]

    business = models.ForeignKey(BusinessProfile, on_delete=models.CASCADE, related_name="invoices", null=True, blank=True)
    invoice_number = models.CharField(max_length=50, unique=True)
    access_token = models.UUIDField(default=uuid.uuid4, unique=True, editable=False)
    customer_name = models.CharField(max_length=150)
    customer_phone = models.CharField(max_length=25)
    notes = models.TextField(blank=True, null=True, help_text="Terms, warranty or payment details")
    status = models.CharField(max_length=15, choices=STATUS_CHOICES, default='paid')
    total_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    paid_amount = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    created_at = models.DateTimeField(auto_now_add=True)

    @property
    def balance_due(self):
        return max(Decimal('0.00'), self.total_amount - self.paid_amount)

    def __str__(self):
        return f"{self.invoice_number} - {self.customer_name}"

class InvoiceItem(models.Model):
    invoice = models.ForeignKey(Invoice, on_delete=models.CASCADE, related_name="items")
    description = models.CharField(max_length=250)
    quantity = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal('1.00'))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))

    @property
    def line_total(self):
        return round(self.quantity * self.unit_price, 2)


# ==========================================
# VISITOR & SIGNUP MONITORING SYSTEM
# ==========================================
class VisitorLog(models.Model):
    ip_address = models.CharField(max_length=45)
    user_agent = models.TextField(blank=True, null=True)
    path = models.CharField(max_length=255, default='/')
    referrer = models.CharField(max_length=255, blank=True, null=True)
    device_type = models.CharField(max_length=50, default='Desktop')
    country = models.CharField(max_length=100, default='Unknown')
    session_key = models.CharField(max_length=100, blank=True, null=True)
    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True)
    visited_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.ip_address} on {self.path} at {self.visited_at}"


class RegisteredMerchant(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="merchant_profile")
    store_name = models.CharField(max_length=150)
    phone = models.CharField(max_length=30)
    business_type = models.CharField(max_length=100, default="Grocery / Supermarket")
    country = models.CharField(max_length=50, default="United Arab Emirates")
    city = models.CharField(max_length=50, default="Dubai")
    currency = models.CharField(max_length=10, default="AED")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.store_name} ({self.user.username})"
