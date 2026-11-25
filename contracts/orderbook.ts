export interface AllocateOrderRequest {
  buyer_id: string;
  sku: string;
  qty: number;
  idempotency_key: string;
}

export interface LotSplit {
  lot_id: number;
  supplier_code: string;
  qty: number;
  unit_price_cents: number;
}

export interface AllocateOrderResponse {
  order_id: number;
  sku: string;
  allocated_qty: number;
  total_cents: number;
  replayed: boolean;
  lot_splits: LotSplit[];
  trace_id: string;
  latency_ms: number;
}
