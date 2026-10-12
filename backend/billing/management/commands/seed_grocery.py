import datetime
from decimal import Decimal
from django.core.management.base import BaseCommand
from django.contrib.auth.models import User
from django.utils import timezone
from billing.models import (
    Product, Supplier, PurchaseBill, ExpenseCategory, Expense,
    CustomerKhata, UserProfile, CashRegisterSession
)

GROCERY_CATALOG = [
    # سبزی و پھل
    {"name": "Onion", "barcode": "6291001000018", "category": "Fresh Produce / سبزی و پھل", "unit_price": Decimal("3.50"), "cost_price": Decimal("2.20"), "current_stock": 100, "min_alert_stock": 15, "expiry_date": timezone.now().date() + datetime.timedelta(days=14), "batch_number": "B-ON-01"},
    {"name": "Tomato", "barcode": "6291001000025", "category": "Fresh Produce / سبزی و پھل", "unit_price": Decimal("4.00"), "cost_price": Decimal("2.50"), "current_stock": 80, "min_alert_stock": 15, "expiry_date": timezone.now().date() + datetime.timedelta(days=4), "batch_number": "B-TM-01"},
    {"name": "Potato", "barcode": "6291001000032", "category": "Fresh Produce / سبزی و پھل", "unit_price": Decimal("2.50"), "cost_price": Decimal("1.60"), "current_stock": 120, "min_alert_stock": 20, "expiry_date": timezone.now().date() + datetime.timedelta(days=25), "batch_number": "B-PT-01"},
    {"name": "Garlic", "barcode": "6291001000049", "category": "Fresh Produce / سبزی و پھل", "unit_price": Decimal("6.00"), "cost_price": Decimal("3.80"), "current_stock": 50, "min_alert_stock": 10, "expiry_date": timezone.now().date() + datetime.timedelta(days=40), "batch_number": "B-GL-01"},
    {"name": "Red Apples", "barcode": "6291001000056", "category": "Fresh Produce / سبزی و پھل", "unit_price": Decimal("6.50"), "cost_price": Decimal("4.20"), "current_stock": 45, "min_alert_stock": 10, "expiry_date": timezone.now().date() + datetime.timedelta(days=10), "batch_number": "B-AP-01"},
    {"name": "Bananas", "barcode": "6291001000063", "category": "Fresh Produce / سبزی و پھل", "unit_price": Decimal("4.50"), "cost_price": Decimal("2.90"), "current_stock": 60, "min_alert_stock": 12, "expiry_date": timezone.now().date() + datetime.timedelta(days=3), "batch_number": "B-BN-01"},
    {"name": "Coriander/Mint", "barcode": "6291001000070", "category": "Fresh Produce / سبزی و پھل", "unit_price": Decimal("1.50"), "cost_price": Decimal("0.80"), "current_stock": 40, "min_alert_stock": 10, "expiry_date": timezone.now().date() + datetime.timedelta(days=2), "batch_number": "B-CM-01"},

    # ڈیری و بیکری
    {"name": "Fresh Milk", "barcode": "6291002000017", "category": "Dairy & Bakery / ڈیری و بیکری", "unit_price": Decimal("6.00"), "cost_price": Decimal("4.50"), "current_stock": 50, "min_alert_stock": 10, "expiry_date": timezone.now().date() + datetime.timedelta(days=5), "batch_number": "D-MK-01"},
    {"name": "Bread", "barcode": "6291002000024", "category": "Dairy & Bakery / ڈیری و بیکری", "unit_price": Decimal("4.50"), "cost_price": Decimal("3.20"), "current_stock": 35, "min_alert_stock": 8, "expiry_date": timezone.now().date() + datetime.timedelta(days=3), "batch_number": "D-BR-01"},
    {"name": "Eggs", "barcode": "6291002000031", "category": "Dairy & Bakery / ڈیری و بیکری", "unit_price": Decimal("5.00"), "cost_price": Decimal("3.60"), "current_stock": 40, "min_alert_stock": 10, "expiry_date": timezone.now().date() + datetime.timedelta(days=15), "batch_number": "D-EG-01"},
    {"name": "Egg Tray", "barcode": "6291002000048", "category": "Dairy & Bakery / ڈیری و بیکری", "unit_price": Decimal("22.00"), "cost_price": Decimal("17.00"), "current_stock": 25, "min_alert_stock": 5, "expiry_date": timezone.now().date() + datetime.timedelta(days=20), "batch_number": "D-ET-01"},
    {"name": "Yogurt", "barcode": "6291002000055", "category": "Dairy & Bakery / ڈیری و بیکری", "unit_price": Decimal("3.00"), "cost_price": Decimal("2.10"), "current_stock": 45, "min_alert_stock": 10, "expiry_date": timezone.now().date() + datetime.timedelta(days=6), "batch_number": "D-YG-01"},

    # اناج، دالیں اور مصالحہ جات
    {"name": "White Sugar", "barcode": "6291003000016", "category": "Grains & Spices / اناج و مصالحہ جات", "unit_price": Decimal("4.00"), "cost_price": Decimal("2.90"), "current_stock": 90, "min_alert_stock": 20, "expiry_date": timezone.now().date() + datetime.timedelta(days=360), "batch_number": "G-SG-01"},
    {"name": "Basmati Rice", "barcode": "6291003000023", "category": "Grains & Spices / اناج و مصالحہ جات", "unit_price": Decimal("7.50"), "cost_price": Decimal("5.30"), "current_stock": 85, "min_alert_stock": 15, "expiry_date": timezone.now().date() + datetime.timedelta(days=300), "batch_number": "G-RC-01"},
    {"name": "Cooking Oil", "barcode": "6291003000030", "category": "Grains & Spices / اناج و مصالحہ جات", "unit_price": Decimal("14.00"), "cost_price": Decimal("10.50"), "current_stock": 40, "min_alert_stock": 8, "expiry_date": timezone.now().date() + datetime.timedelta(days=240), "batch_number": "G-OL-01"},
    {"name": "Pure Ghee", "barcode": "6291003000047", "category": "Grains & Spices / اناج و مصالحہ جات", "unit_price": Decimal("15.00"), "cost_price": Decimal("11.50"), "current_stock": 30, "min_alert_stock": 6, "expiry_date": timezone.now().date() + datetime.timedelta(days=280), "batch_number": "G-GH-01"},
    {"name": "Daal Mash", "barcode": "6291003000054", "category": "Grains & Spices / اناج و مصالحہ جات", "unit_price": Decimal("11.00"), "cost_price": Decimal("8.00"), "current_stock": 50, "min_alert_stock": 10, "expiry_date": timezone.now().date() + datetime.timedelta(days=180), "batch_number": "G-DM-01"},
    {"name": "Daal Chana", "barcode": "6291003000061", "category": "Grains & Spices / اناج و مصالحہ جات", "unit_price": Decimal("9.50"), "cost_price": Decimal("7.00"), "current_stock": 50, "min_alert_stock": 10, "expiry_date": timezone.now().date() + datetime.timedelta(days=180), "batch_number": "G-DC-01"},
    {"name": "Tea Dust", "barcode": "6291003000078", "category": "Beverages & Tea / چائے و مشروبات", "unit_price": Decimal("12.00"), "cost_price": Decimal("8.80"), "current_stock": 60, "min_alert_stock": 12, "expiry_date": timezone.now().date() + datetime.timedelta(days=360), "batch_number": "B-TD-01"},

    # مشروبات و اسنیکس
    {"name": "Water Bottle", "barcode": "6291004000015", "category": "Beverages & Tea / چائے و مشروبات", "unit_price": Decimal("1.50"), "cost_price": Decimal("0.85"), "current_stock": 150, "min_alert_stock": 30, "expiry_date": timezone.now().date() + datetime.timedelta(days=300), "batch_number": "B-WB-01"},
    {"name": "Soft Drink", "barcode": "6291004000022", "category": "Beverages & Tea / چائے و مشروبات", "unit_price": Decimal("2.50"), "cost_price": Decimal("1.70"), "current_stock": 100, "min_alert_stock": 20, "expiry_date": timezone.now().date() + datetime.timedelta(days=200), "batch_number": "B-SD-01"},
    {"name": "Biscuits", "barcode": "6291004000039", "category": "Snacks / بسکٹ و اسنیکس", "unit_price": Decimal("2.00"), "cost_price": Decimal("1.30"), "current_stock": 80, "min_alert_stock": 15, "expiry_date": timezone.now().date() + datetime.timedelta(days=120), "batch_number": "S-BS-01"},

    # گوشت و پروٹین
    {"name": "Fresh Chicken", "barcode": "6291005000014", "category": "Meat & Poultry / گوشت و چکن", "unit_price": Decimal("15.00"), "cost_price": Decimal("11.50"), "current_stock": 30, "min_alert_stock": 5, "expiry_date": timezone.now().date() + datetime.timedelta(days=2), "batch_number": "M-CH-01"},
    {"name": "Fresh Fish", "barcode": "6291005000021", "category": "Meat & Poultry / گوشت و چکن", "unit_price": Decimal("22.00"), "cost_price": Decimal("16.50"), "current_stock": 20, "min_alert_stock": 4, "expiry_date": timezone.now().date() + datetime.timedelta(days=2), "batch_number": "M-FS-01"},

    # صابن و گھریلو اشیاء
    {"name": "Bath Soap", "barcode": "6291006000013", "category": "Household / گھریلو سامان", "unit_price": Decimal("3.50"), "cost_price": Decimal("2.40"), "current_stock": 70, "min_alert_stock": 15, "expiry_date": timezone.now().date() + datetime.timedelta(days=500), "batch_number": "H-BS-01"},
    {"name": "Detergent", "barcode": "6291006000020", "category": "Household / گھریلو سامان", "unit_price": Decimal("8.50"), "cost_price": Decimal("6.00"), "current_stock": 40, "min_alert_stock": 10, "expiry_date": timezone.now().date() + datetime.timedelta(days=500), "batch_number": "H-DT-01"},
    {"name": "Shampoo", "barcode": "6291006000037", "category": "Household / گھریلو سامان", "unit_price": Decimal("16.00"), "cost_price": Decimal("11.00"), "current_stock": 30, "min_alert_stock": 6, "expiry_date": timezone.now().date() + datetime.timedelta(days=400), "batch_number": "H-SH-01"},
    {"name": "Baby Diapers", "barcode": "6291006000044", "category": "Baby Care / بچوں کا سامان", "unit_price": Decimal("35.00"), "cost_price": Decimal("26.00"), "current_stock": 25, "min_alert_stock": 5, "expiry_date": timezone.now().date() + datetime.timedelta(days=600), "batch_number": "H-DP-01"},
]

