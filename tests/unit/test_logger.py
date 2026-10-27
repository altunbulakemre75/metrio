import logging
from utils.logger import RedactingFormatter, get_logger


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


def test_formatter_hides_telegram_bot_token():
    record = logging.LogRecord(
        "bot", logging.WARNING, __file__, 1,
        "getUpdates başarısız: /bot123456:ABC-def_789/getUpdates", None, None,
    )
    out = RedactingFormatter("%(message)s").format(record)
    assert "ABC-def_789" not in out
    assert "/bot<gizli>/getUpdates" in out
