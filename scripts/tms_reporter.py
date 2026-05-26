#!/usr/bin/env python3
"""Synchronize pytest JUnit results with a TMS backend.

The script parses JUnit XML, normalizes test outcomes, and sends them to a
REST API in bulk. It is intentionally opinionated at the transport layer and
supports explicit TMS markers like ``@pytest.mark.tms_id("TC-123")``.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import xml.etree.ElementTree as ET
from collections.abc import Sequence
from dataclasses import dataclass
from enum import IntEnum
from pathlib import Path
from typing import Any

import requests
from src.config.settings import settings

TMS_ID_PATTERN = re.compile(r"(TC-[A-Z0-9-]+)")
DEFAULT_TIMEOUT_SECONDS = 30
DEFAULT_RETRIES = 3
DEFAULT_QASE_RESULTS_PATH = "/result/{code}/{id}/bulk"
DEFAULT_QASE_RUN_PATH = "/run/{code}"


class ExitCode(IntEnum):
    """CLI exit codes."""

    SUCCESS = 0
    USAGE_ERROR = 1
    NO_RESULTS = 2
    CONFIG_ERROR = 3
    PARSE_ERROR = 4
    API_ERROR = 5


@dataclass(slots=True)
class TestResult:
    """Normalized test result extracted from JUnit XML."""

    name: str
    nodeid: str
    status: str
    duration: float
    tms_id: str | None = None

    def to_payload(self) -> dict[str, Any]:
        """Convert the result to a JSON-serializable payload."""
        payload: dict[str, Any] = {
            "name": self.name,
            "nodeid": self.nodeid,
            "status": self.status,
            "duration": round(self.duration, 3),
        }
        if self.tms_id:
            payload["tms_id"] = self.tms_id
        return payload


@dataclass(slots=True)
class SyncSummary:
    """Summary of parsed and synced test results."""

    total: int
    mapped: int
    unmapped: int
    passed: int
    failed: int
    skipped: int

    def as_dict(self) -> dict[str, int]:
        """Return a dictionary form for console output."""
        return {
            "total": self.total,
            "mapped": self.mapped,
            "unmapped": self.unmapped,
            "passed": self.passed,
            "failed": self.failed,
            "skipped": self.skipped,
        }


def _extract_tms_id(*candidates: str) -> str | None:
    """Extract a TMS id from pytest name/classname fragments."""
    for candidate in candidates:
        match = TMS_ID_PATTERN.search(candidate.replace("[", " ").replace("]", " "))
        if match:
            return match.group(1)
    return None


def parse_junit_file(path: str | Path) -> list[TestResult]:
    """Parse a single JUnit XML file.

    Args:
        path: Path to the JUnit XML file.

    Returns:
        Normalized test results.
    """
    tree = ET.parse(path)
    root = tree.getroot()
    results: list[TestResult] = []

    for testcase in root.findall(".//testcase"):
        name = testcase.attrib.get("name", "")
        classname = testcase.attrib.get("classname", "")
        nodeid = f"{classname}::{name}" if classname else name
        status = "passed"
        if testcase.find("failure") is not None or testcase.find("error") is not None:
            status = "failed"
        elif testcase.find("skipped") is not None or testcase.find("skip") is not None:
            status = "skipped"

        duration = float(testcase.attrib.get("time", "0") or 0)
        results.append(
            TestResult(
                name=name,
                nodeid=nodeid,
                status=status,
                duration=duration,
                tms_id=_extract_tms_id(name, classname),
            ),
        )

    return results


def parse_junit_dir(directory: str | Path) -> list[TestResult]:
    """Parse all JUnit XML files from a directory tree."""
    all_results: list[TestResult] = []
    for xml_file in sorted(Path(directory).glob("**/*.xml")):
        try:
            all_results.extend(parse_junit_file(xml_file))
        except ET.ParseError as exc:
            print(f"Warning: failed to parse {xml_file}: {exc}", file=sys.stderr)
    return all_results


def _build_summary(results: Sequence[TestResult]) -> SyncSummary:
    """Build a console-friendly summary for parsed results."""
    total = len(results)
    mapped = sum(1 for result in results if result.tms_id)
    unmapped = total - mapped
    passed = sum(1 for result in results if result.status == "passed")
    failed = sum(1 for result in results if result.status == "failed")
    skipped = sum(1 for result in results if result.status == "skipped")
    return SyncSummary(total=total, mapped=mapped, unmapped=unmapped, passed=passed, failed=failed, skipped=skipped)


def _print_summary(summary: SyncSummary) -> None:
    """Print a compact summary to stdout."""
    print(json.dumps(summary.as_dict(), ensure_ascii=False))


def _build_payload(results: Sequence[TestResult]) -> dict[str, Any]:
    """Build request payload for the TMS API."""
    return {
        "results": [
            {
                "status": result.status,
                "comment": json.dumps(result.to_payload(), ensure_ascii=False),
            }
            for result in results
        ],
    }


def _create_run(url: str, headers: dict[str, str], timeout: int) -> int:
    """Create a Qase run and return its numeric id."""
    response = requests.post(
        url,
        json={
            "title": "Automated Playwright run",
            "description": "Created by scripts/tms_reporter.py",
            "is_autotest": True,
        },
        headers=headers,
        timeout=timeout,
    )
    response.raise_for_status()
    data = response.json()
    run_id = (
        data.get("result", {}).get("id")
        or data.get("result", {}).get("run_id")
        or data.get("id")
    )
    if run_id is None:
        raise ValueError(f"Qase run response did not contain an id: {data}")
    return int(run_id)


def _post_with_retry(
    url: str,
    headers: dict[str, str],
    payload: dict[str, Any],
    timeout: int,
    retries: int,
) -> requests.Response:
    """Post payload with simple retry handling for transient failures."""
    last_exc: Exception | None = None
    for attempt in range(1, retries + 1):
        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
            if response.status_code >= 500 and attempt < retries:
                last_exc = requests.HTTPError(f"{response.status_code} Server Error: {response.text}", response=response)
                continue
            response.raise_for_status()
            return response
        except requests.RequestException as exc:
            last_exc = exc
            if attempt >= retries:
                break
    assert last_exc is not None
    raise last_exc


def sync_to_tms(results: list[TestResult], dry_run: bool = False, verbose: bool = False) -> bool:
    """Send normalized test results to the configured TMS backend."""
    tms_api_url = settings.tms_api_url
    tms_token = settings.tms_token
    tms_project_code = getattr(settings, "tms_project_code", "")
    tms_run_id = getattr(settings, "tms_run_id", "")

    if not tms_api_url or not tms_token:
        print("Error: TMS_API_URL and TMS_TOKEN must be configured", file=sys.stderr)
        return False
    if not tms_project_code:
        print("Error: TMS_PROJECT_CODE must be configured", file=sys.stderr)
        return False

    summary = _build_summary(results)
    payload = _build_payload(results)

    if verbose or dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        _print_summary(summary)

    if dry_run:
        print(f"Dry run: {summary.total} test results prepared")
        return True

    headers = {
        "Token": tms_token,
        "Content-Type": "application/json",
    }

    try:
        run_id = int(tms_run_id) if tms_run_id else _create_run(
            f"{tms_api_url.rstrip('/')}{DEFAULT_QASE_RUN_PATH.format(code=tms_project_code)}",
            headers=headers,
            timeout=DEFAULT_TIMEOUT_SECONDS,
        )
        response = _post_with_retry(
            f"{tms_api_url.rstrip('/')}{DEFAULT_QASE_RESULTS_PATH.format(code=tms_project_code, id=run_id)}",
            headers=headers,
            payload=payload,
            timeout=DEFAULT_TIMEOUT_SECONDS,
            retries=DEFAULT_RETRIES,
        )
        print(f"TMS sync completed: {response.status_code}")
        print(f"Synced {summary.mapped}/{summary.total} mapped test results")
        return True
    except requests.RequestException as exc:
        print(f"TMS sync failed: {exc}", file=sys.stderr)
        return False


def build_parser() -> argparse.ArgumentParser:
    """Build command-line parser."""
    parser = argparse.ArgumentParser(description="Sync JUnit XML results to TMS")
    parser.add_argument("--junit", type=str, help="Path to a single JUnit XML file")
    parser.add_argument("--junit-dir", type=str, help="Path to a directory with JUnit XML files")
    parser.add_argument("--dry-run", action="store_true", help="Parse and print payload without POST")
    parser.add_argument("--verbose", action="store_true", help="Print full payload and summary")
    parser.add_argument("--project-code", type=str, default="", help="Qase project code")
    parser.add_argument("--run-id", type=str, default="", help="Qase run id")
    return parser


def main() -> int:
    """Command-line entry point."""
    args = build_parser().parse_args()

    if not args.junit and not args.junit_dir:
        print("Error: specify either --junit or --junit-dir", file=sys.stderr)
        return ExitCode.USAGE_ERROR

    try:
        results = parse_junit_file(args.junit) if args.junit else parse_junit_dir(args.junit_dir)
    except (FileNotFoundError, ET.ParseError) as exc:
        print(f"Error: failed to parse JUnit file(s): {exc}", file=sys.stderr)
        return ExitCode.PARSE_ERROR

    if not results:
        print("No test results found", file=sys.stderr)
        return ExitCode.NO_RESULTS

    if not settings.tms_api_url or not settings.tms_token:
        print("Error: TMS_API_URL and TMS_TOKEN must be configured", file=sys.stderr)
        return ExitCode.CONFIG_ERROR

    if args.project_code:
        settings.tms_project_code = args.project_code
    if args.run_id:
        settings.tms_run_id = args.run_id

    return ExitCode.SUCCESS if sync_to_tms(results, dry_run=args.dry_run, verbose=args.verbose) else ExitCode.API_ERROR


if __name__ == "__main__":
    sys.exit(main())
