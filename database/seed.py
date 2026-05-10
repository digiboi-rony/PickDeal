"""database/seed.py — sample data seeder"""
import json
import logging
from database.connection import get_conn

logger = logging.getLogger(__name__)

CATEGORIES = [
    (1, "Fashion",      "👗", "পোশাক ও ফ্যাশন আইটেম",    1),
    (2, "Gadgets",      "⚡", "ইলেকট্রনিক্স ও গ্যাজেট",  2),
    (3, "Umbrellas",    "☂️", "ছাতা কালেকশন",              3),
    (4, "Offers",       "🔥", "বিশেষ অফার ও ডিসকাউন্ট",   4),
    (5, "New Arrivals", "✨", "নতুন পণ্য সমূহ",             5),
]

PRODUCTS = [
    (2, "Smart Watch Pro X",
     "⌚ *বৈশিষ্ট্য:*\n• হার্ট রেট ও SpO2 মনিটর\n• স্লিপ ট্র্যাকার\n• ৭ দিনের ব্যাটারি\n• IP67 ওয়াটারপ্রুফ\n• ১০০+ স্পোর্ট মোড\n• Android ও iOS সাপোর্ট",
     1499, 1299, 50, json.dumps(["watch","smart","fitness"]), 1, 1),

    (3, "Premium Auto Umbrella",
     "☂️ *বৈশিষ্ট্য:*\n• ডাবল লেয়ার উইন্ডপ্রুফ\n• অটো ওপেন/ক্লোজ\n• UV প্রোটেকশন SPF50+\n• ১০ ফাইবার রিব\n• কম্প্যাক্ট ট্র্যাভেল সাইজ",
     349, 299, 100, json.dumps(["umbrella","rain","UV"]), 0, 1),

    (2, "Bluetooth Speaker X9",
     "🔊 *বৈশিষ্ট্য:*\n• ৩৬০° সাউন্ড\n• ২০W আউটপুট\n• IPX5 ওয়াটারপ্রুফ\n• ১২ ঘণ্টা ব্যাটারি\n• TWS পেয়ারিং\n• বিল্ট-ইন মাইক",
     899, 799, 30, json.dumps(["speaker","bluetooth","audio"]), 1, 0),

    (1, "Premium Cotton T-Shirt",
     "👕 *বিবরণ:*\n• ১০০% প্রিমিয়াম কটন\n• সাইজ: S/M/L/XL/XXL\n• রঙ: White, Black, Navy, Red\n• মেশিন ওয়াশযোগ্য",
     299, None, 200, json.dumps(["tshirt","fashion","cotton"]), 0, 1),

    (2, "TWS Earbuds Pro",
     "🎧 *বৈশিষ্ট্য:*\n• Active Noise Cancellation\n• ৩০ ঘণ্টা মোট ব্যাটারি\n• IPX4 ওয়াটার রেজিস্ট্যান্ট\n• টাচ কন্ট্রোল\n• লো লেটেন্সি গেমিং মোড",
     1299, 1099, 40, json.dumps(["earbuds","ANC","wireless"]), 1, 0),

    (4, "Combo: Watch + Earbuds",
     "🎁 *স্পেশাল বান্ডেল:*\n• Smart Watch Pro X\n• TWS Earbuds Pro\n• আলাদা কেনার চেয়ে ৳৫০০ সাশ্রয়\n• প্রিমিয়াম গিফট বক্স\n• সীমিত স্টক!",
     2299, 1999, 15, json.dumps(["combo","bundle","offer"]), 1, 1),

    (5, "Wireless Charging Pad",
     "🔋 *বৈশিষ্ট্য:*\n• ১৫W ফাস্ট ওয়্যারলেস চার্জিং\n• Universal Qi সাপোর্ট\n• LED ইন্ডিকেটর\n• অ্যান্টি-স্লিপ সারফেস\n• ওভারহিট প্রোটেকশন",
     699, 599, 60, json.dumps(["charger","wireless","fast"]), 1, 0),

    (1, "Genuine Leather Wallet",
     "👛 *বিবরণ:*\n• ১০০% অরিজিনাল লেদার\n• RFID ব্লকিং\n• ৮টি কার্ড স্লট\n• রঙ: Brown ও Black\n• গিফট বক্স সহ",
     549, 449, 75, json.dumps(["wallet","leather","RFID"]), 0, 0),
]

COUPONS = [
    ("PICKDEAL10", "percent", 10.0, 200,  500),
    ("NEWUSER20",  "percent", 20.0, 500,  100),
    ("FLAT100",    "fixed",  100.0, 800,   50),
]


def run():
    conn = get_conn()
    c = conn.cursor()
    if c.execute("SELECT COUNT(*) FROM categories").fetchone()[0] > 0:
        return
    c.executemany(
        "INSERT OR IGNORE INTO categories(cat_id,name,emoji,description,sort_order) VALUES(?,?,?,?,?)",
        CATEGORIES
    )
    for p in PRODUCTS:
        c.execute("""
            INSERT INTO products
              (cat_id,name,description,price,discount_price,stock,tags,is_featured,is_bestseller)
            VALUES(?,?,?,?,?,?,?,?,?)
        """, p)
    c.executemany(
        "INSERT OR IGNORE INTO coupons(code,type,value,min_order,max_uses) VALUES(?,?,?,?,?)",
        COUPONS
    )
    conn.commit()
    logger.info("🌱 Sample data seeded.")
