def brl(value):
    try:
        return f"R$ {float(value):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
    except Exception:
        return "R$ --"


def build(offer, coupon=None):
    discount = float(offer.get("discount") or 0)
    if discount > 0:
        line = f"🔥 {discount:.0f}% OFF"
    else:
        line = "🔥 Oferta encontrada"
    msg = (
        f"{line}\n\n"
        f"{offer.get('title','Produto')}\n"
        f"💰 {brl(offer.get('price'))}"
    )
    if offer.get("original_price"):
        msg += f" (antes {brl(offer['original_price'])})"
    if coupon:
        msg += f"\n🎟️ Cupom: {coupon.strip()}"
    msg += f"\n🛒 {offer.get('permalink','')}\n\n⚠️ Preço e estoque podem mudar no Mercado Livre."
    return msg