EXPENSE_CATEGORIES = [
    ("Shop Rent / دکان کا کرایہ", "Monthly premises rental fee"),
    ("DEWA / بجلی و پانی بل", "Utility bills (electricity, water, municipal fees)"),
    ("Staff Salaries / عملے کی تنخواہیں", "Monthly cashier & worker wages"),
    ("Tea & Refreshment / چائے اور ضیافت", "Daily tea, coffee, and refreshments"),
    ("Packaging Bags / شاپنگ بیگز اور سامان", "Plastic bags, thermal receipt paper, boxes"),
    ("Shop Maintenance / دکان مرمت", "AC repair, refrigeration service, lighting"),
    ("Miscellaneous / متفرق اخراجات", "Other minor daily cash expenses"),
]

SUPPLIERS = [
    {
        "name": "Al Rawabi Dairy Co.",
        "company_name": "Al Rawabi Juice & Dairy LLC",
        "phone": "+971501239871",
        "email": "orders@alrawabi.ae",
        "address": "Al Khawaneej, Dubai",
        "outstanding_payable": Decimal("450.00")
    },
    {
        "name": "Fresh Harvest Farms",
        "company_name": "Fresh Harvest Fruits & Veg Trading",
        "phone": "+971556784321",
        "email": "sales@freshharvest.ae",
        "address": "Central Fruit & Veg Market, Al Aweer, Dubai",
        "outstanding_payable": Decimal("620.00")
    },
    {
        "name": "National FMCG Dist.",
        "company_name": "National Foodstuff Distribution LLC",
        "phone": "+971529871144",
        "email": "supply@nationalfmcg.com",
        "address": "Ras Al Khor Industrial 2, Dubai",
        "outstanding_payable": Decimal("1280.00")
    }
]

