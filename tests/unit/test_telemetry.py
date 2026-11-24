import os
import time

from shop.common.telemetry import configure_logging


def test_telemetry_logging_non_blocking(tmp_path):
    logger = configure_logging("test_service")

    # Log a test message
    logger.info("non_blocking_test_event", test_key="test_value")

    # Give listener thread a brief moment to process
    time.sleep(0.05)

    # Check that log files were created and contains the event
    assert os.path.exists("logs/test_service.log")
    assert os.path.exists("logs/shop.log")

    with open("logs/test_service.log") as f:
        content = f.read()
    assert "non_blocking_test_event" in content


def test_telemetry_multiple_services_isolated():
    logger_a = configure_logging("multi_svc_a")
    logger_b = configure_logging("multi_svc_b")

    logger_a.info("event_from_svc_a")
    logger_b.info("event_from_svc_b")
    time.sleep(0.05)

    with open("logs/multi_svc_a.log") as f:
        content_a = f.read()
    with open("logs/multi_svc_b.log") as f:
        content_b = f.read()

    assert "event_from_svc_a" in content_a
    assert "event_from_svc_b" not in content_a
    assert "event_from_svc_b" in content_b
    assert "event_from_svc_a" not in content_b
