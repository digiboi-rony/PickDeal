# 🛍️ PickDeal BD — Telegram E-Commerce Bot

A fully-featured **Telegram shopping bot** built with Python. Customers can browse products, place orders, submit payments, and track delivery — all inside Telegram!

---

## 📦 Features

### Customer Features
- `/start` — Welcome screen with interactive menu
- Browse products by category
- View product details with price and description
- Multi-step order form (Name → Phone → Address → Quantity)
- bKash / Nagad payment instructions
- Upload payment screenshot
- Track order status
- View order history

### Admin Features
- Instant notification for new orders
- Receive payment screenshots
- Update order status (Confirm → Processing → Shipped → Delivered)
- View all orders with pagination
- Filter orders by status
- Search order by ID
- Broadcast message to all users

---

## 🗂️ Project Structure

```
pickdeal_bd/
├── main.py                  ← Bot entry point
├── handlers/
│   ├── start_handler.py     ← /start, main menu
│   ├── product_handler.py   ← Browse categories & products
│   ├── order_handler.py     ← Order form (ConversationHandler)
│   ├── payment_handler.py   ← Payment instructions & screenshots
│   ├── tracking_handler.py  ← Order tracking & My Orders
│   ├── support_handler.py   ← Customer support
│   └── admin_handler.py     ← Admin panel
├── database/
│   ├── db_setup.py          ← SQLite table creation & seeding
│   └── queries.py           ← All database functions
├── utils/
│   └── helpers.py           ← Shared utilities & constants
├── requirements.txt
├── Procfile                 ← For Railway deployment
├── .env.example             ← Environment variable template
├── .gitignore
└── README.md
```

---

## ⚡ Quick Start (Local)

### Step 1: Prerequisites
- Python 3.11+
- pip

### Step 2: Clone or download the project
```bash
git clone https://github.com/yourusername/pickdeal-bd.git
cd pickdeal-bd
```

### Step 3: Install dependencies
```bash
pip install -r requirements.txt
```

### Step 4: Set up environment variables
```bash
cp .env.example .env
```
Now open `.env` and fill in your values:
```
BOT_TOKEN=your_bot_token_here
ADMIN_ID=your_telegram_user_id
BKASH_NUMBER=01XXXXXXXXX
NAGAD_NUMBER=01XXXXXXXXX
```

#### How to get BOT_TOKEN:
1. Open Telegram and search for **@BotFather**
2. Send `/newbot`
3. Follow the instructions
4. Copy the token

#### How to get your ADMIN_ID:
1. Open Telegram and search for **@userinfobot**
2. Send `/start`
3. It will show your numeric user ID

### Step 5: Run the bot
```bash
python main.py
```

---

## 📱 Termux (Android) Setup

Run the bot on your Android phone using Termux:

```bash
# Install Termux from F-Droid (not Play Store)

# Update packages
pkg update && pkg upgrade

# Install Python
pkg install python

# Install git
pkg install git

# Clone project
git clone https://github.com/yourusername/pickdeal-bd.git
cd pickdeal-bd

# Install dependencies
pip install -r requirements.txt

# Set up .env
cp .env.example .env
nano .env   # Edit your values

# Run bot
python main.py
```

To keep running after closing Termux:
```bash
# Install tmux
pkg install tmux

# Start new session
tmux new -s pickdeal

# Run bot inside tmux
python main.py

# Detach from tmux (bot keeps running)
# Press Ctrl+B then D
```

---

## 🚂 Railway Deployment

Deploy for free on [Railway.app](https://railway.app):

### Step 1: Push to GitHub
```bash
git init
git add .
git commit -m "Initial commit"
git branch -M main
git remote add origin https://github.com/yourusername/pickdeal-bd.git
git push -u origin main
```

### Step 2: Create Railway project
1. Go to [railway.app](https://railway.app)
2. Sign in with GitHub
3. Click **"New Project"**
4. Select **"Deploy from GitHub repo"**
5. Select your `pickdeal-bd` repository

### Step 3: Add Environment Variables
In Railway dashboard → your project → **Variables** tab:

| Variable         | Value                          |
|-----------------|--------------------------------|
| `BOT_TOKEN`     | Your bot token from @BotFather |
| `ADMIN_ID`      | Your Telegram user ID          |
| `BKASH_NUMBER`  | Your bKash number              |
| `NAGAD_NUMBER`  | Your Nagad number              |
| `SUPPORT_USERNAME` | Your support Telegram handle |
| `SUPPORT_PHONE` | Your support phone number      |

### Step 4: Deploy
Railway will automatically:
1. Detect the `Procfile`
2. Install `requirements.txt`
3. Run `python main.py`

Your bot is now live! 🎉

---

## 🗄️ Database Tables

| Table     | Purpose                              |
|-----------|--------------------------------------|
| `users`   | All Telegram users who used the bot  |
| `products`| Product catalog                      |
| `orders`  | Customer orders                      |
| `payments`| Payment screenshots & verification   |
| `coupons` | Discount coupon codes                |

---

## 📋 Admin Commands

| Command       | Description                        |
|---------------|------------------------------------|
| `/admin`      | Open admin panel (admin only)      |
| `/orders`     | View your own orders               |
| `/track <id>` | Track a specific order             |

---

## 🔄 Order Status Flow

```
pending → confirmed → processing → shipped → delivered
                ↓
           cancelled
```

---

## 🎫 Sample Coupon

A sample coupon is pre-loaded:
- **Code:** `PICKDEAL10`
- **Discount:** 10%
- **Uses:** 500

---

## ⚙️ Customization

### Adding Products
Edit `database/db_setup.py` → `_seed_products()` function, or directly insert into the SQLite database:
```sql
INSERT INTO products (name, category, description, price, stock)
VALUES ('New Product', 'Electronics', 'Description here', 999.00, 50);
```

### Changing Bot Name
Edit `utils/helpers.py` → `BOT_NAME` variable.

### Adding More Admins
Set `ADMIN_ID=123456,789012` (comma-separated) in your `.env`.

---

## 🔐 Security Notes

- ✅ Bot token stored in environment variable (never hardcoded)
- ✅ Admin ID verified on every admin action
- ✅ Input validation on all form fields
- ✅ Users can only view their own orders
- ✅ SQLite foreign keys enforced

---

## 🧰 Tech Stack

| Tool                   | Version | Purpose                    |
|------------------------|---------|----------------------------|
| Python                 | 3.11+   | Core language              |
| python-telegram-bot    | 20.8    | Telegram Bot API wrapper   |
| SQLite                 | built-in| Database                   |
| python-dotenv          | 1.0.1   | Environment variables      |

---

## 📞 Support

If you have questions, open a GitHub issue or contact @PickDealSupport on Telegram.

---

*Built with ❤️ for Bangladesh 🇧🇩*
