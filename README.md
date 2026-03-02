# general_bug_report

A Flask API to receive bug reports with files, then asynchronously upload records/files to Feishu Bitable.

## Features

- `POST /<project>` API with validation.
- Two upload modes:
  - `files` (single archive).
  - `log_file + save_file` (server zips them before Feishu upload).
- Optional screenshot compression (JPG).
- Async background worker to avoid blocking clients.
- Cleanup utility for expired upload folders.

## Quick Start

1. Install:

```bash
pip install -e .
```

2. Configure:

方式 A（手动）：

```bash
cp config.example.py config.py
# then edit config.py with your own Feishu values
```

方式 B（交互向导，推荐新手）：

```bash
general-bug-report-init-config
# 按提示一步步输入，会自动生成 config.py
# 其中 UPLOAD_ROOT 默认是 ./uploads/<project_name>
```

关键配置项：

- `PROJECTS`: 项目路由与每个项目的飞书配置（必填）
- `DEFAULT_APP_ID` / `DEFAULT_APP_SECRET`: 飞书应用凭证（可作为默认值）
- `DEFAULT_BITABLE_APP_TOKEN` / `DEFAULT_BITABLE_TABLE_ID` / `DEFAULT_BITABLE_PARENT_NODE`: 多维表格写入目标（可作为默认值）
- `DEFAULT_WEBHOOK`: 异常告警 webhook（推荐）
- `UPLOAD_ROOT`: 文件落盘目录
- `MAX_BYTES`: 单文件大小限制

3. Run:

```bash
python -m general_bug_report
```

4. Health check:

```bash
curl http://127.0.0.1:40404/healthz
```

## API

### `POST /<project>`

**Required form fields**

- `bug_title`
- `player_id` or `steam_id`
- `hardware`
- `type`
- `version`

**Optional form fields**

- `description`
- `name`
- `contact` or `email`
- `isStableReproducible`

**Required files** (choose one mode)

- Mode A: `files` (default `.zip`)
- Mode B: `log_file` + `save_file`

**Optional files**

- `image` (`.jpg/.jpeg/.png`)

### Response

- `200`: `{ "status": "success", "project": "...", "job_id": "..." }`
- `400`: `{ "status": "fail", "message": "..." }`

> Note: success means request accepted. Feishu upload happens asynchronously.

## Example request (curl)

```bash
curl -X POST "http://127.0.0.1:40404/demo" \
  -F bug_title="Crash while saving" \
  -F player_id="123456" \
  -F hardware="CPU i7, RTX 3070" \
  -F type="Crash" \
  -F version="1.0.0" \
  -F description="Steps to reproduce..." \
  -F log_file=@Player.log \
  -F save_file=@save_data.zip
```

## Example request (Python)

```python
import requests

url = "http://127.0.0.1:40404/demo"

with open("Player.log", "rb") as log_file, open("save_data.zip", "rb") as save_file:
    files = {
        "log_file": ("Player.log", log_file),
        "save_file": ("save_data.zip", save_file),
    }
    data = {
        "bug_title": "Crash while saving",
        "player_id": "123456",
        "hardware": "CPU i7, RTX 3070",
        "type": "Crash",
        "version": "1.0.0",
        "description": "Steps to reproduce...",
    }

    response = requests.post(url, files=files, data=data, timeout=20)
    print(response.status_code, response.text)
```

## Cleanup

```bash
python -m general_bug_report.cleanup
```

## Data retention and security recommendations

- Run behind HTTPS reverse proxy.
- Set request size limit in Nginx (`client_max_body_size`).
- Keep `config.py` out of version control.
- Regularly run cleanup and define retention policy.

## Development

```bash
pip install -e .[dev]
pytest
```
