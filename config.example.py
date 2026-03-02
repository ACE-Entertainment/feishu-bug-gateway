"""Copy this file to config.py and fill your own values.
Never commit config.py with real secrets.
"""

UPLOAD_ROOT = "./uploads"
MAX_BYTES = 6 * 1024 * 1024

ALLOWED_LOG_EXT = {".log", ".zip", ".txt"}
ALLOWED_SAVE_EXT = {".zip", ".sav"}
ALLOWED_IMG_EXT = {".jpg", ".jpeg", ".png"}
ALLOWED_FILES_EXT = {".zip"}

DEFAULT_WEBHOOK = "https://open.feishu.cn/open-apis/bot/v2/hook/replace-me"
DEFAULT_APP_ID = "cli_xxx"
DEFAULT_APP_SECRET = "replace-me"
DEFAULT_BITABLE_APP_TOKEN = "bascn_xxx"
DEFAULT_BITABLE_TABLE_ID = "tbl_xxx"
DEFAULT_BITABLE_PARENT_NODE = "fldr_xxx"

DEFAULT_FIELDS_MAP = {
    "bug_title": "Bug Title",
    "version": "Version",
    "bug_type": "Bug Type",
    "stable": "Stable Reproducible",
    "player_id": "Player ID",
    "hardware": "Hardware",
    "name": "Name",
    "contact": "Contact",
    "description": "Description",
    "received": "Upload Time",
    "category": "Category",
    "files": "Files",
    "screenshot": "Screenshot",
}

DEFAULT_CONSTANTS = {"category_value": "Bug"}

PROJECTS = {
    "demo": {
        "webhook": DEFAULT_WEBHOOK,
        "bitable": {
            "app_id": DEFAULT_APP_ID,
            "app_secret": DEFAULT_APP_SECRET,
            "app_token": DEFAULT_BITABLE_APP_TOKEN,
            "table_id": DEFAULT_BITABLE_TABLE_ID,
            "parent_node": DEFAULT_BITABLE_PARENT_NODE,
        },
        "fields_override": {},
        "constants_override": {},
    }
}
