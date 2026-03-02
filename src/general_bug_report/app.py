from __future__ import annotations

import logging
import os
import re
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from flask import Flask, jsonify, request
from werkzeug.utils import secure_filename

from .services import (
    bitable_batch_create,
    build_bundle_zip,
    compress_image_to_jpg,
    create_lark_client,
    send_error_webhook,
    tenant_token,
    upload_media,
)
from .settings import Settings, load_settings, validate_settings

LOG_FILE = "error_bugreport.log"
PROJECT_RE = re.compile(r"^[a-z0-9_-]{1,20}$")


def create_app(settings: Settings | None = None) -> Flask:
    logging.basicConfig(filename=LOG_FILE, level=logging.ERROR, format="%(asctime)s - %(levelname)s - %(message)s")
    cfg = settings or load_settings()
    validate_settings(cfg)
    executor = ThreadPoolExecutor(max_workers=3)

    app = Flask(__name__)
    app.config["SETTINGS"] = cfg

    def project_cfg(project: str) -> dict:
        return cfg.projects.get(project, {}) or {}

    def fields_map_for(project: str) -> dict:
        fmap = dict(cfg.default_fields_map)
        fmap.update(project_cfg(project).get("fields_override", {}) or {})
        return fmap

    def consts_for(project: str) -> dict:
        consts = dict(cfg.default_constants)
        consts.update(project_cfg(project).get("constants_override", {}) or {})
        return consts

    def bitable_cfg(project: str) -> dict:
        proj = project_cfg(project).get("bitable", {}) or {}
        return {
            "app_id": proj.get("app_id", cfg.default_app_id),
            "app_secret": proj.get("app_secret", cfg.default_app_secret),
            "app_token": proj.get("app_token", cfg.default_bitable_app_token),
            "table_id": proj.get("table_id", cfg.default_bitable_table_id),
            "parent_node": proj.get("parent_node", cfg.default_bitable_parent_node),
        }

    def webhook_for(project: str) -> str:
        return project_cfg(project).get("webhook", cfg.default_webhook)

    def validate_project(project: str):
        if project not in cfg.projects:
            raise ValueError(f"Unknown project: {project}")

    def file_size(fs) -> int:
        pos = fs.stream.tell()
        fs.stream.seek(0, os.SEEK_END)
        size = fs.stream.tell()
        fs.stream.seek(pos, os.SEEK_SET)
        return size

    def save_upload(file_storage, project: str, subdir: str, allowed_ext: set[str], job_id: str) -> Path:
        if not file_storage or not file_storage.filename:
            raise ValueError("Missing file")
        size = file_size(file_storage)
        if size <= 0 or size > cfg.max_bytes:
            raise ValueError(f"{subdir} file size must be between 1B and {cfg.max_bytes} bytes")
        ext = Path(file_storage.filename).suffix.lower()
        if ext not in allowed_ext:
            raise ValueError(f"Unsupported file extension: {ext}")
        safe_name = secure_filename(f"{uuid.uuid4().hex}{ext}")
        dest_dir = cfg.upload_root / project / job_id / subdir
        dest_dir.mkdir(parents=True, exist_ok=True)
        dest_path = dest_dir / safe_name
        file_storage.save(dest_path)
        return dest_path

    def build_fields(project: str, payload: dict, file_tokens: dict) -> dict:
        fmap = fields_map_for(project)
        consts = consts_for(project)
        fields = {
            fmap["bug_title"]: payload.get("bug_title", ""),
            fmap["version"]: payload.get("version", ""),
            fmap["bug_type"]: payload.get("bug_type", ""),
            fmap["stable"]: payload.get("isStableReproducible", ""),
            fmap["player_id"]: payload.get("player_id", ""),
            fmap["hardware"]: payload.get("hardware", ""),
            fmap["name"]: payload.get("name", ""),
            fmap["contact"]: payload.get("contact", ""),
            fmap["description"]: payload.get("description", ""),
            fmap["received"]: payload.get("upload_time", "") or "",
            fmap["category"]: payload.get("category", consts.get("category_value", "")),
        }
        if file_tokens.get("files") and fmap.get("files"):
            fields[fmap["files"]] = [{"file_token": file_tokens["files"]}]
        if file_tokens.get("screenshot") and fmap.get("screenshot"):
            fields[fmap["screenshot"]] = [{"file_token": file_tokens["screenshot"]}]
        return fields

    def process_job(project, job_id, bug_title, player_id, hardware, bug_type, version, description, name, contact, is_stable, img_path, files_path):
        try:
            if img_path:
                img_path = compress_image_to_jpg(img_path)
            bit = bitable_cfg(project)
            if not all([bit.get(k) for k in ("app_id", "app_secret", "app_token", "table_id", "parent_node")]):
                raise RuntimeError("Incomplete bitable config")

            token = tenant_token(bit["app_id"], bit["app_secret"])
            client = create_lark_client(bit["app_id"], bit["app_secret"])

            files_token = upload_media(client, files_path, bit["parent_node"], bug_title)

            file_tokens = {"files": files_token}
            if img_path:
                time.sleep(0.3)
                file_tokens["screenshot"] = upload_media(client, img_path, bit["parent_node"], bug_title)

            payload = {
                "bug_title": bug_title,
                "version": version,
                "bug_type": bug_type,
                "isStableReproducible": is_stable,
                "player_id": player_id,
                "hardware": hardware,
                "name": name,
                "contact": contact,
                "description": description,
                "upload_time": int(time.time() * 1000),
            }
            fields = build_fields(project, payload, file_tokens)
            bitable_batch_create(token, bit["app_token"], bit["table_id"], [fields])
        except Exception as e:
            logging.exception("background job error: %s", e)
            send_error_webhook(
                webhook_for(project),
                project,
                "Bug report failed in background worker",
                f"{type(e).__name__}: {e}",
                {"job_id": job_id, "player_id": player_id},
            )

    @app.route("/healthz", methods=["GET"])
    def healthz():
        return "ok", 200

    @app.route("/<project>", methods=["POST"])
    def upload_data(project: str):
        try:
            validate_project(project)
            bug_title = request.form.get("bug_title", "")
            player_id = request.form.get("player_id") or request.form.get("steam_id") or ""
            hardware = request.form.get("hardware", "")
            bug_type = request.form.get("type", "")
            version = request.form.get("version", "")

            if not bug_title:
                return jsonify({"status": "fail", "message": "bug_title is required"}), 400
            if not player_id:
                return jsonify({"status": "fail", "message": "player_id is required"}), 400
            if not hardware:
                return jsonify({"status": "fail", "message": "hardware is required"}), 400
            if not bug_type:
                return jsonify({"status": "fail", "message": "type is required"}), 400
            if not version:
                return jsonify({"status": "fail", "message": "version is required"}), 400

            description = request.form.get("description", "")
            name = request.form.get("name", "")
            contact = request.form.get("contact", request.form.get("email", ""))
            is_stable = request.form.get("isStableReproducible", "")
            job_id = uuid.uuid4().hex

            files_uploads = [fs for fs in request.files.getlist("files") if fs and fs.filename]
            extra_uploads = []

            log_file = request.files.get("log_file")
            if log_file and log_file.filename:
                extra_uploads.append((log_file, "log"))

            save_file = request.files.get("save_file")
            if save_file and save_file.filename:
                extra_uploads.append((save_file, "save"))

            if not files_uploads and not extra_uploads:
                return jsonify({"status": "fail", "message": "files is required"}), 400

            if len(files_uploads) == 1 and not extra_uploads:
                files_path = save_upload(files_uploads[0], project, "files", cfg.allowed_files_ext, job_id)
            else:
                bundle_files = []
                for idx, fs in enumerate(files_uploads):
                    p = save_upload(fs, project, "attachments", cfg.allowed_files_ext, job_id)
                    bundle_files.append((p, f"files_{idx + 1}{p.suffix}"))
                for fs, prefix in extra_uploads:
                    allowed_ext = cfg.allowed_log_ext if prefix == "log" else cfg.allowed_save_ext
                    p = save_upload(fs, project, "attachments", allowed_ext, job_id)
                    bundle_files.append((p, f"{prefix}{p.suffix}"))
                files_path = build_bundle_zip(bundle_files, cfg.upload_root / project / job_id / "files")

            img_file = request.files.get("image")
            img_path = save_upload(img_file, project, "images", cfg.allowed_img_ext, job_id) if img_file and img_file.filename else None

            executor.submit(
                process_job,
                project,
                job_id,
                bug_title,
                player_id,
                hardware,
                bug_type,
                version,
                description,
                name,
                contact,
                is_stable,
                img_path,
                files_path,
            )
            return jsonify({"status": "success", "project": project, "job_id": job_id}), 200
        except ValueError as e:
            return jsonify({"status": "fail", "message": str(e)}), 400
        except Exception as e:
            logging.exception("upload_data error: %s", e)
            if PROJECT_RE.match(project or ""):
                send_error_webhook(webhook_for(project), project, "Bug report failed in handler", f"{type(e).__name__}: {e}")
            return jsonify({"status": "success", "message": "ok"}), 200

    return app
