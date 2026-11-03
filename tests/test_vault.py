# -*- coding: utf-8 -*-
"""oobs.vault 단위 테스트 (stdlib unittest — 추가 의존성·네트워크·실제 볼트 없음).

파일을 만지는 테스트는 모두 tempfile 임시 디렉터리 안에서만 돈다.

실행: python -m unittest discover -s tests
"""
from __future__ import annotations

import datetime as dt
import json
import os
import tempfile
import unittest
from pathlib import Path

from oobs import vault


class SafeFilenameTest(unittest.TestCase):
    def test_spaces_become_hyphens(self) -> None:
        self.assertEqual(vault.safe_filename("WL-1234 정렬 버그"), "WL-1234-정렬-버그")

    def test_forbidden_chars_replaced(self) -> None:
        # : / \ | # ^ [ ] 는 옵시디언에서 파일명에 못 씀
        self.assertEqual(vault.safe_filename("a:b/c|d#e"), "a-b-c-d-e")
        self.assertEqual(vault.safe_filename("[초안] 검토"), "초안-검토")

    def test_repeated_hyphens_collapsed_and_trimmed(self) -> None:
        self.assertEqual(vault.safe_filename("  a   b  "), "a-b")
        self.assertEqual(vault.safe_filename("-- x --"), "x")

    def test_no_valid_chars_raises(self) -> None:
        for bad in ("", "   ", "///"):
            with self.assertRaises(ValueError):
                vault.safe_filename(bad)


class FmtTest(unittest.TestCase):
    def test_none_becomes_empty_string(self) -> None:
        self.assertEqual(vault.fmt(None), "")

    def test_dates_normalized_to_iso(self) -> None:
        self.assertEqual(vault.fmt(dt.date(2026, 6, 30)), "2026-06-30")
        self.assertEqual(vault.fmt(dt.datetime(2026, 6, 30, 13, 5)), "2026-06-30")
        self.assertEqual(vault.fmt("2026-06-30"), "2026-06-30")


class FrontmatterTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.dir = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_round_trip_preserves_values(self) -> None:
        meta = {
            "tags": ["task"], "status": "진행 중", "category": "운영",
            "repo": "crow-backend", "priority": "high", "due": "2026-06-30",
            "created": "2026-06-01", "session": "abc-123",
        }
        body = "# 제목\n\n본문 한 줄\n"
        path = self.dir / "t.md"
        vault.write_note(path, meta, body)

        got_meta, got_body = vault.parse_note(path)
        for key, value in meta.items():
            if key == "tags":
                continue
            self.assertEqual(vault.fmt(got_meta.get(key)), value, key)
        self.assertEqual(got_meta["tags"], ["task"])
        self.assertEqual(got_body.strip(), body.strip())

    def test_key_order_fixed_and_tags_flow_style(self) -> None:
        text = vault.serialize_note({"status": "진행 중", "priority": "low"}, "본문")
        lines = text.split("\n")
        self.assertEqual(lines[0], "---")
        self.assertEqual(lines[1], "tags: [task]")  # 기본 tags + flow style
        keys = [l.split(":")[0] for l in lines[1:] if l != "---" and ":" in l]
        self.assertEqual(keys[: len(vault.FRONT_KEYS)], vault.FRONT_KEYS)  # 순서 고정

    def test_unknown_keys_appended_after_known_ones(self) -> None:
        text = vault.serialize_note({"status": "보류", "커스텀": "값"}, "본문")
        self.assertIn("커스텀: 값", text)
        self.assertGreater(text.index("커스텀:"), text.index("status:"))

    def test_note_without_frontmatter_parses_as_body(self) -> None:
        path = self.dir / "plain.md"
        path.write_text("# 그냥 메모\n", encoding="utf-8")
        meta, body = vault.parse_note(path)
        self.assertEqual(meta, {})
        self.assertEqual(body, "# 그냥 메모\n")

    def test_atomic_write_leaves_no_temp_file(self) -> None:
        path = self.dir / "sub" / "a.md"
        vault.atomic_write(path, "내용\n")  # 부모 디렉터리 자동 생성
        self.assertEqual(path.read_text(encoding="utf-8"), "내용\n")
        vault.atomic_write(path, "덮어쓴 내용\n")
        self.assertEqual(path.read_text(encoding="utf-8"), "덮어쓴 내용\n")
        self.assertEqual([p.name for p in path.parent.iterdir()], ["a.md"])