USERS = [
    {"username": "admin", "role": "admin", "pin": "1122", "phone": "+971501112233", "is_staff": True, "is_superuser": True},
    {"username": "manager", "role": "manager", "pin": "2233", "phone": "+971504445566", "is_staff": True, "is_superuser": False},
    {"username": "cashier", "role": "cashier", "pin": "1234", "phone": "+971507778899", "is_staff": False, "is_superuser": False},
]

class Command(BaseCommand):
    help = "Seed complete professional POS system data for all 7 modules"

    def handle(self, *args, **kwargs):
        self.stdout.write("Seeding POS modules data...")

        # 1. Seed Products with Cost Prices & Expiry
        prod_count = 0
        for item in GROCERY_CATALOG:
            prod, _ = Product.objects.update_or_create(
                name__iexact=item["name"],
                defaults=item
            )
            prod_count += 1
        self.stdout.write(self.style.SUCCESS(f"[OK] {prod_count} Products updated with Cost Price, Categories, and Expiry Dates."))

        # 2. Seed Expense Categories
        cat_count = 0
        for name, desc in EXPENSE_CATEGORIES:
            ExpenseCategory.objects.get_or_create(name=name, defaults={"description": desc})
            cat_count += 1
        self.stdout.write(self.style.SUCCESS(f"[OK] {cat_count} Expense Categories created."))

        # 3. Seed Sample Expenses
        rent_cat = ExpenseCategory.objects.first()
        if not Expense.objects.exists():
            Expense.objects.create(category=rent_cat, title="Morning Shop Supplies & Ice", amount=Decimal("35.00"), payment_mode="Cash", notes="Fresh ice blocks for poultry display")
            Expense.objects.create(category=rent_cat, title="Thermal Receipt Rolls (Box of 20)", amount=Decimal("45.00"), payment_mode="Cash", notes="POS printer rolls")

        # 4. Seed Suppliers
        sup_count = 0
        for s in SUPPLIERS:
            Supplier.objects.update_or_create(name=s["name"], defaults=s)
            sup_count += 1
        self.stdout.write(self.style.SUCCESS(f"[OK] {sup_count} Suppliers created."))

        # 5. Seed Users & Permissions
        for u in USERS:
            user_obj, created = User.objects.get_or_create(username=u["username"])
            if created or not user_obj.has_usable_password():
                user_obj.set_password(f"{u['username']}123")
                user_obj.is_staff = u["is_staff"]
                user_obj.is_superuser = u["is_superuser"]
                user_obj.save()
            
            UserProfile.objects.update_or_create(
                user=user_obj,
                defaults={"role": u["role"], "pin_code": u["pin"], "phone": u["phone"]}
            )
        self.stdout.write(self.style.SUCCESS("[OK] Staff roles created: admin (PIN 1122), manager (PIN 2233), cashier (PIN 1234)."))

        # 6. Ensure Cash Register Drawer is active
        if not CashRegisterSession.objects.filter(status='open').exists():
            CashRegisterSession.objects.create(
                cashier_name="cashier",
                opening_cash=Decimal("200.00"),
                expected_cash=Decimal("200.00"),
                status='open',
                notes="Morning shift started with 200 AED float"
            )
            self.stdout.write(self.style.SUCCESS("[OK] Cash Drawer opened with 200 AED morning float."))

        self.stdout.write(self.style.SUCCESS("All 7 POS Modules successfully initialized!"))
