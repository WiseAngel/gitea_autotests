from __future__ import annotations

from pathlib import Path

import pytest
from scripts import tms_reporter


def _write_junit_file(path: Path) -> None:
    path.write_text(
        """<?xml version="1.0" encoding="utf-8"?>
<testsuite tests="3">
  <testcase classname="tests.e2e.test_gitea_ui[tms_id-TC-E2E-001]" name="test_public_homepage_links_to_login"/>
  <testcase classname="tests.integration.test_gitea_api" name="test_authenticated_repo_lifecycle">
    <failure message="boom">boom</failure>
  </testcase>
  <testcase classname="tests.components.test_gitea_helpers" name="test_build_auth_headers_uses_gitea_token_scheme">
    <skipped />
  </testcase>
</testsuite>
""",
        encoding="utf-8",
    )


def test_extract_tms_id_from_name_or_classname() -> None:
    assert tms_reporter._extract_tms_id("test_name[tms_id-TC-123]", "module") == "TC-123"
    assert tms_reporter._extract_tms_id("test_name", "module[tms_id-TC-456]") == "TC-456"
    assert tms_reporter._extract_tms_id("test_name", "module") is None


def test_parse_junit_file_extracts_status_and_tms_id(tmp_path: Path) -> None:
    junit_path = tmp_path / "report.xml"
    _write_junit_file(junit_path)

    results = tms_reporter.parse_junit_file(junit_path)

    assert [result.status for result in results] == ["passed", "failed", "skipped"]
    assert results[0].tms_id == "TC-E2E-001"
    assert results[0].nodeid == "tests.e2e.test_gitea_ui[tms_id-TC-E2E-001]::test_public_homepage_links_to_login"
    assert results[0].duration == 0
    assert results[1].tms_id is None
    assert results[2].tms_id is None


def test_parse_junit_dir_collects_xml_files(tmp_path: Path) -> None:
    first = tmp_path / "one.xml"
    second_dir = tmp_path / "nested"
    second_dir.mkdir()
    second = second_dir / "two.xml"
    _write_junit_file(first)
    _write_junit_file(second)

    results = tms_reporter.parse_junit_dir(tmp_path)

    assert len(results) == 6


def test_sync_to_tms_dry_run_returns_true(monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]) -> None:
    monkeypatch.setattr(tms_reporter.settings, "tms_api_url", "https://qase.io/v1")
    monkeypatch.setattr(tms_reporter.settings, "tms_token", "token")
    monkeypatch.setattr(tms_reporter.settings, "tms_project_code", "GITEA")
    monkeypatch.setattr(tms_reporter.settings, "tms_run_id", "1")

    ok = tms_reporter.sync_to_tms(
        [tms_reporter.TestResult(name="test", nodeid="module::test", status="passed", duration=1.234)],
        dry_run=True,
    )

    captured = capsys.readouterr()
    assert ok is True
    assert "Dry run" in captured.out
    assert '"status": "passed"' in captured.out


def test_sync_to_tms_posts_payload_and_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tms_reporter.settings, "tms_api_url", "https://qase.io/v1")
    monkeypatch.setattr(tms_reporter.settings, "tms_token", "token")
    monkeypatch.setattr(tms_reporter.settings, "tms_project_code", "GITEA")
    monkeypatch.setattr(tms_reporter.settings, "tms_run_id", "42")

    calls: list[str] = []

    class Response:
        status_code = 200

        def raise_for_status(self) -> None:
            return None

    def fake_post(url: str, json: object, headers: dict[str, str], timeout: int) -> Response:
        calls.append(url)
        assert headers["Token"] == "token"
        assert timeout == tms_reporter.DEFAULT_TIMEOUT_SECONDS
        assert "results" in json
        return Response()

    monkeypatch.setattr(tms_reporter.requests, "post", fake_post)

    ok = tms_reporter.sync_to_tms(
        [tms_reporter.TestResult(name="test", nodeid="module::test", status="passed", duration=0.5)],
    )

    assert ok is True
    assert calls == ["https://qase.io/v1/result/GITEA/42/bulk"]


def test_main_returns_config_error_without_tms(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(tms_reporter.settings, "tms_api_url", "")
    monkeypatch.setattr(tms_reporter.settings, "tms_token", "")
    monkeypatch.setattr(tms_reporter.settings, "tms_project_code", "GITEA")
    monkeypatch.setattr(tms_reporter.settings, "tms_run_id", "1")
    monkeypatch.setattr(
        tms_reporter,
        "parse_junit_file",
        lambda path: [tms_reporter.TestResult(name="test", nodeid="module::test", status="passed", duration=0.1)],
    )
    monkeypatch.setattr(tms_reporter.sys, "argv", ["tms_reporter.py", "--junit", "file.xml"])

    assert tms_reporter.main() == tms_reporter.ExitCode.CONFIG_ERROR
