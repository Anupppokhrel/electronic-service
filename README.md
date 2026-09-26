# ❄️ Multi-Brand AC & Appliance Service Workshop Management Portal

A modern, fast, and connected web application designed for a multi-brand appliance servicing and repair workshop in **Damak, Jhapa, Nepal**. Built to replace manual Excel spreadsheet workflows with seamless entity connectivity, strict Role-Based Access Control (RBAC), and localized operational features.

---

## 🌟 Key Features

### 1. 🛠️ 4-Appliance Multi-Brand Support
Tracks repairs, installations, and maintenance across all four core appliances:
- **Air Conditioners (AC)**: Split, Window, Cassette, Tower, Multi-split
- **Refrigerators (Ref)**: Single Door, Double Door Frost-free, Deep Freezers
- **Washing Machines (WM)**: Front Load, Top Load Fully-Automatic, Semi-Automatic
- **Air Coolers**: Desert Coolers, Room Coolers

### 2. 📋 Real-World Job Classifications
Directly mapped to traditional workshop operations:
- **General Service (`SVC only`)**: Routine servicing, chemical wash, filter maintenance
- **Installation**: Mounting, bracket placement, and piping
- **Uninstallation**: Dismantling and pump-down before relocation
- **Repair & Replacement**: Diagnosing faults, PCB repair, capacitor/relay/motor replacement
- **Demo / Orientation**: Demonstration and customer walk-through
- **Repeat Complaint / Warranty Rework (`Ree complain`)**: Priority tracking for callbacks

### 3. 🛡️ Dealer Warranty (`WTY`) Claims Hub
- **Rs. 0 Customer Invoicing**: Warranty jobs automatically zero out customer billing.
- **Showroom Claims Ledger**: Track pending, submitted, and settled claims directly owed by brand authorized dealers (e.g. CG Electronics, Samsung Plaza, LG Damak).
- **Direct Dispatch**: 1-click warranty job dispatch linked to authorized dealers.

### 4. 📒 Udharo Khata (Credit & Due Management)
- Dedicated aging ledger (`/billing/due/`) tracking all unpaid customer balances.
- Displays customer name, phone, ward location, job voucher, and days outstanding.
- **1-Click Settlement Modal**: Rapid payment clearing with receipt recording and balance sync.

### 5. 🇳🇵 Dual Bikram Sambat (BS) & Gregorian (AD) Calendar
- All job vouchers, invoices, customer records, and dashboard metrics display dual dates:
  > **24 Sep 2026 (8 Ashwin 2083 BS)**
- Localized address auto-fill for Damak wards, Urlabari, Pathri, Gauradaha, Kirat Chowk, and Kankai.

### 6. 🔒 Strict Role-Based Access Control (RBAC)
- **Workshop Owner / Admin**: Complete command over financial reports, Udharo Khata, warranty claims, customer database, staff directory, inventory pricing, and dispatch.
- **Technician Field Hub (`/services/tech-hub/`)**:
  - Independent secure credentials for each staff member.
  - Technicians can **ONLY** view their assigned jobs (cross-technician privacy enforced).
  - Can update work status (`Start Work`, `Wait for Parts`, `Mark Completed`), log work notes, and record spare parts used.
  - Can check inventory availability (read-only; purchase costs and restock controls hidden).
  - All administrative, financial, billing, and settings pages are strictly blocked.

### 7. 📱 Mobile Field Hub & Static Payment QRs
- Technicians can present static payment QRs (**eSewa**, **Fonepay**, **Bank Transfer**) directly to customers on mobile devices for instant on-site payment.

---

## 🏗️ Technology Stack

- **Backend**: Python 3, Django 6.0
- **Frontend**: Django Templates, Tailwind CSS, Lucide Icons
- **Database**: SQLite3
- **Reports**: OpenPyXL (Excel Export)
- **Architecture**: Modular Django apps (`core`, `accounts`, `customers`, `services`, `inventory`, `billing`, `reports`)

---

## 🚀 Quick Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/Anupppokhrel/Alidai_scratch.git
cd Alidai_scratch
```

### 2. Create and activate a virtual environment
```bash
python -m venv venv

# Windows (Command Prompt / PowerShell):
venv\Scripts\activate

# Linux / macOS:
source venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run database migrations
```bash
python manage.py migrate
```

### 5. Load pre-seeded workshop data
```bash
python manage.py loaddata seed_data.json
```

### 6. Start the local development server
```bash
python manage.py runserver 0.0.0.0:8000
```
Open [http://localhost:8000](http://localhost:8000) in your browser.

---

## 👥 Default User Accounts

| Role | Username | Password | Default Landing Page |
| :--- | :--- | :--- | :--- |
| **Owner / Admin** | `admin` | `admin123` | `/` (Workshop Dashboard) |
| **Senior Technician** | `bikash` | `tech123` | `/services/tech-hub/` (Mobile Field Hub) |
| **Technician** | `suman` | `tech123` | `/services/tech-hub/` (Mobile Field Hub) |
| **Technician** | `raj` | `tech123` | `/services/tech-hub/` (Mobile Field Hub) |
| **Technician** | `anup` | `tech123` | `/services/tech-hub/` (Mobile Field Hub) |

---

## 🧪 Running Automated Tests

To run the full suite of unit and security tests:

```bash
# Run Django unit tests
python manage.py test

# Run Role-Based Access Control (RBAC) security tests
python scratch/test_role_security.py

# Run Full Entity Bidirectional Connectivity tests
python scratch/test_connectivity_features.py

# Run Spreadsheet-Matched Features test
python scratch/test_spreadsheet_features.py
```

---

## 📄 License
Internal proprietary software for Workshop Operations. All rights reserved.
