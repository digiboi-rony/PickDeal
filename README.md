# 🛍️ PickDeal BD v3 — Professional Telegram E-Commerce Bot

> **Python 3.11 | python-telegram-bot v20+ | SQLite | Railway Ready**

---

## ✅ v3-তে কী কী সমস্যা ঠিক করা হয়েছে

### 🔴 User Side Bugs Fixed

| সমস্যা | সমাধান |
|---|---|
| ❌ Featured Products button error | ✅ Empty check যোগ করা হয়েছে, সঠিক fallback দেখানো হচ্ছে |
| ❌ My Tickets button error | ✅ `get_user_tickets` সঠিকভাবে import ও call করা হয়েছে |
| ❌ Search Products error | ✅ ConversationHandler state সঠিকভাবে flow করছে |
| ❌ Product images দেখা যায় না | ✅ `reply_photo()` দিয়ে সঠিকভাবে image পাঠানো হচ্ছে |
| ❌ Category name-এ underscore থাকলে parse ভাঙত | ✅ `catid_<id>` pattern ব্যবহার করা হয়েছে (name নয়) |
| ❌ Static delivery system | ✅ DB থেকে dynamic delivery methods লোড হচ্ছে |
| ❌ Static payment methods | ✅ DB থেকে dynamic payment methods লোড হচ্ছে |

### 🔴 Admin Side Bugs Fixed

| সমস্যা | সমাধান |
|---|---|
| ❌ Open Tickets button error | ✅ `adm_tickets_<page>` pattern সঠিকভাবে কাজ করছে |
| ❌ Category CRUD ছিল না | ✅ সম্পূর্ণ Category Add/Edit/Delete/Toggle/Feature যোগ হয়েছে |
| ❌ Delivery system ছিল না | ✅ Delivery Method CRUD (Add/Edit/Toggle/Delete) যোগ হয়েছে |
| ❌ Payment management ছিল না | ✅ Payment Method Add/Edit/Toggle যোগ হয়েছে |
| ❌ Coupon edit/delete ছিল না | ✅ সম্পূর্ণ Coupon CRUD (Edit/Delete/Toggle/Expiry) যোগ হয়েছে |
| ❌ Single user message ছিল না | ✅ "একজনকে মেসেজ" ফিচার যোগ হয়েছে |
| ❌ Ticket reopen ছিল না | ✅ Ticket Reopen ফিচার যোগ হয়েছে |
| ❌ Admin order note ছিল না | ✅ Order-এ admin note যোগ করার ফিচার এসেছে |
| ❌ `notify_admins(update, ...)` — ভুল argument | ✅ `notify_admins(context, ...)` — সঠিক করা হয়েছে |
| ❌ `admview_\d+` ও `admview_prod_\d+` conflict | ✅ `adm_order_\d+` ও `admprodview_\d+` আলাদা pattern |

---

## 📁 Project Structure

```
pickdeal_v3/
├── main.py                    ← Entry point, সব handler registered
├── config/
│   └── settings.py            ← Environment variables থেকে সব config
├── database/
│   ├── db_setup.py            ← 18-table schema, WAL mode, seed data
│   └── queries.py             ← সব SQL এক জায়গায়
├── handlers/
│   ├── start_handler.py       ← /start, menu, profile, wishlist, search
│   ├── product_handler.py     ← Categories (ID-based), products, cart
│   ├── order_handler.py       ← Dynamic delivery checkout flow
│   ├── payment_handler.py     ← Dynamic payment methods + screenshot
│   └── tracking_handler.py   ← Orders, tracking, support tickets
├── admin/
│   └── admin_handler.py       ← Full admin dashboard (15+ features)
├── keyboards/
│   └── builder.py             ← সব InlineKeyboard এক মডিউলে
├── utils/
│   ├── helpers.py             ← Decorators, validators, notify helpers
│   └── formatters.py          ← সব message text formatting
├── logs/                      ← Auto-created
├── assets/                    ← Static files
├── requirements.txt
├── Procfile                   ← Railway: worker: python main.py
├── runtime.txt                ← python-3.11.7
└── .env.example               ← Environment template
```

---

## 🗄️ Database Tables (18টি)

