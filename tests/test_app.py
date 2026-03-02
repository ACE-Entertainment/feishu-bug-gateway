from io import BytesIO

import pytest

from general_bug_report.app import create_app
from general_bug_report.settings import Settings


@pytest.fixture
def settings(tmp_path):
    return Settings(
        port=20404,
        upload_root=tmp_path,
        max_bytes=6 * 1024 * 1024,
        allowed_log_ext={".log", ".zip", ".txt"},
        allowed_save_ext={".zip", ".sav"},
        allowed_img_ext={".jpg", ".jpeg", ".png"},
        allowed_files_ext={".zip"},
        default_webhook="",
        default_app_id="",
        default_app_secret="",
        default_bitable_app_token="",
        default_bitable_table_id="",
        default_bitable_parent_node="",
        default_fields_map={
            "bug_title": "Bug Title",
            "version": "Version",
            "bug_type": "Bug Type",
            "stable": "Stable",
            "player_id": "Player",
            "hardware": "Hardware",
            "name": "Name",
            "contact": "Contact",
            "description": "Description",
            "received": "Upload Time",
            "category": "Category",
            "files": "Files",
            "screenshot": "Screenshot",
        },
        default_constants={"category_value": "Bug"},
        projects={"demo": {"bitable": {}}},
    )


@pytest.fixture
def client(settings):
    app = create_app(settings)
    app.config["TESTING"] = True
    return app.test_client()


def test_missing_required_field(client):
    resp = client.post("/demo", data={})
    assert resp.status_code == 400
    assert resp.get_json()["status"] == "fail"


def test_requires_save_file_when_no_files_bundle(client):
    data = {
        "bug_title": "t",
        "player_id": "p",
        "hardware": "h",
        "type": "bug",
        "version": "1.0",
        "log_file": (BytesIO(b"hello"), "player.log"),
    }
    resp = client.post("/demo", data=data, content_type="multipart/form-data")
    assert resp.status_code == 400
    assert "save_file" in resp.get_json()["message"]


def test_accepts_files_bundle(client):
    data = {
        "bug_title": "t",
        "player_id": "p",
        "hardware": "h",
        "type": "bug",
        "version": "1.0",
        "files": (BytesIO(b"PK\x03\x04"), "bundle.zip"),
    }
    resp = client.post("/demo", data=data, content_type="multipart/form-data")
    assert resp.status_code == 200
    body = resp.get_json()
    assert body["status"] == "success"
    assert body["project"] == "demo"
