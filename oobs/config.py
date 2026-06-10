# -*- coding: utf-8 -*-
"""~/.config/oobs/config.yaml 로드. 없으면 기본값으로 동작."""
import os
from pathlib import Path

import yaml

CONFIG_PATH = Path(os.environ.get("OOBS_CONFIG", "~/.config/oobs/config.yaml")).expanduser()

DEFAULTS = {
    "vault": "~/vault",
    # 노션(nacho) 미러 — oobs 코어는 nacho 없이 완결되며, 미러는 선택적 부가 기능.
    #   auto:  nacho 가 설치돼 있으면 미러, 없으면 조용히 스킵 (기본)
    #   true:  항상 미러 시도, nacho 없으면 경고
    #   false: 미러 안 함
    "mirror": "auto",
    "nacho": {
        "categories": ["리팩토링", "기존기능개선", "신규기능개발", "운영"],
        "projects": ["글로벌 윙크", "한국 윙크"],
    },
}

STATUSES = ["시작 전", "진행 중", "배포 대기", "모니터링", "의사결정 대기", "보류", "취소", "완료"]
TERMINAL_STATUSES = ["완료", "취소"]
PRIORITIES = ["high", "normal", "low"]


def load() -> dict:
    cfg = dict(DEFAULTS)
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            user = yaml.safe_load(f) or {}
        for k, v in user.items():
            if isinstance(v, dict) and isinstance(cfg.get(k), dict):
                cfg[k] = {**cfg[k], **v}
            else:
                cfg[k] = v
    cfg["vault"] = Path(str(cfg["vault"])).expanduser()
    return cfg
