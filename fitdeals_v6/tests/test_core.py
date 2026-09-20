import unittest
from app.mercadolivre import MercadoLivreClient


class CoreTests(unittest.TestCase):
    def test_discount(self):
        c = MercadoLivreClient()
        c._sale_price = lambda item_id: (80.0, 100.0, "promotion", {"amount": 80.0, "regular_amount": 100.0})
        out = c.price_for_item({"id": "MLB123", "title": "Teste", "permalink": "https://example.com"})
        self.assertEqual(out["discount"], 20.0)
        self.assertEqual(out["price_type"], "promotion")

    def test_fallback_to_search_price(self):
        c = MercadoLivreClient()
        c._sale_price = lambda item_id: (_ for _ in ()).throw(RuntimeError("fail"))
        c._prices = lambda item_id: (_ for _ in ()).throw(RuntimeError("fail"))
        out = c.price_for_item({"id": "MLB123", "title": "Teste", "price": 42.0, "original_price": 50.0})
        self.assertEqual(out["price"], 42.0)
        self.assertEqual(out["discount"], 16.0)


if __name__ == "__main__":
    unittest.main()