class AppendProgressTest(unittest.TestCase):
    def test_creates_section_when_absent(self) -> None:
        out = vault.append_progress("# 제목\n", "생성", date="2026-06-01")
        self.assertIn(vault.PROGRESS_HEADER, out)
        self.assertTrue(out.rstrip().endswith("- 2026-06-01 생성"))

    def test_appends_to_existing_section(self) -> None:
        body = f"# 제목\n\n{vault.PROGRESS_HEADER}\n\n- 2026-06-01 생성\n"
        out = vault.append_progress(body, "PR 머지", date="2026-06-02")
        lines = [l for l in out.split("\n") if l.startswith("- ")]
        self.assertEqual(lines, ["- 2026-06-01 생성", "- 2026-06-02 PR 머지"])

    def test_inserts_inside_section_not_after_following_section(self) -> None:
        body = (
            f"# 제목\n\n{vault.PROGRESS_HEADER}\n\n- 2026-06-01 생성\n\n## 참고\n\n링크\n"
        )
        out = vault.append_progress(body, "배포", date="2026-06-02")
        self.assertLess(out.index("- 2026-06-02 배포"), out.index("## 참고"))

    def test_defaults_to_today(self) -> None:
        out = vault.append_progress("# 제목\n", "메모")
        self.assertIn(f"- {vault.today()} 메모", out)


class UrgencyTest(unittest.TestCase):
    REF = dt.date(2026, 6, 15)

    def test_priority_coefficients(self) -> None:
        self.assertEqual(vault.urgency({"priority": "high"}, self.REF), 6.0)
        self.assertEqual(vault.urgency({"priority": "normal"}, self.REF), 3.9)
        self.assertEqual(vault.urgency({"priority": "low"}, self.REF), 1.8)
        self.assertEqual(vault.urgency({}, self.REF), 3.9)  # 미지정 = normal
        self.assertEqual(vault.urgency({"priority": "urgent"}, self.REF), 3.9)  # 미지의 값도 normal

    def test_status_coefficients(self) -> None:
        self.assertEqual(vault.urgency({"status": "배포 대기"}, self.REF), 8.9)  # 3.9 + 5.0
        self.assertEqual(vault.urgency({"status": "진행 중"}, self.REF), 7.9)
        self.assertEqual(vault.urgency({"status": "보류"}, self.REF), 0.9)  # 3.9 - 3.0
        self.assertEqual(vault.urgency({"status": "의사결정 대기"}, self.REF), 2.9)
        self.assertEqual(vault.urgency({"status": "시작 전"}, self.REF), 3.9)

    def test_due_ramp(self) -> None:
        # 7일 이상 초과 = 최대(1.0 × 12), 14일 넘게 남음 = 최소(0.2 × 12)
        overdue = vault.urgency({"due": "2026-06-01"}, self.REF)  # 14일 초과
        self.assertAlmostEqual(overdue, 12.0 + 3.9, places=1)
        far = vault.urgency({"due": "2026-08-01"}, self.REF)
        self.assertAlmostEqual(far, 12.0 * 0.2 + 3.9, places=1)
        today_due = vault.urgency({"due": "2026-06-15"}, self.REF)
        self.assertAlmostEqual(today_due, 8.8 + 3.9, places=1)
        self.assertLess(far, today_due)
        self.assertLess(today_due, overdue)

    def test_due_accepts_date_object(self) -> None:
        self.assertEqual(
            vault.urgency({"due": dt.date(2026, 6, 1)}, self.REF),
            vault.urgency({"due": "2026-06-01"}, self.REF),
        )

    def test_age_bonus_caps_at_one_year(self) -> None:
        fresh = vault.urgency({"created": "2026-06-15"}, self.REF)
        old = vault.urgency({"created": "2025-06-01"}, self.REF)  # 1년 이상
        self.assertEqual(fresh, 3.9)
        self.assertEqual(old, 5.9)  # 3.9 + 2.0 (상한)


