from __future__ import annotations

import json
import logging
import os
import time
import zipfile
from pathlib import Path

import lark_oapi as lark
import requests
from lark_oapi.api.drive.v1 import UploadAllMediaRequest, UploadAllMediaRequestBody, UploadAllMediaResponse
from PIL import Image


def compress_image_to_jpg(src_path: Path, quality: int = 69) -> Path:
    try:
        with Image.open(src_path) as img:
            if img.mode != "RGB":
                img = img.convert("RGB")
            dst_path = src_path.with_suffix(".jpg")
            img.save(dst_path, "JPEG", optimize=True, quality=quality)
        if dst_path.exists():
            src_path.unlink(missing_ok=True)
        return dst_path
    except Exception as e:
        logging.exception("compress_image_to_jpg failed: %s", e)
        return src_path


def tenant_token(app_id: str, app_secret: str) -> str:
    url = "https://open.feishu.cn/open-apis/auth/v3/tenant_access_token/internal"
    r = requests.post(url, json={"app_id": app_id, "app_secret": app_secret}, timeout=10)
    j = r.json()
    if j.get("code") != 0:
        raise RuntimeError(f"get tenant token failed: {j}")
    return j["tenant_access_token"]


def upload_media(client, file_path: Path, parent_node: str, title: str = "") -> str:
    ext = os.path.splitext(file_path)[1]
    file_name = f"{title[:80]}{ext}" if title else os.path.basename(file_path)
    with open(file_path, "rb") as f:
        request: UploadAllMediaRequest = UploadAllMediaRequest.builder().request_body(
            UploadAllMediaRequestBody.builder()
            .file_name(file_name)
            .parent_type("bitable_file")
            .parent_node(parent_node)
            .size(os.path.getsize(file_path))
            .file(f)
            .build()
        ).build()
        resp: UploadAllMediaResponse = client.drive.v1.media.upload_all(request)
    if resp.code != 0:
        raise RuntimeError(f"upload media failed: {resp.code} {resp.msg}")
    return resp.data.file_token


def build_files_zip(log_path: Path, save_path: Path, dest_dir: Path) -> Path:
    dest_dir.mkdir(parents=True, exist_ok=True)
    zip_path = dest_dir / "files.zip"
    with zipfile.ZipFile(zip_path, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(log_path, arcname=f"log{log_path.suffix}")
        zf.write(save_path, arcname=f"save{save_path.suffix}")
    return zip_path


def bitable_batch_create(token: str, app_token: str, table_id: str, fields_list: list[dict]) -> dict:
    url = f"https://open.feishu.cn/open-apis/bitable/v1/apps/{app_token}/tables/{table_id}/records/batch_create"
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    body = {"records": [{"fields": x} for x in fields_list]}
    r = requests.post(url, headers=headers, data=json.dumps(body), timeout=30)
    j = r.json()
    if j.get("code") != 0:
        raise RuntimeError(f"bitable batch_create failed: {j}")
    return j


def send_error_webhook(webhook: str, project: str, title: str, error_text: str, context: dict | None = None):
    if not webhook:
        logging.error("Webhook not configured for project=%s; skipped webhook error notification", project)
        return
    payload = {
        "msg_type": "post",
        "content": {
            "post": {
                "zh_cn": {
                    "title": f"【{project}】 {title}",
                    "content": [[{"tag": "text", "text": error_text}]]
                    + ([[{"tag": "text", "text": f"context={json.dumps(context, ensure_ascii=False)[:1200]}"}]] if context else []),
                }
            }
        },
    }
    try:
        r = requests.post(webhook, headers={"Content-Type": "application/json"}, data=json.dumps(payload), timeout=15)
        if r.status_code != 200:
            logging.error("error webhook failed: %s %s", r.status_code, r.text)
    except Exception:
        logging.exception("send error webhook exception")


def create_lark_client(app_id: str, app_secret: str):
    return lark.Client.builder().app_id(app_id).app_secret(app_secret).log_level(lark.LogLevel.WARNING).build()
