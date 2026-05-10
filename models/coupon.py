"""models/coupon.py"""
from database.connection import get_conn


def validate(code: str, order_total: float):
    row = get_conn().execute("""
        SELECT * FROM coupons
        WHERE code=? AND is_active=1
          AND used_count < max_uses
          AND (expires_at IS NULL OR expires_at > datetime('now'))
    """, (code.upper(),)).fetchone()
    if not row:
        return None, "❌ কুপন কোড সঠিক নয় বা মেয়াদ শেষ।"
    if order_total < row["min_order"]:
        return None, f"❌ এই কুপনের জন্য সর্বনিম্ন অর্ডার ৳{row['min_order']:.0f}"
    return row, None


def calc_discount(coupon_row, order_total: float) -> float:
    if coupon_row["type"] == "percent":
        return round(order_total * coupon_row["value"] / 100, 2)
    return min(float(coupon_row["value"]), order_total)


def use(code: str):
    conn = get_conn()
    conn.execute("UPDATE coupons SET used_count=used_count+1 WHERE code=?", (code.upper(),))
    conn.commit()


def get_all():
    return get_conn().execute("SELECT * FROM coupons ORDER BY coupon_id DESC").fetchall()
