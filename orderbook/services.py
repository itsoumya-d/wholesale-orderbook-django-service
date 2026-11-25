from dataclasses import dataclass
from typing import List
from django.db import transaction
from orderbook.models import SupplierLot, WholesaleOrder


class InsufficientInventoryError(Exception):
    def __init__(self, sku: str, requested: int, available: int):
        super().__init__(f"Insufficient stock for {sku}: requested={requested}, available={available}")
        self.sku = sku
        self.requested = requested
        self.available = available


@dataclass
class AllocationOutcome:
    order: WholesaleOrder
    replayed: bool
    lot_splits: List[dict]


def allocate_order(
    *, buyer_id: str, sku: str, qty: int, idempotency_key: str, trace_id: str
) -> AllocationOutcome:
    if qty <= 0:
        raise ValueError("qty must be positive")

    with transaction.atomic():
        existing = WholesaleOrder.objects.filter(idempotency_key=idempotency_key).first()
        if existing:
            return AllocationOutcome(order=existing, replayed=True, lot_splits=[])

        lots = list(
            SupplierLot.objects.select_for_update()
            .filter(sku=sku, available_qty__gt=0)
            .order_by("unit_price_cents", "id")
        )
        total_avail = sum(lot.available_qty for lot in lots)
        if total_avail < qty:
            raise InsufficientInventoryError(sku=sku, requested=qty, available=total_avail)

        remaining = qty
        total_cents = 0
        splits: List[dict] = []
        for lot in lots:
            if remaining == 0:
                break
            take = min(remaining, lot.available_qty)
            lot.available_qty -= take
            lot.save(update_fields=["available_qty"])
            total_cents += take * lot.unit_price_cents
            remaining -= take
            splits.append({
                "lot_id": lot.id,
                "supplier_code": lot.supplier_code,
                "qty": take,
                "unit_price_cents": lot.unit_price_cents,
            })

        order = WholesaleOrder.objects.create(
            idempotency_key=idempotency_key,
            buyer_id=buyer_id,
            sku=sku,
            requested_qty=qty,
            allocated_qty=qty,
            total_cents=total_cents,
            trace_id=trace_id,
        )
        return AllocationOutcome(order=order, replayed=False, lot_splits=splits)
