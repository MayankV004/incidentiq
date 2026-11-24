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
