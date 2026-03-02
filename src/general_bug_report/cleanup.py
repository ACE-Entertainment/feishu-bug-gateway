from __future__ import annotations

import logging
import os
import shutil
import time
from pathlib import Path

from .settings import load_settings

RETENTION_DAYS = 30
KEEP_PER_PROJECT = 60
MAX_TOTAL_GB_GLOBAL = 1
MAX_TOTAL_GB_PER_PROJECT = {}
ONLY_PROJECTS = None
DRY_RUN = False
LOG_FILE = "cleanup.log"
UUID_HEX_32 = set("0123456789abcdef")


def is_uuid_hex(s: str) -> bool:
    return len(s) == 32 and all(c in UUID_HEX_32 for c in s.lower())


def dir_latest_mtime(p: Path) -> float:
    latest = p.stat().st_mtime
    for root, dirs, files in os.walk(p, topdown=True, followlinks=False):
        for n in files + dirs:
            try:
                t = (Path(root) / n).stat().st_mtime
                if t > latest:
                    latest = t
            except FileNotFoundError:
                continue
    return latest


def dir_size_bytes(p: Path) -> int:
    total = 0
    for root, _, files in os.walk(p, topdown=True, followlinks=False):
        for n in files:
            try:
                total += (Path(root) / n).stat().st_size
            except FileNotFoundError:
                continue
    return total


def safe_rmtree(p: Path):
    if not DRY_RUN:
        shutil.rmtree(p, ignore_errors=True)


def cleanup() -> None:
    settings = load_settings()
    base = settings.upload_root.resolve()
    base.mkdir(parents=True, exist_ok=True)

    logging.basicConfig(filename=LOG_FILE, level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
    cutoff = time.time() - RETENTION_DAYS * 86400
    allowed = set(settings.projects.keys())
    projects = (ONLY_PROJECTS or allowed) & allowed

    for project in sorted(projects):
        proj_dir = base / project
        if not proj_dir.exists() or not proj_dir.is_dir():
            continue

        jobs = []
        for child in proj_dir.iterdir():
            if child.is_dir() and is_uuid_hex(child.name):
                jobs.append((child, dir_latest_mtime(child)))

        jobs.sort(key=lambda x: x[1], reverse=True)
        protected = {j[0] for j in jobs[: max(0, KEEP_PER_PROJECT)]}

        for path, mtime in jobs[max(0, KEEP_PER_PROJECT) :]:
            if mtime < cutoff:
                safe_rmtree(path)

        limit_gb = MAX_TOTAL_GB_PER_PROJECT.get(project, MAX_TOTAL_GB_GLOBAL)
        if limit_gb and limit_gb > 0:
            limit_bytes = int(limit_gb * (1024**3))
            remaining = [(c, dir_latest_mtime(c)) for c in proj_dir.iterdir() if c.is_dir() and is_uuid_hex(c.name)]
            remaining.sort(key=lambda x: x[1], reverse=True)
            cur = dir_size_bytes(proj_dir)
            while cur > limit_bytes and remaining:
                victim, _ = remaining.pop()
                if victim in protected:
                    continue
                size = dir_size_bytes(victim)
                safe_rmtree(victim)
                cur -= size


if __name__ == "__main__":
    cleanup()
    print(f"Cleanup finished. See log: {LOG_FILE} (DRY_RUN={DRY_RUN})")
