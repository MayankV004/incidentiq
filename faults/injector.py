import argparse
import sys

import httpx

SERVICE_URLS = {
    "gateway": "http://localhost:8001",
    "orders": "http://localhost:8002",
    "payments": "http://localhost:8003",
    "fake_external": "http://localhost:8004",
}


def inject_db_pool_exhaustion(enable: bool = True):
    print(f"[*] {'Enabling' if enable else 'Disabling'} DB Pool Exhaustion on Orders Service...")
    resp = httpx.post(f"{SERVICE_URLS['orders']}/chaos/pool_exhaust?enabled={str(enable).lower()}")
    print(f"[Result] HTTP {resp.status_code}: {resp.json()}")


def inject_slow_query(enable: bool = True):
    print(f"[*] {'Enabling' if enable else 'Disabling'} Slow Query simulation on Orders Service...")
    resp = httpx.post(f"{SERVICE_URLS['orders']}/chaos/slow_query?enabled={str(enable).lower()}")
    print(f"[Result] HTTP {resp.status_code}: {resp.json()}")


def inject_dependency_delay(delay_sec: float = 6.0, failure_rate: float = 0.0):
    print(f"[*] Setting Fake External delay to {delay_sec}s, failure_rate={failure_rate}...")
    resp = httpx.post(
        f"{SERVICE_URLS['fake_external']}/chaos",
        json={"delay_sec": delay_sec, "failure_rate": failure_rate},
    )
    print(f"[Result] HTTP {resp.status_code}: {resp.json()}")


def reset_all():
    print("[*] Resetting all chaos injection to normal operation...")
    try:
        httpx.post(f"{SERVICE_URLS['orders']}/chaos/pool_exhaust?enabled=false")
        httpx.post(f"{SERVICE_URLS['orders']}/chaos/slow_query?enabled=false")
        httpx.post(f"{SERVICE_URLS['fake_external']}/chaos", json={"delay_sec": 0.0, "failure_rate": 0.0})
        print("[*] Shop restored to healthy baseline.")
    except (httpx.HTTPError, OSError) as e:
        print(f"[Warning] Could not reach all services: {e}", file=sys.stderr)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="IncidentIQ Chaos & Fault Injector")
    parser.add_argument(
        "--fault",
        choices=["db_pool", "slow_query", "dependency_timeout", "reset"],
        required=True,
        help="Fault type to inject",
    )
    args = parser.parse_args()

    if args.fault == "db_pool":
        inject_db_pool_exhaustion(True)
    elif args.fault == "slow_query":
        inject_slow_query(True)
    elif args.fault == "dependency_timeout":
        inject_dependency_delay(delay_sec=7.0, failure_rate=0.4)
    elif args.fault == "reset":
        reset_all()
