"""Milestone 3 tests verifying local web UI serving, required screens, and accessibility markers."""

from __future__ import annotations

from pathlib import Path

from fastapi.testclient import TestClient

from app.core.config import Settings
from app.main import create_app


def _client(tmp_path: Path) -> TestClient:
    cfg = Settings(
        environment="test",
        data_dir=tmp_path / "data",
        model_dir=tmp_path / "models",
    )
    return TestClient(create_app(settings=cfg))


def test_frontend_served_from_root_and_assets(tmp_path: Path) -> None:
    client = _client(tmp_path)

    index_res = client.get("/")
    assert index_res.status_code == 200
    assert "text/html" in index_res.headers["content-type"]
    html = index_res.text

    # All 7 required screens present
    for view_id in (
        "view-dashboard",
        "view-voices",
        "view-create-voice",
        "view-studio",
        "view-preview",
        "view-history",
        "view-settings",
    ):
        assert f'id="{view_id}"' in html

    # Key WCAG 2.2 accessibility & RTL markers present
    assert 'class="skip-link"' in html
    assert 'aria-live="polite"' in html
    assert 'for="ownership-checkbox"' in html
    assert 'for="studio-text-input"' in html
    assert 'dir="auto"' in html

    css_res = client.get("/assets/styles.css")
    assert css_res.status_code == 200
    assert ":focus-visible" in css_res.text

    js_res = client.get("/assets/app.js")
    assert js_res.status_code == 200
    assert "/api/v1/voices/import" in js_res.text
