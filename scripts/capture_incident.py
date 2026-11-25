"""Captures a live Prometheus + JSON log window into an IncidentBench scenario folder."""

import argparse
import json
import os
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

import httpx

from incidentiq.guardrails.guards import GuardrailManager
from mcp_servers.validation import (
    ALLOWED_METRICS,
    ALLOWED_SERVICES,
    get_safe_log_path,
    sanitize_promql_service,
    validate_scenario_id,
    validate_service,
)


def fetch_prometheus_series(
    prometheus_url: str,
    service: str,
    metric: str,
    start_dt: datetime,
    end_dt: datetime,
    step: str = "15s",
) -> list[dict[str, Any]]:
    """Queries Prometheus query_range for shop_<metric>{service='<service>'}."""
    clean_srv = sanitize_promql_service(service)
    resp = httpx.get(
        f"{prometheus_url.rstrip('/')}/api/v1/query_range",
        params={
            "query": f"shop_{metric}{{service='{clean_srv}'}}",
            "start": str(int(start_dt.timestamp())),
            "end": str(int(end_dt.timestamp())),
            "step": step,
        },
        timeout=5.0,
    )
    resp.raise_for_status()
    result = resp.json().get("data", {}).get("result", [])
    if not result:
        return []
    return [
        {
            "timestamp": datetime.fromtimestamp(float(pt[0]), tz=UTC).isoformat(),
            "value": float(pt[1]),
        }
        for pt in result[0].get("values", [])
    ]


def collect_logs_window(
    service: str,
    start_dt: datetime,
    end_dt: datetime,
    logs_dir: str = "logs",
) -> list[dict[str, Any]]:
    """Extracts and PII-scrubs structured JSON log lines for a service window."""
    safe_path = get_safe_log_path(service)
    candidate = Path(logs_dir) / (
        Path(safe_path).name if safe_path else f"{service}.log"
    )
    if not candidate.exists():
        candidate = Path(logs_dir) / "shop.log"
    if not candidate.exists():
        return []

    captured: list[dict[str, Any]] = []
    with open(candidate, encoding="utf-8") as f:
        for line in f:
            raw = line.strip()
            if not raw:
                continue
            try:
                entry = json.loads(raw)
            except json.JSONDecodeError:
                continue
            if entry.get("service") and entry.get("service") != service:
                continue
            ts_raw = entry.get("ts") or entry.get("timestamp")
            if isinstance(ts_raw, str):
                try:
                    ts_dt = datetime.fromisoformat(ts_raw)
                    if ts_dt.tzinfo is None:
                        ts_dt = ts_dt.replace(tzinfo=UTC)
                    if ts_dt < start_dt or ts_dt > end_dt:
                        continue
                except ValueError:
                    pass
            msg = str(entry.get("msg") or entry.get("event") or "")
            clean_msg, _ = GuardrailManager.redact_pii(msg)
            entry["msg"] = clean_msg
            captured.append(entry)
    return captured


def build_captured_scenario(
    scenario_id: str,
    service: str,
    symptom: str,
    metrics_data: dict[str, list[dict[str, Any]]],
    log_entries: list[dict[str, Any]],
    start_dt: datetime,
    end_dt: datetime,
    output_root: str = "scenarios_real",
    category: str | None = None,
    should_abstain: bool = False,
) -> Path:
    """Writes a validated IncidentBench scenario directory to disk."""
    if not validate_service(service):
        raise ValueError(
            f"Unsupported service '{service}'. Allowed: {sorted(ALLOWED_SERVICES)}"
        )
    if not validate_scenario_id(scenario_id):
        raise ValueError(f"Invalid scenario_id '{scenario_id}'")

    clean_symptom, _ = GuardrailManager.redact_pii(symptom)
    out_dir = Path(output_root) / scenario_id
    out_dir.mkdir(parents=True, exist_ok=True)

    alert_payload = {
        "service": service,
        "symptom": clean_symptom,
        "window_start": start_dt.isoformat(),
        "window_end": end_dt.isoformat(),
    }
    metrics_payload = {"service": service, "metrics": metrics_data}
    label_payload: dict[str, Any] = {
        "scenario_id": scenario_id,
        "root_cause_category": category,
        "root_cause_service": service if not should_abstain else None,
        "key_evidence": [],
        "acceptable_actions": [],
        "should_abstain": should_abstain,
        "difficulty": "real_capture",
    }

    (out_dir / "alert.json").write_text(json.dumps(alert_payload, indent=2))
    (out_dir / "metrics.json").write_text(json.dumps(metrics_payload, indent=2))
    (out_dir / "label.json").write_text(json.dumps(label_payload, indent=2))
    with open(out_dir / "logs.jsonl", "w", encoding="utf-8") as f:
        for entry in log_entries:
            clean_entry = dict(entry)
            for field in ("msg", "event", "message"):
                if isinstance(clean_entry.get(field), str):
                    redacted, _ = GuardrailManager.redact_pii(clean_entry[field])
                    clean_entry[field] = redacted
            f.write(json.dumps(clean_entry) + "\n")

    return out_dir


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Capture live Prometheus + log telemetry as a replayable scenario"
    )
    parser.add_argument("--scenario-id", required=True)
    parser.add_argument("--service", required=True)
    parser.add_argument("--symptom", required=True)
    parser.add_argument(
        "--prometheus-url",
        default=os.getenv("PROMETHEUS_URL", "http://127.0.0.1:9090"),
    )
    parser.add_argument("--logs-dir", default="logs")
    parser.add_argument("--minutes", type=int, default=30)
    parser.add_argument("--category", default=None)
    parser.add_argument("--should-abstain", action="store_true")
    parser.add_argument("--output-root", default="scenarios_real")
    args = parser.parse_args()

    end_dt = datetime.now(UTC)
    start_dt = end_dt - timedelta(minutes=args.minutes)

    metrics_data: dict[str, list[dict[str, Any]]] = {}
    for metric in ALLOWED_METRICS:
        try:
            metrics_data[metric] = fetch_prometheus_series(
                prometheus_url=args.prometheus_url,
                service=args.service,
                metric=metric,
                start_dt=start_dt,
                end_dt=end_dt,
            )
        except httpx.HTTPError as exc:
            print(f"[!] Warning: failed fetching metric '{metric}': {exc}")
            metrics_data[metric] = []

    log_entries = collect_logs_window(
        service=args.service,
        start_dt=start_dt,
        end_dt=end_dt,
        logs_dir=args.logs_dir,
    )
    out_dir = build_captured_scenario(
        scenario_id=args.scenario_id,
        service=args.service,
        symptom=args.symptom,
        metrics_data=metrics_data,
        log_entries=log_entries,
        start_dt=start_dt,
        end_dt=end_dt,
        output_root=args.output_root,
        category=args.category,
        should_abstain=args.should_abstain,
    )
    print(
        f"[+] Captured scenario '{args.scenario_id}' -> {out_dir} "
        f"({len(log_entries)} log lines, {sum(len(v) for v in metrics_data.values())} metric points)"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
