# 🛍️ PickDeal BD — Production Telegram E-Commerce Bot

A **professional, scalable, production-ready** Telegram shopping platform built with Python 3.11 and python-telegram-bot v20+.

---

## ✨ Features

### 👤 User Features
| Feature | Details |
|---|---|
| 🛍️ Product Browsing | Categories, featured, bestsellers, pagination |
| 🔎 Smart Search | Keyword search across name, description, tags |
| 📦 Product Cards | Images, price, discount %, stock, rating, badges |
| 🛒 Shopping Cart | Add/remove, quantity ±, cart total, clear |
| ⚡ Buy Now | Direct single-product checkout |
| 📋 Checkout Flow | Area → Name → Phone → Address → Notes → Confirm |
| 💳 Payment | bKash, Nagad, Cash on Delivery |
| 📸 Payment Proof | Screenshot upload → admin verification |
| 📍 Order Tracking | 8-step status timeline with live notifications |
| 🔔 Auto Notifications | Every status change triggers customer alert |
| ❤️ Wishlist | Add/remove, view all |
| 🕐 Recently Viewed | Auto-tracked product history |
| 🎫 Coupon System | % discount or flat amount, min order, expiry |
| 👤 Profile | Order history, stats, referral code |
| 💬 Support Tickets | Create, track, receive admin replies |
| 🇧🇩 Bangla UX | Native Bangla messages throughout |

### 🛠️ Admin Features
| Feature | Details |
|---|---|
| 📊 Dashboard | Live stats: users, orders, revenue, daily breakdown |
| 📋 Order Management | Filter by status, paginated list, one-click status update |
| 🔔 Auto Customer Alert | Status change → instant Telegram notification to customer |
| 📦 Product Management | Add, edit, delete, toggle featured, update stock |
| 🖼️ Image Upload | Telegram photo upload or URL |
| 📢 Broadcast | Send message to all users |
| 🎫 Coupon Management | Create, list, deactivate |
| ⚠️ Low Stock Alert | Highlight products with stock ≤ 10 |
| 👥 Customer Management | Top customers by spending |
| 🎫 Support Tickets | View open tickets, reply, close |
| 🔍 Order Search | Search any order by ID |

---

## 📁 Project Structure

```
pickdeal_bd_v2/
├── main.py                  ← Entry point, all handlers registered
├── config/
│   ├── __init__.py
│   └── settings.py          ← All config from environment variables
├── database/
│   ├── __init__.py
│   ├── db_setup.py          ← Schema creation, seeding
│   └── queries.py           ← All SQL queries (single source of truth)
├── handlers/
│   ├── __init__.py
│   ├── start_handler.py     ← /start, menu, profile, wishlist, search
│   ├── product_handler.py   ← Browse, categories, product detail, cart
│   ├── order_handler.py     ← Full checkout ConversationHandler
│   ├── payment_handler.py   ← bKash/Nagad/COD + screenshot upload
│   ├── tracking_handler.py  ← My orders, order detail, /track
│   └── support_handler.py   ← Support ticket creation and history
├── admin/
│   ├── __init__.py
│   └── admin_handler.py     ← Full admin dashboard
├── keyboards/
│   ├── __init__.py
│   └── builder.py           ← All InlineKeyboardMarkup builders
├── utils/
│   ├── __init__.py
│   ├── formatters.py        ← All message text formatters
│   └── helpers.py           ← Validators, decorators, notify helpers
├── logs/                    ← Auto-created at runtime
├── assets/                  ← Static files (optional)
├── requirements.txt
├── Procfile                 ← Railway deployment
├── runtime.txt              ← Python 3.11
├── .env.example             ← Environment variable template
└── .gitignore
```

---

## 🗄️ Database Tables

