# 🛡️ NDA Shield v3 — Cybersecurity NDA Management System

> **Apple-inspired Liquid Glass UI · Email Notifications · Secure One-Time Signing Links**

## ✨ What's New

### 📧 Email Notification System
- **Assignment emails** — Signer receives a beautiful HTML email with secure signing link
- **Reminder emails** — Follow-up emails for pending signatures
- **Confirmation emails** — Signer receives proof of signing with confirmation ID
- **Admin notifications** — Assigner gets notified on sign/decline
- **All emails** — Professional HTML templates with Apple-inspired design

### 🔐 Secure One-Time Links
- Each signing link is unique per person + NDA assignment
- **Link expires after signing** — cannot be reused
- **Link expires by time** — configurable hours (default 72h)
- **Token-based access** — no login required for signers
- **Revoked links** — admin can revoke anytime
- **Tamper-proof** — SHA-256 signature hashing

### 🍎 Apple Liquid Glass UI
- Frosted glass effects (backdrop-filter blur)
- Smooth cubic-bezier animations
- SF Pro / Inter typography with -apple-system fallback
- Subtle shadows and translucency
- Rounded corners (12-24px)
- Light, airy color palette with depth

---

## 🚀 Quick Start

### Backend (Terminal 1)
```bash
cd backend
python -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python manage.py makemigrations && python manage.py migrate
python manage.py seed_data
python manage.py runserver 8000
```

### Frontend (Terminal 2)
```bash
cd frontend
npm install && npm run dev
```

Open **http://localhost:5173** → Login: `admin@cybersec.com` / `admin123`

---

## 📧 Email Configuration

**Development** (default) — emails print to terminal:
```
EMAIL_BACKEND=django.core.mail.backends.console.EmailBackend
```

**Production** — real SMTP (e.g., Gmail):
```env
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password
EMAIL_USE_TLS=True
DEFAULT_FROM_EMAIL=nda@yourcompany.com
```

### Email Events
| Event | Recipient | Trigger |
|---|---|---|
| 📋 NDA Assigned | Signer | Admin assigns NDA |
| ⏰ Reminder | Signer | Admin clicks Remind |
| ✅ Signed Confirmation | Signer | After signing |
| ✅ Signed Notification | Admin | After signing |
| ❌ Declined Notification | Admin | Signer declines |

---

## 🔐 Demo Credentials

| Email | Password | Role |
|---|---|---|
| admin@cybersec.com | admin123 | Super Admin |
| legal@cybersec.com | legal123 | Legal |
| hr@cybersec.com | hr123 | HR |
| manager@cybersec.com | manager123 | Manager |
| employee@cybersec.com | employee123 | Employee |

---

## 📡 API Endpoints (30+ endpoints)

### Auth & Users
- `POST /api/auth/login/` — Login
- `POST /api/auth/refresh/` — Refresh token
- `GET /api/auth/dashboard/` — Dashboard stats
- `GET/POST /api/auth/users/` — User management

### NDAs
- `GET/POST /api/ndas/` — Template CRUD
- `POST /api/ndas/{id}/new-version/` — Upload DOCX version
- `GET /api/ndas/categories/` — Category breakdown

### People
- `GET/POST /api/people/` — Person CRUD
- `POST /api/people/bulk-create/` — Bulk import

### Assignments (with email)
- `POST /api/assignments/assign-single/` — Assign + send email
- `POST /api/assignments/assign-group/` — Group assign + send N emails
- `POST /api/assignments/{id}/remind/` — Send reminder email
- `POST /api/assignments/{id}/revoke/` — Revoke link

### Signing Portal (public, no auth)
- `GET /api/documents/portal/{token}/` — View NDA
- `POST /api/documents/portal/{token}/sign/` — Sign + send confirmation emails
- `POST /api/documents/portal/{token}/decline/` — Decline + notify admin

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Backend | Django 5.1.4, DRF 3.15.2, OAuth2 |
| Frontend | React 18, React Router 6, Vite 6 |
| Auth | OAuth2 (ROPC), token-based signing portal |
| Email | Django SMTP with HTML templates |
| Database | SQLite (dev) / PostgreSQL (prod) |
| Security | SHA-256 hashing, one-time tokens, RBAC |
