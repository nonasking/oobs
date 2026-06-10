# -*- coding: utf-8 -*-
"""oobs — 옵시디언 관제탑 볼트 작업 노트 CLI.

서브커맨드:
  new    작업 노트 생성 (+데일리 로그, +노션 미러)
  note   진행 일지 한 줄 append + 현황 요약 갱신 (+노션 미러)
  done   완료/취소 처리 (+데일리 로그, +노션 미러)
  list   작업 현황 표 출력 (frontmatter 직접 파싱 — 옵시디언 앱 불필요)
  inbox  inbox/ 에 빠른 메모
"""
import argparse
import sys
from pathlib import Path

from . import config, mirror, vault

MARKERS = {
    "시작 전": "⚪", "진행 중": "🔵", "배포 대기": "🚀", "모니터링": "📡",
    "의사결정 대기": "🤔", "보류": "⏸️", "취소": "🚫", "완료": "✅",
}


def fail(msg: str) -> None:
    print(f"[x] {msg}", file=sys.stderr)
    sys.exit(1)


def pick_note(cfg: dict, query: str, first: bool) -> Path:
    hits = vault.find_tasks(cfg["vault"], query)
    if not hits:
        fail(f"'{query}' 에 매칭되는 작업 노트 없음 (tasks/ 파일명·본문 검색)")
    if len(hits) == 1 or first:
        return hits[0]
    print(f"'{query}' 매칭 {len(hits)}건:")
    for i, p in enumerate(hits, 1):
        print(f"  {i}) {p.stem}")
    try:
        sel = input("번호 선택: ").strip()
    except EOFError:
        fail("비인터랙티브 환경에서 다중 매칭 — 검색어를 좁히거나 --first 사용")
    if not sel.isdigit() or not (1 <= int(sel) <= len(hits)):
        fail("잘못된 선택")
    return hits[int(sel) - 1]


def strip_progress_for_mirror(body: str) -> str:
    """미러 body 에는 진행 일지 섹션 제외 — nacho 가 자체 진행 일지를 생성하므로 중복 방지."""
    lines, out, skipping = body.split("\n"), [], False
    for line in lines:
        if line.strip() == vault.PROGRESS_HEADER:
            skipping = True
            continue
        if skipping and line.startswith("## "):
            skipping = False
        if not skipping:
            out.append(line)
    return "\n".join(out).strip()


# ---------------------------------------------------------------- new

def cmd_new(args) -> int:
    cfg = config.load()
    if args.status not in config.STATUSES:
        fail(f"status 는 다음 중 하나: {' | '.join(config.STATUSES)}")
    if args.priority not in config.PRIORITIES:
        fail(f"priority 는 다음 중 하나: {' | '.join(config.PRIORITIES)}")
    name = vault.safe_filename(args.title)
    path = cfg["vault"] / "tasks" / f"{name}.md"
    if path.exists():
        fail(f"동명 노트가 이미 있음: {path} (갱신은 oobs note)")

    today = vault.today()
    meta = {
        "tags": ["task"], "status": args.status, "category": args.category,
        "repo": args.repo, "priority": args.priority, "link": args.link,
        "note": args.note, "due": args.due, "scheduled": args.scheduled,
        "created": today, "completed": "", "session": args.session,
    }
    body = f"# {args.title}\n"
    if args.body:
        body += f"\n{args.body.strip()}\n"
    body = vault.append_progress(body, args.note or "생성")
    vault.write_note(path, meta, body)
    print(f"✓ 생성: {path}")

    if not args.no_daily:
        line = f"{args.note or args.title} → [[{name}]]"
        vault.daily_append(cfg["vault"], line)
        print(f"✓ 데일리 로그: {line}")

    if mirror.enabled(cfg) and not args.no_mirror:
        url = mirror.mirror_new(
            cfg, title=args.title, status=args.status, category=args.category,
            project=args.project, due=args.due, link=args.link,
            body=strip_progress_for_mirror(body),
        )
        if url is not None:
            print(f"✓ 노션 미러: {url or '(URL 미확인)'}")
    return 0


# ---------------------------------------------------------------- note / done

def _update(cfg: dict, path: Path, memo: str, status: str | None, do_mirror: bool, query: str,
            no_daily: bool = False) -> int:
    meta, body = vault.parse_note(path)
    meta["note"] = memo
    daily_line = None
    if status:
        if status not in config.STATUSES:
            fail(f"status 는 다음 중 하나: {' | '.join(config.STATUSES)}")
        meta["status"] = status
        if status in config.TERMINAL_STATUSES and not no_daily:
            meta["completed"] = vault.today()
            daily_line = f"{path.stem} {status} — {memo} → [[{path.stem}]]"
        elif status in config.TERMINAL_STATUSES:
            meta["completed"] = vault.today()
    body = vault.append_progress(body, memo)
    vault.write_note(path, meta, body)
    print(f"✓ 갱신: {path.stem}  [{meta.get('status')}] {memo}")
    if daily_line:
        vault.daily_append(cfg["vault"], daily_line)
        print(f"✓ 데일리 로그: {daily_line}")
    if mirror.enabled(cfg) and do_mirror:
        # 노션 검색어는 사용자 검색어가 아니라 노트 제목(H1)에서 — 파일명 하이픈과 노션 제목 공백 불일치 방지
        if mirror.mirror_note(_mirror_query(body, path, query), memo):
            print("✓ 노션 미러")
    return 0


