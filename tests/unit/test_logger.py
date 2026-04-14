import logging
from utils.logger import get_logger


def test_logger_returns_named_logger():
    logger = get_logger("test_component")
    assert logger.name == "test_component"
    assert logger.level <= logging.INFO


def test_logger_emits_formatted_message(caplog):
    logger = get_logger("trendyol")
    with caplog.at_level(logging.INFO, logger="trendyol"):
        logger.info("Test mesaj")
    assert "Test mesaj" in caplog.text
    assert "trendyol" in caplog.text


def test_logger_reused_for_same_name():
    a = get_logger("same")
    b = get_logger("same")
    assert a is b
