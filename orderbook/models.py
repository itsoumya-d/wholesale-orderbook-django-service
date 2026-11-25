from django.db import models


class SupplierLot(models.Model):
    sku = models.CharField(max_length=64, db_index=True)
    supplier_code = models.CharField(max_length=32)
    unit_price_cents = models.PositiveIntegerField()
    available_qty = models.PositiveIntegerField()
    currency = models.CharField(max_length=3, default="EUR")

    class Meta:
        ordering = ["unit_price_cents", "id"]


class WholesaleOrder(models.Model):
    idempotency_key = models.CharField(max_length=64, unique=True)
    buyer_id = models.CharField(max_length=64)
    sku = models.CharField(max_length=64, db_index=True)
    requested_qty = models.PositiveIntegerField()
    allocated_qty = models.PositiveIntegerField()
    total_cents = models.PositiveBigIntegerField()
    trace_id = models.CharField(max_length=64)
    created_at = models.DateTimeField(auto_now_add=True)