| Table | Purpose |
|---|---|
| `users` | Customer profiles, stats, referral codes |
| `admins` | Admin roles (owner/manager/support/delivery) |
| `categories` | Product categories with emoji |
| `products` | Full product data with flags |
| `product_images` | Multiple images per product |
| `carts` + `cart_items` | Shopping cart per user |
| `orders` + `order_items` | Order records with item snapshots |
| `payments` | Payment screenshots and verification |
| `coupons` | Discount codes with rules |
| `wishlist` | User saved products |
| `recently_viewed` | Auto-tracked product views |
| `notifications` | System and order notifications |
| `support_tickets` | Customer support thread |
| `broadcasts` | Sent broadcast log |
| `analytics` | Event tracking |

---

## 🚀 Deployment

### Local Development

```bash
# 1. Clone and enter project
git clone <your-repo>
cd pickdeal_bd_v2

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate     # Linux/Mac
venv\Scripts\activate        # Windows

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment
cp .env.example .env
nano .env   # Fill in BOT_TOKEN, ADMIN_ID, etc.

# 5. Run
python main.py
```

### Railway Deployment

```bash
# 1. Push to GitHub
git add .
git commit -m "Initial deployment"
git push origin main

# 2. Connect to Railway
# Go to railway.app → New Project → Deploy from GitHub

# 3. Add Environment Variables in Railway dashboard:
#    BOT_TOKEN, ADMIN_ID, BKASH_NUMBER, NAGAD_NUMBER

# 4. Railway auto-deploys using Procfile:
#    worker: python main.py
```

### Termux (Android) Setup

```bash
pkg update && pkg upgrade
pkg install python git
pip install -r requirements.txt
cp .env.example .env
nano .env   # Add your BOT_TOKEN and ADMIN_ID
python main.py
```

---

## ⚙️ Environment Variables

| Variable | Required | Description |
|---|---|---|
| `BOT_TOKEN` | ✅ | Your Telegram bot token from @BotFather |
| `ADMIN_ID` | ✅ | Comma-separated admin Telegram user IDs |
| `BKASH_NUMBER` | ✅ | Your bKash merchant/personal number |
| `NAGAD_NUMBER` | ✅ | Your Nagad merchant/personal number |
| `COD_ENABLED` | ❌ | `true` or `false` (default: true) |
| `DB_PATH` | ❌ | SQLite file path (default: pickdeal.db) |
| `DELIVERY_INSIDE_DHAKA` | ❌ | Delivery charge inside Dhaka (default: 60) |
| `DELIVERY_OUTSIDE_DHAKA` | ❌ | Delivery charge outside Dhaka (default: 120) |
| `LOG_LEVEL` | ❌ | `INFO` or `DEBUG` (default: INFO) |

---

## 🔄 Order Status Flow

```
pending → confirmed → processing → packed → shipped → delivered
                                                     ↘ cancelled (any stage)
```

Each status change:
1. Updates database
2. Sends instant Telegram notification to customer
3. Logs analytics event

---

## 🛡️ Security Features

- ✅ Admin-only decorator on all admin handlers
- ✅ Ban check on user entry
- ✅ SQL parameterized queries (no injection)
- ✅ Order ownership verification before access
- ✅ Phone number validation (BD format)
- ✅ Stock availability check before order
- ✅ Duplicate cart item handling (quantity merge)
- ✅ Environment variables for all secrets
- ✅ WAL mode SQLite for concurrent access safety

---

## 📈 Upgrade Path: SQLite → PostgreSQL

The codebase is designed for easy migration:

1. Install `asyncpg` or `psycopg2-binary`
2. Replace `get_connection()` in `database/db_setup.py` with a PostgreSQL connection
3. Update `DB_PATH` with `DATABASE_URL` from Railway PostgreSQL
4. All queries use standard SQL compatible with PostgreSQL

---

## 📞 Default Coupon Codes (Seeded)

| Code | Discount | Min Order |
|---|---|---|
| `PICKDEAL10` | 10% off | ৳500 |
| `WELCOME50` | ৳50 flat | ৳300 |

---

## 🤝 Admin Commands

| Command | Action |
|---|---|
| `/admin` | Open admin dashboard |
| `/start` | User main menu |
| `/orders` | My orders list |
| `/cart` | View cart |
| `/track <id>` | Track specific order |
