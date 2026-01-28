import threading


class MockOdooClient:
    """Simulates Odoo/Cre-soft API for the POC."""

    def __init__(self):
        self._counter = 1000
        self._lock = threading.Lock()

    def _next_id(self) -> int:
        with self._lock:
            self._counter += 1
            return self._counter

    def create_sale_order(self, rfq_data: dict) -> dict:
        order_id = self._next_id()
        return {
            "sale_order_id": order_id,
            "quotation_number": f"S{order_id:05d}",
            "status": "draft",
            "customer": rfq_data.get("customer_name", "Unknown"),
        }

    def confirm_quotation(self, order_id: int) -> dict:
        return {
            "sale_order_id": order_id,
            "status": "confirmed",
        }

    def get_quotation_pdf(self, order_id: int) -> bytes:
        return b"%PDF-1.4 (mock quotation PDF placeholder)"


mock_odoo = MockOdooClient()
