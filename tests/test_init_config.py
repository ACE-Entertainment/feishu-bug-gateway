from general_bug_report.init_config import _default_upload_root, render_config


def test_render_config_contains_values():
    cfg = render_config(
        upload_root="/tmp/uploads",
        max_bytes=123,
        project_name="prod",
        webhook="https://example.com/hook",
        app_id="cli_123",
        app_secret="secret",
        app_token="bascn_123",
        table_id="tbl_123",
        parent_node="fldr_123",
    )

    assert 'UPLOAD_ROOT = "/tmp/uploads"' in cfg
    assert "MAX_BYTES = 123" in cfg
    assert '"prod": {' in cfg
    assert 'DEFAULT_APP_ID = "cli_123"' in cfg


def test_default_upload_root_uses_project_name():
    assert _default_upload_root("oasis") == "./uploads/oasis"
