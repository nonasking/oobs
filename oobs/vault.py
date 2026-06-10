# -*- coding: utf-8 -*-
"""볼트 파일 입출력 — frontmatter 파싱/직렬화, 원자적 쓰기, 데일리 노트, 노트 검색.

규칙은 ~/vault/CLAUDE.md 를 따른다:
- frontmatter 키 순서 고정, tags 는 flow style ([task])
- 날짜는 YYYY-MM-DD
- 데일리 노트는 ## 로그 끝에 append-only
- 원자적 쓰기 (temp + os.replace) — 동기화 도입 대비
"""
import datetime as dt
import os
import re
import tempfile
from pathlib import Path

import yaml

FRONT_KEYS = [
    "tags", "status", "category", "repo", "priority",
    "link", "note", "due", "scheduled", "created", "completed", "session",
]
FORBIDDEN = ':/\\|#^[]'
PROGRESS_HEADER = "## 진행 일지"


def today() -> str:
    return dt.date.today().isoformat()


def fmt(val) -> str:
    if val is None:
        return ""
    if isinstance(val, (dt.date, dt.datetime)):
        return val.strftime("%Y-%m-%d")
    return str(val)


def safe_filename(title: str) -> str:
    name = "".join("-" if c in FORBIDDEN or c.isspace() else c for c in title.strip())
    name = re.sub(r"-{2,}", "-", name).strip("-")
    if not name:
        raise ValueError(f"제목에서 유효한 파일명을 만들 수 없음: {title!r}")
    return name


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=path.parent, suffix=".tmp")
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as f:
            f.write(content)
        os.replace(tmp, path)
    except BaseException:
        if os.path.exists(tmp):
            os.unlink(tmp)
        raise


def parse_note(path: Path) -> tuple[dict, str]:
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\A---\n(.*?)\n---\n?", text, re.DOTALL)
    if not m:
        return {}, text
    meta = yaml.safe_load(m.group(1)) or {}
    return meta, text[m.end():]


def serialize_note(meta: dict, body: str) -> str:
    lines = ["---"]
    keys = FRONT_KEYS + [k for k in meta if k not in FRONT_KEYS]
    for key in keys:
        if key == "tags":
            tags = meta.get("tags") or ["task"]
            lines.append(f"tags: [{', '.join(str(t) for t in tags)}]")
            continue
        if key not in meta and key not in FRONT_KEYS:
            continue
        val = fmt(meta.get(key))
        lines.append(f"{key}: {val}".rstrip())
    lines.append("---")
    return "\n".join(lines) + "\n\n" + body.lstrip("\n")


def write_note(path: Path, meta: dict, body: str) -> None:
    atomic_write(path, serialize_note(meta, body))


def append_progress(body: str, memo: str, date: str | None = None) -> str:
    """## 진행 일지 섹션 끝에 `- YYYY-MM-DD memo` 한 줄 append. 섹션 없으면 본문 끝에 생성."""
    entry = f"- {date or today()} {memo}"
    if PROGRESS_HEADER not in body:
        return body.rstrip("\n") + f"\n\n{PROGRESS_HEADER}\n\n{entry}\n"
    lines = body.split("\n")
    start = next(i for i, l in enumerate(lines) if l.strip() == PROGRESS_HEADER)
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## "):
            end = i
            break
    # 섹션 내 마지막 비어 있지 않은 줄 뒤에 삽입
    insert_at = start
    for i in range(start + 1, end):
        if lines[i].strip():
            insert_at = i
    lines.insert(insert_at + 1, entry)
    return "\n".join(lines)


def daily_append(vault: Path, line: str) -> Path:
    path = vault / "daily" / f"{today()}.md"
    if path.exists():
        text = path.read_text(encoding="utf-8")
        if "## 로그" not in text:
            text = text.rstrip("\n") + "\n\n## 로그\n"
        text = text.rstrip("\n") + f"\n- {line}\n"
    else:
        text = f"# {today()}\n\n## 로그\n\n- {line}\n"
    atomic_write(path, text)
    return path


def find_tasks(vault: Path, query: str) -> list[Path]:
    """파일명 부분일치 우선, 없으면 본문 검색."""
    tasks_dir = vault / "tasks"
    if not tasks_dir.is_dir():
        return []
    notes = sorted(tasks_dir.glob("*.md"))
    q = query.casefold().replace(" ", "-")
    hits = [p for p in notes if q in p.stem.casefold()]
    if hits:
        return hits
    q2 = query.casefold()
    return [p for p in notes if q2 in p.read_text(encoding="utf-8").casefold()]


def iter_tasks(vault: Path):
    tasks_dir = vault / "tasks"
    if not tasks_dir.is_dir():
        return
    for p in sorted(tasks_dir.glob("*.md")):
        meta, body = parse_note(p)
        yield p, meta, body
