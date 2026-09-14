import json
from pathlib import Path

PO_FILE = Path("data/purchase_orders.json")


def load_purchase_orders():
    with open(PO_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def get_purchase_order(po_number):
    purchase_orders = load_purchase_orders()

    for po in purchase_orders:
        if po["po_number"] == po_number:
            return po

    return None