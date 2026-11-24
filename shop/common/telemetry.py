import atexit
import json
import logging
import os
import queue
import time
import uuid
from logging.handlers import QueueHandler, QueueListener, RotatingFileHandler

import psutil
import structlog
from fastapi import FastAPI, Request, Response
from prometheus_client import (
    CONTENT_TYPE_LATEST,
    Counter,
    Gauge,
    Histogram,
    generate_latest,
)

# Prometheus Metrics (Aligend with Doc 06: Allowed Metrics)
# Allowed metrics: error_rate, latency_p95, request_rate, memory_mb, db_pool_in_use, cache_hit_rate

REQUESTS_TOTAL = Counter(
    "shop_requests_total",
    "Total HTTP requests handled by shop services",
    ["service", "method", "endpoint", "status"],
)

REQUEST_LATENCY = Histogram(
    "shop_request_duration_seconds",
    "HTTP request latency in seconds",
    ["service", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
)

ERRORS_TOTAL = Counter(
    "shop_errors_total",
    "Total errors encountered",
    ["service", "error_type"],
)

MEMORY_MB = Gauge(
    "shop_memory_mb",
    "Current memory usage in megabytes",
    ["service"],
)

DB_POOL_IN_USE = Gauge(
    "shop_db_pool_in_use",
    "Number of active database pool connections currently in use",
    ["service"],
)

CACHE_HIT_RATE = Gauge(
    "shop_cache_hit_rate",
    "Cache hit rate ratio (0.0 to 1.0)",
    ["service"],
)


_LOG_QUEUE: queue.Queue = queue.Queue()
_QUEUE_LISTENER: QueueListener | None = None
_SERVICE_LISTENERS: dict[str, tuple[queue.Queue, QueueListener]] = {}


def _stop_listener(listener: QueueListener) -> None:
    if getattr(listener, "_thread", None) is not None:
        listener.stop()
    for handler in listener.handlers:
        handler.close()


def _get_queue_logger(service_name: str) -> logging.Logger:
    global _QUEUE_LISTENER
    os.makedirs("logs", exist_ok=True)
    log_file_path = f"logs/{service_name}.log"
    shared_log_path = "logs/shop.log"

    existing = _SERVICE_LISTENERS.get(service_name)
    if (
        existing is not None
        and os.path.exists(log_file_path)
        and os.path.exists(shared_log_path)
    ):
        service_queue, listener = existing
    else:
        if existing is not None:
            _stop_listener(existing[1])
        service_queue = queue.Queue()
        h_service = RotatingFileHandler(
            log_file_path, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        h_shared = RotatingFileHandler(
            shared_log_path, maxBytes=5 * 1024 * 1024, backupCount=3
        )
        fmt = logging.Formatter("%(message)s")
        h_service.setFormatter(fmt)
        h_shared.setFormatter(fmt)

        listener = QueueListener(
            service_queue, h_service, h_shared, respect_handler_level=True
        )
        listener.start()
        atexit.register(_stop_listener, listener)
        _SERVICE_LISTENERS[service_name] = (service_queue, listener)

    _QUEUE_LISTENER = listener

    logger = logging.getLogger(f"shop.{service_name}")
    logger.setLevel(logging.INFO)
    logger.propagate = False
    has_current_queue = any(
        isinstance(h, QueueHandler) and getattr(h, "queue", None) is service_queue
        for h in logger.handlers
    )
    if not has_current_queue:
        for h in list(logger.handlers):
            logger.removeHandler(h)
        logger.addHandler(QueueHandler(service_queue))
    return logger


def configure_logging(service_name: str) -> structlog.BoundLogger:
    """Configures non-blocking structured JSON logging writing via a background QueueListener."""
    _get_queue_logger(service_name)

    def file_output_processor(logger, method_name, event_dict):
        target_service = str(event_dict.get("service") or service_name)
        line = json.dumps(event_dict)
        _get_queue_logger(target_service).info(line)
        return event_dict

    structlog.configure(
        processors=[
            structlog.contextvars.merge_contextvars,
            structlog.processors.add_log_level,
            structlog.processors.TimeStamper(fmt="iso", key="ts"),
            file_output_processor,
            structlog.processors.JSONRenderer(),
        ],
        wrapper_class=structlog.make_filtering_bound_logger(20),  # INFO
        context_class=dict,
        logger_factory=structlog.PrintLoggerFactory(),
        cache_logger_on_first_use=True,
    )

    return structlog.get_logger(service=service_name)


def setup_telemetry(app: FastAPI, service_name: str):
    """Adds metrics, structured logging middleware, and /metrics endpoint to a FastAPI app."""
    logger = configure_logging(service_name)

    # Memory reporter helper
    try:
        process = psutil.Process(os.getpid())
        mem_info = process.memory_info()
        MEMORY_MB.labels(service=service_name).set(mem_info.rss / (1024 * 1024))
    except (psutil.Error, OSError):
        MEMORY_MB.labels(service=service_name).set(42.0)

    @app.middleware("http")
    async def telemetry_middleware(request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", f"req_{uuid.uuid4().hex[:10]}")
        start_time = time.perf_counter()

        endpoint = request.url.path
        method = request.method

        # Bind contextvars
        structlog.contextvars.clear_contextvars()
        structlog.contextvars.bind_contextvars(
            request_id=request_id,
            service=service_name,
            endpoint=endpoint,
            method=method,
        )

        status_code = 500
        try:
            response = await call_next(request)
            status_code = response.status_code
            return response
        except Exception as exc:
            ERRORS_TOTAL.labels(
                service=service_name, error_type=type(exc).__name__
            ).inc()
            logger.error("unhandled_exception", error=str(exc))
            raise
        finally:
            duration = time.perf_counter() - start_time
            REQUEST_LATENCY.labels(service=service_name, endpoint=endpoint).observe(
                duration
            )
            REQUESTS_TOTAL.labels(
                service=service_name,
                method=method,
                endpoint=endpoint,
                status=str(status_code),
            ).inc()

            # Update memory gauge periodically
            try:
                proc = psutil.Process(os.getpid())
                MEMORY_MB.labels(service=service_name).set(
                    proc.memory_info().rss / (1024 * 1024)
                )
            except (psutil.Error, OSError):
                pass

            log_method = (
                logger.info
                if status_code < 400
                else (logger.warning if status_code < 500 else logger.error)
            )
            log_method(
                "http_request_complete",
                status=status_code,
                duration_ms=round(duration * 1000, 2),
            )

    @app.get("/metrics")
    def metrics_endpoint():
        return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)

    return logger
