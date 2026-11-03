# -*- coding: utf-8 -*-
"""oobs.mirror → nacho 호출 계약 테스트 (subprocess는 mock)."""
from __future__ import annotations

import subprocess
import unittest
from unittest import mock

from oobs import mirror


def _ok(stdout: str = "✓ 생성됨: https://www.notion.so/abc\n") -> subprocess.CompletedProcess:
    return subprocess.CompletedProcess(args=[], returncode=0, stdout=stdout, stderr="")


class MirrorNewTest(unittest.TestCase):
    def setUp(self) -> None:
        patcher = mock.patch.object(mirror, "_nacho_available", return_value=True)
        patcher.start()
        self.addCleanup(patcher.stop)

    def test_runs_non_interactive_and_passes_session(self) -> None:
        with mock.patch.object(mirror.subprocess, "run", return_value=_ok()) as run:
            url = mirror.mirror_new({}, title="t", status="진행 중", session="uuid-1")
        cmd = run.call_args.args[0]
        self.assertIn("--no-prompt", cmd)
        self.assertEqual(cmd[cmd.index("--session-id") + 1], "uuid-1")
        # 빈 줄로 프롬프트를 넘기지 않는다(링크 프롬프트에서 Y로 처리되던 문제).
        self.assertEqual(run.call_args.kwargs["input"], "")
        self.assertEqual(url, "https://www.notion.so/abc")

    def test_session_omitted_when_empty(self) -> None:
        with mock.patch.object(mirror.subprocess, "run", return_value=_ok()) as run:
            mirror.mirror_new({}, title="t", status="진행 중")
        self.assertNotIn("--session-id", run.call_args.args[0])

    def test_failure_with_empty_output_does_not_crash(self) -> None:
        failed = subprocess.CompletedProcess(args=[], returncode=1, stdout="", stderr="")
        with mock.patch.object(mirror.subprocess, "run", return_value=failed):
            self.assertIsNone(mirror.mirror_new({}, title="t", status="진행 중"))


if __name__ == "__main__":
    unittest.main()
