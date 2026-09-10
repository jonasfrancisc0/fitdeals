def money(value):
    if value is None:
        return "Preço não informado"
    return f"R$ {value:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")

def build_message(offer, coupon=None):
    lines = [
        "🔥 OFERTA FITDEALS",
        "",
        offer.get("title", "Produto"),
        "",
        f"💰 Por: {money(offer.get('price'))}",
    ]

    if offer.get("original_price") and offer.get("discount"):
        lines.append(
            f"🏷️ De: {money(offer.get('original_price'))} "
            f"({offer.get('discount'):.0f}% OFF)"
        )

    if coupon:
        lines.extend(["", f"🎟️ Cupom: {coupon}"])

    url = offer.get("affiliate_url") or offer.get("permalink")
    if url:
        lines.extend(["", f"🔗 Comprar: {url}"])

    lines.extend(["", "⚠️ Preço e disponibilidade podem mudar sem aviso."])
    return "\n".join(lines)
