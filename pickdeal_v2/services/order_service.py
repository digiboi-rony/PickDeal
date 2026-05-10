"""services/order_service.py — order business logic"""
import logging
import models.order as order_model
import models.cart as cart_model
import models.product as product_model
import models.user as user_model
import models.coupon as coupon_model
from config.settings import DELIVERY_CHARGE_DHAKA, DELIVERY_CHARGE_OUTSIDE

logger = logging.getLogger(__name__)


def build_order_from_cart(user_id: int, session: dict) -> dict | None:
    """
    Build order totals from cart + session data.
    Returns a dict with all financial details, or None if cart is empty.
    """
    items = cart_model.get_items(user_id)
    if not items:
        return None

    subtotal = sum(float(it["eff_price"]) * it["quantity"] for it in items)
    area     = session.get("area", "outside")
    delivery = DELIVERY_CHARGE_DHAKA if area == "dhaka" else DELIVERY_CHARGE_OUTSIDE

    coupon_code = session.get("coupon_code")
    discount    = float(session.get("discount", 0))
    total       = subtotal + delivery - discount

    return {
        "items":       [dict(it) for it in items],
        "subtotal":    subtotal,
        "delivery":    delivery,
        "discount":    discount,
        "total":       max(total, 0),
        "coupon_code": coupon_code,
        "area":        area,
    }


def place_order(user_id: int, session: dict, financials: dict) -> int:
    """
    Create order + order_items, update product stock, clear cart.
    Returns the new order_id.
    """
    order_id = order_model.create(
        user_id        = user_id,
        full_name      = session["full_name"],
        phone          = session["phone"],
        address        = session["address"],
        area           = financials["area"],
        notes          = session.get("notes", ""),
        subtotal       = financials["subtotal"],
        delivery_fee   = financials["delivery"],
        discount       = financials["discount"],
        total          = financials["total"],
        coupon_code    = financials.get("coupon_code"),
        payment_method = session.get("payment_method", "bkash"),
    )

    # Save order items
    items_to_save = []
    for it in financials["items"]:
        items_to_save.append({
            "product_id":   it["product_id"],
            "product_name": it["name"],
            "quantity":     it["quantity"],
            "unit_price":   float(it["eff_price"]),
        })
    order_model.add_items(order_id, items_to_save)

    # Deduct stock
    for it in financials["items"]:
        product_model.update_stock(it["product_id"], -it["quantity"])

    # Use coupon if applied
    if financials.get("coupon_code"):
        coupon_model.use(financials["coupon_code"])

    # Update user total spent
    user_model.add_spent(user_id, financials["total"])

    # Clear cart
    cart_model.clear(user_id)

    logger.info(f"✅ Order #{order_id} placed for user {user_id}")
    return order_id
