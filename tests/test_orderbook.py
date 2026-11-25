import json
import pytest
from orderbook.models import SupplierLot, WholesaleOrder


@pytest.fixture
def seed_lots(db):
    SupplierLot.objects.create(sku="SKU-SERUM-50ML", supplier_code="SUP-DE", unit_price_cents=1450, available_qty=10)
    SupplierLot.objects.create(sku="SKU-SERUM-50ML", supplier_code="SUP-NL", unit_price_cents=1200, available_qty=6)
    SupplierLot.objects.create(sku="SKU-SERUM-50ML", supplier_code="SUP-FR", unit_price_cents=1350, available_qty=8)


def test_greedy_price_priority_allocation(client, seed_lots):
    resp = client.post(
        "/api/orders/allocate",
        data=json.dumps({"buyer_id": "buyer-1", "sku": "SKU-SERUM-50ML", "qty": 10, "idempotency_key": "idem-1"}),
        content_type="application/json",
        HTTP_X_TRACE_ID="tr-greedy-01",
    )
    assert resp.status_code == 201
    body = resp.json()
    assert body["replayed"] is False
    # 6 @ 1200 + 4 @ 1350 = 7200 + 5400 = 12600
    assert body["total_cents"] == 12600
    assert [s["supplier_code"] for s in body["lot_splits"]] == ["SUP-NL", "SUP-FR"]
    assert SupplierLot.objects.get(supplier_code="SUP-NL").available_qty == 0
    assert SupplierLot.objects.get(supplier_code="SUP-FR").available_qty == 4


def test_idempotent_replay_does_not_double_allocate(client, seed_lots):
    payload = json.dumps({"buyer_id": "buyer-1", "sku": "SKU-SERUM-50ML", "qty": 5, "idempotency_key": "idem-dup"})
    r1 = client.post("/api/orders/allocate", data=payload, content_type="application/json")
    r2 = client.post("/api/orders/allocate", data=payload, content_type="application/json")
    assert r1.status_code == 201 and r2.status_code == 200
    assert r2.json()["replayed"] is True
    assert r2.json()["order_id"] == r1.json()["order_id"]
    assert WholesaleOrder.objects.count() == 1
    assert SupplierLot.objects.get(supplier_code="SUP-NL").available_qty == 1


def test_atomic_rollback_on_insufficient_inventory(client, seed_lots):
    resp = client.post(
        "/api/orders/allocate",
        data=json.dumps({"buyer_id": "buyer-2", "sku": "SKU-SERUM-50ML", "qty": 99, "idempotency_key": "idem-big"}),
        content_type="application/json",
    )
    assert resp.status_code == 409
    assert resp.json()["available_qty"] == 24
    assert SupplierLot.objects.get(supplier_code="SUP-NL").available_qty == 6
    assert WholesaleOrder.objects.count() == 0


def test_orderbook_depth_endpoint(client, seed_lots):
    resp = client.get("/api/orderbook/SKU-SERUM-50ML")
    assert resp.status_code == 200
    body = resp.json()
    assert body["total_available"] == 24
    assert body["lowest_unit_price_cents"] == 1200


def test_invalid_qty_returns_400(client, seed_lots):
    resp = client.post(
        "/api/orders/allocate",
        data=json.dumps({"buyer_id": "buyer-1", "sku": "SKU-SERUM-50ML", "qty": 0, "idempotency_key": "idem-zero"}),
        content_type="application/json",
    )
    assert resp.status_code == 400
