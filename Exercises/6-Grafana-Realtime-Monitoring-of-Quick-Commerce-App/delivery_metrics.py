"""Simulate quick-commerce delivery metrics and expose them to Prometheus on port 8000."""
import random
import time

from prometheus_client import Gauge, Summary, start_http_server

total_deliveries = Gauge("total_deliveries", "Total number of deliveries")
pending_deliveries = Gauge("pending_deliveries", "Number of pending deliveries")
on_the_way_deliveries = Gauge("on_the_way_deliveries", "Number of deliveries on the way")
average_delivery_time = Summary("average_delivery_time", "Average delivery time in seconds")


def simulate_metrics():
    total_deliveries.set(random.randint(50, 150))
    pending_deliveries.set(random.randint(10, 20))
    on_the_way_deliveries.set(random.randint(5, 15))
    average_delivery_time.observe(random.randint(20, 40))


if __name__ == "__main__":
    start_http_server(8000)
    print("Serving delivery metrics on http://localhost:8000/metrics", flush=True)
    while True:
        simulate_metrics()
        time.sleep(1)