class DaysIdleTest(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.path = Path(self._tmp.name) / "t.md"
        self.path.write_text("x", encoding="utf-8")

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def test_uses_latest_progress_date(self) -> None:
        body = "- 2020-01-01 옛날\n- 2020-01-05 그 다음\n"
        expected = (dt.date.today() - dt.date(2020, 1, 5)).days
        self.assertEqual(vault.days_idle(self.path, body), expected)

    def test_falls_back_to_mtime_without_progress_lines(self) -> None:
        # 진행 일지 줄이 없으면 파일 mtime 기준 — 방금 만든 파일이므로 0일
        self.assertEqual(vault.days_idle(self.path, "# 제목\n본문\n"), 0)


class SessionLookupTest(unittest.TestCase):
    """~/.claude/projects 를 임시 디렉터리로 갈아끼우고 전사 파일(.jsonl) 픽스처로 검증."""

    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)
        self.projects = self.root / "projects"
        self.projects.mkdir()
        self._prev = vault.CLAUDE_PROJECTS
        vault.CLAUDE_PROJECTS = self.projects

    def tearDown(self) -> None:
        vault.CLAUDE_PROJECTS = self._prev
        self._tmp.cleanup()

    def _session(self, slug: str, uuid: str, cwd: str | None, mtime: float) -> Path:
        d = self.projects / slug
        d.mkdir(parents=True, exist_ok=True)
        p = d / f"{uuid}.jsonl"
        lines = [json.dumps({"type": "summary"})]
        if cwd is not None:
            lines.append(json.dumps({"type": "user", "cwd": cwd}))
        p.write_text("\n".join(lines) + "\n", encoding="utf-8")
        os.utime(p, (mtime, mtime))
        return p

    def test_newest_session_for_dir_picks_most_recent(self) -> None:
        repo = self.root / "dev" / "crow-backend"
        repo.mkdir(parents=True)
        self._session("-dev-crow-backend", "old-uuid", str(repo), mtime=1_000_000)
        self._session("-dev-crow-backend", "new-uuid", str(repo), mtime=2_000_000)
        self.assertEqual(vault.newest_session_for_dir(str(repo)), "new-uuid")

    def test_newest_session_for_dir_matches_cwd_not_slug(self) -> None:
        # 슬러그는 / _ . 가 모두 - 로 뭉개져 비가역 — 매칭은 전사 파일의 cwd 필드로만.
        repo = self.root / "dev" / "oobs"
        other = self.root / "dev" / "tako"
        repo.mkdir(parents=True)
        other.mkdir(parents=True)
        self._session("-dev-tako", "tako-uuid", str(other), mtime=3_000_000)
        self._session("-dev-oobs", "oobs-uuid", str(repo), mtime=1_000_000)
        self.assertEqual(vault.newest_session_for_dir(str(repo)), "oobs-uuid")

    def test_newest_session_for_dir_none_when_no_match(self) -> None:
        empty = self.root / "dev" / "nothing"
        empty.mkdir(parents=True)
        self._session("-dev-other", "u1", str(self.root / "dev" / "other"), mtime=1_000_000)
        self.assertIsNone(vault.newest_session_for_dir(str(empty)))

    def test_transcript_without_cwd_is_skipped(self) -> None:
        repo = self.root / "dev" / "x"
        repo.mkdir(parents=True)
        self._session("-dev-x", "no-cwd", None, mtime=5_000_000)
        self.assertIsNone(vault.newest_session_for_dir(str(repo)))

    def test_find_session_jsonl_and_status(self) -> None:
        repo = self.root / "dev" / "y"
        repo.mkdir(parents=True)
        p = self._session("-dev-y", "uuid-1", str(repo), mtime=dt.datetime.now().timestamp())
        self.assertEqual(vault.find_session_jsonl("uuid-1"), p)
        self.assertIsNone(vault.find_session_jsonl("nope"))
        self.assertIsNone(vault.find_session_jsonl(""))

        st = vault.session_status("uuid-1")
        self.assertIsNotNone(st)
        self.assertEqual(st["idle_days"], 0)
        self.assertEqual(st["last"], "방금")
        self.assertIsNone(vault.session_status("nope"))


if __name__ == "__main__":
    unittest.main()


class SpecialCharRoundTripTest(unittest.TestCase):
    """YAML에서 특별한 의미가 있는 문자가 들어간 값도 그대로 돌아와야 한다."""

    def _round_trip(self, **meta):
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "t.md"
            vault.write_note(path, {"tags": ["task"], **meta}, "# t\n")
            parsed, _ = vault.parse_note(path)
        return parsed

    def test_colon_bracket_hash_values_survive(self) -> None:
        values = ["배포: 완료", "[WIP] 작업", "#3 이슈", "PR #12 리뷰", "a, b", "yes", "null", "'따옴표'", '큰"따옴표']
        for v in values:
            with self.subTest(v=v):
                self.assertEqual(self._round_trip(note=v)["note"], v)

    def test_dates_and_numbers_stay_unquoted(self) -> None:
        self.assertEqual(vault.fmt("2026-11-10"), "2026-11-10")
        self.assertEqual(vault.fmt(3), "3")
        self.assertEqual(vault.fmt("진행 중"), "진행 중")
        self.assertEqual(self._round_trip(due="2026-11-10")["due"], dt.date(2026, 11, 10))

    def test_quoted_only_when_needed(self) -> None:
        self.assertEqual(vault.fmt("배포: 완료"), '"배포: 완료"')


class InvalidDueTest(unittest.TestCase):
    def test_non_date_due_does_not_crash_urgency(self) -> None:
        self.assertEqual(vault._due_measure("다음주", dt.date(2026, 11, 2)), 0.0)


class AtomicWriteModeTest(unittest.TestCase):
    def test_existing_file_mode_preserved(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "n.md"
            path.write_text("old", encoding="utf-8")
            os.chmod(path, 0o644)
            vault.atomic_write(path, "new")
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)
            self.assertEqual(path.read_text(encoding="utf-8"), "new")

    def test_new_file_follows_umask(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            path = Path(d) / "n.md"
            old = os.umask(0o022)
            try:
                vault.atomic_write(path, "x")
            finally:
                os.umask(old)
            self.assertEqual(path.stat().st_mode & 0o777, 0o644)