def _mirror_query(body: str, path: Path, fallback: str) -> str:
    for line in body.split("\n"):
        if line.startswith("# "):
            return line[2:].strip()
    return path.stem.replace("-", " ") or fallback


def cmd_note(args) -> int:
    cfg = config.load()
    path = pick_note(cfg, args.query, args.first)
    return _update(cfg, path, args.memo, args.status, not args.no_mirror, args.query, args.no_daily)


def cmd_done(args) -> int:
    cfg = config.load()
    path = pick_note(cfg, args.query, args.first)
    status = "취소" if args.cancel else "완료"
    memo = args.memo or status
    return _update(cfg, path, memo, status, not args.no_mirror, args.query, args.no_daily)


# ---------------------------------------------------------------- list

def cmd_list(args) -> int:
    cfg = config.load()
    rows = []
    for path, meta, _ in vault.iter_tasks(cfg["vault"]):
        status = str(meta.get("status", ""))
        if args.status and status != args.status:
            continue
        if not args.all and not args.status and status in config.TERMINAL_STATUSES:
            continue
        rows.append((
            MARKERS.get(status, "·"), status, path.stem,
            vault.fmt(meta.get("note")), vault.fmt(meta.get("due")),
        ))
    if not rows:
        print("(없음)")
        return 0
    rows.sort(key=lambda r: (config.STATUSES.index(r[1]) if r[1] in config.STATUSES else 99, r[4] or "9999"))
    w_name = max(len(r[2]) for r in rows)
    for m, status, name, note, due in rows:
        due_s = f"  ~{due}" if due else ""
        note_s = f"  | {note}" if note else ""
        print(f"{m} {status:<7} {name:<{w_name}}{due_s}{note_s}")
    return 0


# ---------------------------------------------------------------- inbox

def cmd_inbox(args) -> int:
    cfg = config.load()
    title = " ".join(args.text)
    name = vault.safe_filename(f"{vault.today()} {title[:40]}")
    path = cfg["vault"] / "inbox" / f"{name}.md"
    n = 1
    while path.exists():
        n += 1
        path = cfg["vault"] / "inbox" / f"{name}-{n}.md"
    vault.atomic_write(path, f"{title}\n")
    print(f"✓ inbox: {path}")
    return 0


# ---------------------------------------------------------------- entry

def run() -> None:
    p = argparse.ArgumentParser(prog="oobs", description="옵시디언 관제탑 볼트 작업 노트 CLI")
    sub = p.add_subparsers(dest="cmd", required=True)

    pn = sub.add_parser("new", help="작업 노트 생성")
    pn.add_argument("--title", required=True)
    pn.add_argument("--status", default="진행 중", help=f"기본 '진행 중' ({' | '.join(config.STATUSES)})")
    pn.add_argument("--category", default="")
    pn.add_argument("--project", default="", help="노션 미러 전용 (글로벌 윙크 | 한국 윙크)")
    pn.add_argument("--repo", default="")
    pn.add_argument("--priority", default="normal")
    pn.add_argument("--link", default="")
    pn.add_argument("--note", default="", help="현황 요약 한 줄")
    pn.add_argument("--due", default="")
    pn.add_argument("--scheduled", default="")
    pn.add_argument("--session", default="")
    pn.add_argument("--body", default="")
    pn.add_argument("--no-mirror", action="store_true")
    pn.add_argument("--no-daily", action="store_true")
    pn.set_defaults(func=cmd_new)

    pt = sub.add_parser("note", help="진행 일지 한 줄 + 현황 요약 갱신")
    pt.add_argument("query")
    pt.add_argument("memo")
    pt.add_argument("--status", default=None)
    pt.add_argument("--first", action="store_true", help="다중 매칭 시 첫 결과 사용")
    pt.add_argument("--no-mirror", action="store_true")
    pt.add_argument("--no-daily", action="store_true")
    pt.set_defaults(func=cmd_note)

    pd = sub.add_parser("done", help="완료(또는 --cancel 취소) 처리")
    pd.add_argument("query")
    pd.add_argument("memo", nargs="?", default="")
    pd.add_argument("--cancel", action="store_true")
    pd.add_argument("--first", action="store_true")
    pd.add_argument("--no-mirror", action="store_true")
    pd.add_argument("--no-daily", action="store_true")
    pd.set_defaults(func=cmd_done)

    pl = sub.add_parser("list", help="작업 현황 (기본: 진행 작업만)")
    pl.add_argument("--status", default=None)
    pl.add_argument("--all", action="store_true")
    pl.set_defaults(func=cmd_list)

    pi = sub.add_parser("inbox", help="inbox 에 빠른 메모")
    pi.add_argument("text", nargs="+")
    pi.set_defaults(func=cmd_inbox)

    args = p.parse_args()
    sys.exit(args.func(args) or 0)
