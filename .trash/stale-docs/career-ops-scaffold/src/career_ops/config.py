"""CareerOps MVP — configuração e caminhos."""
from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import yaml

HOME = Path("/home/daviaaze/Projects/pessoal/ai-workspace")
KB_PATH = HOME / "docs/carrer/Kimi_Agent_cv/agente-candidaturas"
CV_MESTRE_PATH = HOME / "docs/carrer/Kimi_Agent_cv/cv-mestre-davi-azevedo.md"
CAREER_OPS_HOME = HOME / "career-ops"
OUTPUT_DIR = CAREER_OPS_HOME / "output"
CANDIDATURAS_DIR = OUTPUT_DIR / "candidaturas"
TRACKER_DB = OUTPUT_DIR / "tracker.db"
CONFIG_PATH = CAREER_OPS_HOME / "config/config.yml"

DEFAULT_CONFIG: dict[str, Any] = {
    "score_threshold": 7,
    "rate_floor_usd": 6000,
    "target_rate_usd": [6000, 8000],
    "rate_hour_usd": [50, 65],
    "timezone": "America/Sao_Paulo",
    "followup_workdays": 5,
    "archive_after_workdays": 12,
    "cron_weekly": "0 8 * * 1",
    "cron_daily": "0 8 * * 1-5",
    "sources": {
        "career_pages": [
            "https://engineco.com/careers",
            "https://hopper.com/careers",
            "https://www.travelperk.com/careers/",
            "https://careers.kiwi.com/",
            "https://www.spotnana.com/careers",
            "https://careers.navan.com/",
            "https://www.zoftify.com/careers",
            "https://www.amtrav.com/careers",
            "https://www.duffel.com/careers",
        ],
        "rss_feeds": [
            "https://hopper.com/careers/rss.xml",
            "https://careers.kiwi.com/rss",
        ],
        "boards_queries": [
            "senior backend node typescript aws remote contractor direct",
            "node serverless remote full-time contractor",
            "travel tech backend engineer remote",
            "GDS integration engineer remote",
        ],
    },
    "notifications": {
        "enabled": True,
        "provider": "smtp",
        "smtp_host": "",
        "smtp_port": 587,
        "smtp_user": "",
        "smtp_password_env": "CAREER_OPS_SMTP_PASSWORD",
        "from_email": "",
        "to_email": "daviaaze@gmail.com",
    },
}


def load_config(path: str | Path | None = None) -> dict[str, Any]:
    cfg = dict(DEFAULT_CONFIG)
    cfg["_kb_path"] = str(KB_PATH)
    cfg["_cv_mestre_path"] = str(CV_MESTRE_PATH)
    cfg["_output_dir"] = str(OUTPUT_DIR)
    cfg["_candidaturas_dir"] = str(CANDIDATURAS_DIR)
    cfg["_tracker_db"] = str(TRACKER_DB)
    cfg["_config_path"] = str(CONFIG_PATH)
    p = Path(path) if path else CONFIG_PATH
    if p.exists():
        with p.open() as f:
            cfg.update(yaml.safe_load(f) or {})
    cfg["_config_path"] = str(p)
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    CANDIDATURAS_DIR.mkdir(parents=True, exist_ok=True)
    return cfg


def kb_file(name: str) -> Path:
    return KB_PATH / name
