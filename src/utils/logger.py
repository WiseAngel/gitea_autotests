"""
Модуль централизованного логирования.

Предоставляет единый интерфейс для логирования событий в приложении.
Поддерживает различные уровни логирования и вывод в консоль/файл.
"""

import logging
import sys
from pathlib import Path


def setup_logger(
    name: str = "playwright_qa",
    level: int = logging.INFO,
    log_file: str | None = None,
    format_string: str | None = None,
) -> logging.Logger:
    """
    Настроить и вернуть экземпляр логгера.

    Args:
        name: Имя логгера (обычно __name__ модуля).
        level: Уровень логирования (DEBUG, INFO, WARNING, ERROR, CRITICAL).
        log_file: Путь к файлу для записи логов (опционально).
        format_string: Кастомный формат строки лога.

    Returns:
        Настроенный экземпляр logging.Logger.

    Example:
        >>> logger = setup_logger(__name__)
        >>> logger.info("Приложение запущено")
    """
    logger = logging.getLogger(name)
    logger.setLevel(level)

    # Если логгер уже настроен, не настраиваем повторно
    if logger.handlers:
        return logger

    # Формат по умолчанию
    if format_string is None:
        format_string = "%(asctime)s | %(levelname)-8s | %(name)s:%(lineno)d | %(message)s"

    formatter = logging.Formatter(format_string, datefmt="%Y-%m-%d %H:%M:%S")

    # Консольный обработчик
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(level)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Файловый обработчик (если указан)
    if log_file:
        log_path = Path(log_file)
        log_path.parent.mkdir(parents=True, exist_ok=True)
        file_handler = logging.FileHandler(log_file, encoding="utf-8")
        file_handler.setLevel(level)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)

    return logger


# Глобальный логгер по умолчанию
default_logger = setup_logger()


def get_logger(name: str) -> logging.Logger:
    """
    Получить логгер с указанным именем, используя базовые настройки.

    Args:
        name: Имя логгера (обычно __name__ модуля).

    Returns:
        Экземпляр logging.Logger.
    """
    return setup_logger(name)