| Table | কাজ |
|---|---|
| `users` | Customer profiles, stats, referral |
| `admins` | Admin roles |
| `categories` | Dynamic categories with emoji, featured flag |
| `products` | Full product data (advance_pct, cod_available) |
| `product_images` | Multiple images per product |
| `delivery_methods` | **NEW** — Dynamic delivery zones & charges |
| `payment_methods` | **NEW** — Dynamic payment methods from DB |
| `carts` + `cart_items` | Shopping cart |
| `orders` + `order_items` | Orders with delivery_method snapshot |
| `payments` | Screenshot verification queue |
| `coupons` | Percent/flat discount, expiry, edit/delete |
| `wishlist` | User saved products |
| `recently_viewed` | Auto-tracked |
| `support_tickets` | Customer support with reopen |
| `notifications` | System notifications |
| `broadcasts` | Broadcast log |
| `analytics` | Event tracking |

---

## 🚀 Deployment

### Local / Termux

```bash
# 1. Extract
unzip pickdeal_bd_v3.zip
cd pickdeal_v3

# 2. Install
pip install -r requirements.txt

# 3. Configure
cp .env.example .env
nano .env   # BOT_TOKEN ও ADMIN_ID দিন

# 4. Run
python main.py
```

### Railway

```bash
# 1. GitHub-এ push করুন
git init
git add .
git commit -m "PickDeal BD v3"
git remote add origin <your-repo>
git push -u origin main

# 2. Railway dashboard → New Project → GitHub থেকে deploy
# 3. Environment Variables সেট করুন:
#    BOT_TOKEN, ADMIN_ID, BKASH_NUMBER, NAGAD_NUMBER
# 4. Railway auto-deploys via Procfile: worker: python main.py
```

---

## ⚙️ Environment Variables

| Variable | Required | Default | বিবরণ |
|---|---|---|---|
| `BOT_TOKEN` | ✅ | — | @BotFather থেকে নিন |
| `ADMIN_ID` | ✅ | — | Telegram User ID (একাধিক হলে কমা দিয়ে) |
| `BKASH_NUMBER` | ✅ | — | bKash নম্বর |
| `NAGAD_NUMBER` | ✅ | — | Nagad নম্বর |
| `ROCKET_NUMBER` | ❌ | — | Rocket নম্বর |
| `COD_ENABLED` | ❌ | true | Cash on Delivery চালু/বন্ধ |
| `DB_PATH` | ❌ | pickdeal.db | Database file path |
| `DELIVERY_INSIDE_DHAKA` | ❌ | 60 | Default ভেতরে চার্জ |
| `DELIVERY_OUTSIDE_DHAKA` | ❌ | 120 | Default বাইরে চার্জ |
| `LOG_LEVEL` | ❌ | INFO | INFO বা DEBUG |

---

## 🔄 Order Status Flow

```
pending → confirmed → processing → packed → shipped → out_for_delivery → delivered
                                                                        ↘ cancelled → refunded
```

প্রতিটি status পরিবর্তনে Customer-কে **স্বয়ংক্রিয় Telegram notification** যায়।

---

## 🎫 Default Coupon Codes (Seeded)

| Code | ধরন | ডিসকাউন্ট | ন্যূনতম অর্ডার |
|---|---|---|---|
| `PICKDEAL10` | % | 10% | ৳500 |
| `WELCOME50` | flat | ৳50 | ৳300 |
| `EIDMUBARAK` | % | 15% | ৳800 |

---

## 📞 Admin Commands

| Command | কাজ |
|---|---|
| `/admin` | Admin dashboard |
| `/start` | User main menu |
| `/orders` | My orders |
| `/cart` | Cart দেখুন |
| `/track <id>` | Order track করুন |

---

## 🔑 Key Architecture Decisions

1. **Category ID-based routing** — `catid_<id>` pattern, name string নয়। Category নামে `_` থাকলে parse ভাঙে না।
2. **Dynamic delivery/payment** — DB থেকে লোড হয়। Admin যেকোনো সময় পরিবর্তন করতে পারেন।
3. **ConversationHandler FIRST** — `main.py`-তে Conversation handlers সবার আগে register হয়েছে।
4. **Single SQL layer** — `database/queries.py`-তে সব SQL। Handler-এ কোনো raw SQL নেই।
5. **`notify_admins(context, ...)`** — v2-এর bug ছিল `update` পাঠানো হতো। v3-তে সঠিক।
