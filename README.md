# Wholesale Orderbook Django Service

Deterministic B2B wholesale order book matching, supplier lot allocation, and cross-border checkout service built with **Python**, **Django**, and **TypeScript** API contracts.

## Problem
In fragmented B2B wholesale markets, multiple buyers compete for limited supplier inventory batches across currencies and delivery tiers. Without strict row-level locking and idempotency keys, concurrent orders double-allocate stock or leave partial reservations.

## How to Run
```bash
pip install django pytest pytest-django
pytest -v
```
