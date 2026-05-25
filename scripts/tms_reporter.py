#!/usr/bin/env python3
"""
TMS Reporter — синхронизация результатов тестов с внешней TMS через REST API.

Парсит JUnit XML файлы из CI и отправляет статусы тестов в TMS систему.
Маппинг тестов осуществляется через pytest.mark.tms_id("TC-XXX").

Usage:
    python scripts/tms_reporter.py --junit-dir artifacts/
    python scripts/tms_reporter.py --junit test-results-shard-1.xml

Environment Variables:
    TMS_API_URL: Базовый URL TMS API (например, https://tms.example.com)
    TMS_TOKEN: Токен авторизации для доступа к API
"""

import argparse
import sys
from pathlib import Path

import requests
from src.config.settings import settings


def parse_junit_file(path: str) -> list[dict]:
    """
    Парсинг одного JUnit XML файла.

    Args:
        path: Путь к JUnit XML файлу

    Returns:
        Список словарей с результатами тестов:
        [{"name": "...", "status": "passed|failed|skipped", "tms_id": "TC-XXX"}, ...]

    Raises:
        FileNotFoundError: Если файл не найден
        ET.ParseError: Если XML невалидный
    """
    import xml.etree.ElementTree as ET

    tree = ET.parse(path)
    root = tree.getroot()
    results = []

    for testcase in root.findall(".//testcase"):
        # Извлекаем tms_id из имени теста или classname
        tms_id = None
        name = testcase.attrib.get("name", "")
        classname = testcase.attrib.get("classname", "")

        # Пробуем найти tms_id в формате test_name[tms_id-TC-123]
        import re

        match = re.search(r"\[tms_id-(TC-\d+)\]", name)
        if not match:
            match = re.search(r"\[tms_id-(TC-\d+)\]", classname)
        if match:
            tms_id = match.group(1)

        # Определяем статус
        status = "passed"
        if testcase.find("failure") is not None:
            status = "failed"
        elif testcase.find("skipped") is not None or testcase.find("skip") is not None:
            status = "skipped"

        result = {"name": name, "status": status}
        if tms_id:
            result["tms_id"] = tms_id

        results.append(result)

    return results


def parse_junit_dir(directory: str) -> list[dict]:
    """
    Парсинг всех JUnit XML файлов в директории.

    Args:
        directory: Путь к директории с JUnit XML файлами

    Returns:
        Объединённый список результатов всех тестов
    """
    all_results = []
    dir_path = Path(directory)

    for xml_file in dir_path.glob("**/test-results*.xml"):
        print(f"Parsing: {xml_file}")
        try:
            results = parse_junit_file(str(xml_file))
            all_results.extend(results)
        except Exception as e:
            print(f"Warning: Failed to parse {xml_file}: {e}")

    return all_results


def sync_to_tms(results: list[dict]) -> bool:
    """
    Отправка результатов тестов в TMS систему.

    Args:
        results: Список результатов тестов

    Returns:
        True если синхронизация успешна, False иначе

    Raises:
        requests.RequestException: При ошибке сети
        ValueError: Если переменные окружения не настроены
    """
    tms_api_url = settings.tms_api_url
    tms_token = settings.tms_token

    if not tms_api_url or not tms_token:
        print("Error: TMS API settings are required")
        return False

    payload = {"test_results": results}
    headers = {
        "Authorization": f"Bearer {tms_token}",
        "Content-Type": "application/json",
    }

    try:
        resp = requests.post(f"{tms_api_url}/api/v1/results", json=payload, headers=headers, timeout=30)
        resp.raise_for_status()
        print(f"TMS sync completed: {resp.status_code}")
        print(f"Synced {len(results)} test results")
        return True
    except requests.RequestException as e:
        print(f"TMS sync failed: {e}")
        return False


def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Sync test results from JUnit XML to TMS")
    parser.add_argument("--junit", type=str, help="Path to single JUnit XML file")
    parser.add_argument("--junit-dir", type=str, help="Path to directory with JUnit XML files")
    args = parser.parse_args()

    if not args.junit and not args.junit_dir:
        print("Error: Specify either --junit or --junit-dir")
        return 1

    results = []
    if args.junit:
        print(f"Parsing single file: {args.junit}")
        results = parse_junit_file(args.junit)
    elif args.junit_dir:
        print(f"Parsing directory: {args.junit_dir}")
        results = parse_junit_dir(args.junit_dir)

    if not results:
        print("No test results found")
        return 0

    success = sync_to_tms(results)
    return 0 if success else 1


if __name__ == "__main__":
    sys.exit(main())
