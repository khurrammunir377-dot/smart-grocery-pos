# Smart Grocery POS — 7-in-1 Retail & Digital Billing System

An intelligent, high-speed Point of Sale (POS) system designed for retail groceries, supermarkets, and convenience stores with automated background WhatsApp digital receipts and multi-currency support.

---

## 🚀 Key Modules & Features

1. **Sales & Fast Checkout (کاؤنٹر فروخت)**
   - Hardware barcode scanner integration.
   - 28 dual-language fast-touch 3D catalog tiles.
   - Natural language free-text bulk input parser (e.g. `2 Milk 6, 1 Bread 4.5`).
   - Multiple payment methods: Cash, Card, Digital Khata Credit, and Split payments.
   - Customer return & refund processing with automated inventory re-stocking.

2. **Real-time Inventory & Expiry Tracking (اسٹاک و ایکسپائری)**
   - Automated real-time stock deduction upon sale.
   - Low stock threshold alerts.
   - Expiry date tracking with warning badges (Expired, Critical ≤ 7 days, Warning ≤ 30 days).
   - Stock adjustments (spoilage, damage write-offs, physical inventory audits).

3. **Purchases & Supplier Management (سپلائر و خریداری)**
   - Supplier vendor directory and payment balance ledger.
   - Purchase bills entry (Stock In) with automatic quantity and cost updates.
   - Cost price margins and accounts payable tracking.

4. **Customer Digital Khata & Credit Ledger (گاہک کھاتہ)**
   - Digital credit ledger for regular neighborhood customers.
   - Credit limit protection to mitigate unpaid debt risk.
   - Automated debt settlement receipts sent directly to customer WhatsApp.
   - Customer loyalty reward points.

5. **Cash Drawer Sessions & Expense Vouchers (کیش دراز و اخراجات)**
   - Shift drawer opening float and end-of-shift closing reconciliations.
   - Daily store operational expense vouchers (Rent, Utilities/DEWA, Salaries, Tea, Maintenance).
   - Cash discrepancy reporting (Shortage / Excess audits).

6. **Reports & Profit/Loss Analytics (کاروباری رپورٹس)**
   - Gross revenue, cash vs. credit breakdowns, and net margins.
   - Top 10 Best-Selling products ranking.
   - Accurate Net Profit calculation (Revenue − COGS − Operational Expenses).
   - Cashier and staff sales metrics.

7. **User Roles & PIN Security (صارفین اور اختیارات)**
   - Multi-role access control: Owner/Admin, Store Manager, and Cashier.
   - Fast 4-digit PIN authentication (`1122`, `2233`, `1234`).
   - Role-based restrictions (cashier cannot delete products or view net profits).

8. **Silent WhatsApp Delivery Gateway**
   - Headless background gateway powered by Baileys.
   - Sends digital receipt links directly to customer WhatsApp numbers upon checkout.

---

## 🛠️ Tech Stack

- **Backend:** Python 3, Django 5
- **Database:** SQLite (Development) / PostgreSQL-ready
- **Frontend:** Vanilla HTML5, CSS3, JavaScript (Fast responsive 3D UI, zero bloated dependencies)
- **WhatsApp Gateway:** Node.js, Express, Baileys WebSocket API
- **Mobile Client:** Flutter / Dart

---

## 💻 Quick Start & Setup

### 1. Backend (Django)
```bash
# Navigate to backend directory
cd backend

# Install dependencies (if not already installed)
pip install django requests pillow

# Run migrations
python manage.py migrate

# Seed initial grocery catalog & sample data
python manage.py seed_grocery

# Start server
python manage.py runserver 8000
```
Open **`http://127.0.0.1:8000/`** in your browser to access the POS Counter directly, or **`http://127.0.0.1:8000/landing/`** for the SaaS overview.

### 2. WhatsApp Gateway (Optional for live WhatsApp messaging)
```bash
cd wa_gateway
npm install
node server.js
```

---

## 📄 License
MIT License. Free to use, adapt, and scale for retail groceries and supermarkets.
