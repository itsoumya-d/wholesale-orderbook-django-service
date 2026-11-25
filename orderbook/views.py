import json
import time
import uuid
from django.http import HttpRequest, JsonResponse
from django.views.decorators.http import require_GET, require_POST
from orderbook.models import SupplierLot
from orderbook.services import InsufficientInventoryError, allocate_order


@require_POST
def allocate_view(request: HttpRequest) -> JsonResponse:
    t0 = time.perf_counter()
    trace_id = request.headers.get("X-Trace-Id") or f"tr-{uuid.uuid4().hex[:10]}"
    try:
        body = json.loads(request.body.decode("utf-8"))
        buyer_id = str(body["buyer_id"]).strip()
        sku = str(body["sku"]).strip()
        qty = int(body["qty"])
        idem_key = str(body["idempotency_key"]).strip()
        if not buyer_id or not sku or not idem_key:
            raise ValueError("buyer_id, sku, and idempotency_key are required")
    except (KeyError, TypeError, ValueError, json.JSONDecodeError) as exc:
        return JsonResponse({"error": str(exc), "trace_id": trace_id}, status=400)

    try:
        outcome = allocate_order(
            buyer_id=buyer_id, sku=sku, qty=qty, idempotency_key=idem_key, trace_id=trace_id
        )
    except ValueError as exc:
        return JsonResponse({"error": str(exc), "trace_id": trace_id}, status=400)
    except InsufficientInventoryError as exc:
        return JsonResponse(
            {"error": str(exc), "available_qty": exc.available, "trace_id": trace_id}, status=409
        )

    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 2)
    return JsonResponse(
        {
            "order_id": outcome.order.id,
            "sku": outcome.order.sku,
            "allocated_qty": outcome.order.allocated_qty,
            "total_cents": outcome.order.total_cents,
            "replayed": outcome.replayed,
            "lot_splits": outcome.lot_splits,
            "trace_id": outcome.order.trace_id,
            "latency_ms": elapsed_ms,
        },
        status=200 if outcome.replayed else 201,
    )


@require_GET
def depth_view(request: HttpRequest, sku: str) -> JsonResponse:
    lots = list(
        SupplierLot.objects.filter(sku=sku, available_qty__gt=0)
        .order_by("unit_price_cents", "id")
        .values("id", "supplier_code", "unit_price_cents", "available_qty", "currency")
    )
    return JsonResponse(
        {
            "sku": sku,
            "total_available": sum(l["available_qty"] for l in lots),
            "lowest_unit_price_cents": lots[0]["unit_price_cents"] if lots else None,
            "lots": lots,
        }
    )
