# -*- coding: utf-8 -*-
"""노션 미러 — nacho CLI 를 비인터랙티브로 호출. 병행 기간이 끝나면 config 의 mirror: false 로 끔.

nacho 특성:
- `--yes` 여도 플래그로 안 준 enum/입력 필드를 인터랙티브로 묻는다 → 빈 입력을 stdin 으로 공급
- 옵션에 없는 분류/프로젝트 값을 플래그로 주면 에러 → config 의 옵션 목록과 대조해 매칭될 때만 전달
- 미러 실패는 경고만 — 볼트 기록(원본)을 막지 않는다
"""
import re
import shutil
import subprocess
import sys

EMPTY_INPUTS = "\n" * 10  # 분류/프로젝트/담당자/시작일/링크 등 잔여 프롬프트는 전부 기본값/비움


def _warn(msg: str) -> None:
    print(f"  [미러 경고] {msg}", file=sys.stderr)


def _nacho_available() -> bool:
    return shutil.which("nacho") is not None


def enabled(cfg: dict) -> bool:
    """미러 수행 여부 결정. auto 면 nacho 존재 여부로 판단 (없으면 조용히 스킵)."""
    mode = cfg.get("mirror", "auto")
    if mode is True:
        if not _nacho_available():
            _warn("mirror: true 이지만 nacho 명령을 찾을 수 없음 — 미러 건너뜀")
            return False
        return True
    if mode == "auto":
        return _nacho_available()
    return False


def mirror_new(cfg: dict, *, title: str, status: str, category: str = "",
               project: str = "", due: str = "", link: str = "", body: str = "") -> str | None:
    """nacho new 로 노션 행 생성. 성공 시 페이지 URL 반환, 실패 시 None."""
    if not _nacho_available():
        return None  # 수행 여부는 enabled() 에서 결정 — 여기선 방어만
    cmd = ["nacho", "new", "--yes", "--title", title, "--status", status]
    opts = cfg.get("nacho", {})
    if category in opts.get("categories", []):
        cmd += ["--category", category]
    elif category:
        _warn(f"분류 '{category}' 는 노션 옵션에 없어 미러에서 생략 (볼트에는 기록됨)")
    if project in opts.get("projects", []):
        cmd += ["--project", project]
    if due:
        cmd += ["--due-date", due]
    if link:
        cmd += ["--link", link]
    if body:
        cmd += ["--body", body]
    try:
        r = subprocess.run(cmd, input=EMPTY_INPUTS, capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        _warn("nacho new 응답 없음 (60s timeout)")
        return None
    if r.returncode != 0:
        _warn(f"nacho new 실패: {(r.stderr or r.stdout).strip().splitlines()[-1]}")
        return None
    m = re.search(r"https://\S*notion\S*", r.stdout)
    return m.group(0) if m else ""


def mirror_note(query: str, memo: str) -> bool:
    """nacho note 로 진행 일지 + 현황 요약 미러. 다중 매칭 등 인터랙션이 필요하면 실패 처리."""
    if not _nacho_available():
        return False  # 수행 여부는 enabled() 에서 결정 — 여기선 방어만
    try:
        r = subprocess.run(["nacho", "note", query, memo],
                           input="", capture_output=True, text=True, timeout=60)
    except subprocess.TimeoutExpired:
        _warn("nacho note 응답 없음 (60s timeout)")
        return False
    if r.returncode != 0:
        tail = (r.stderr or r.stdout).strip().splitlines()
        _warn(f"nacho note 실패: {tail[-1] if tail else '원인 불명'}")
        _warn(f"노션에 직접 반영하려면: nacho note \"{query}\" \"{memo}\"")
        return False
    return True
