from django.urls import path
from orderbook.views import allocate_view, depth_view

urlpatterns = [
    path("api/orders/allocate", allocate_view, name="allocate-order"),
    path("api/orderbook/<str:sku>", depth_view, name="orderbook-depth"),
]
