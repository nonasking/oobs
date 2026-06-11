# oobs 백로그

2026-06-11 유사 도구 리서치(Taskwarrior/Beads/Backlog.md/TaskNotes 등)에서 수집한 채택 후보.
v0.2 에 반영: urgency(`next`), `prime`, `stats`+정체 감지, 생성 시 중복 감지.

## 후보 (가치순)

- **의존성 + ready** (Beads `bd ready`): `blocked_by:` frontmatter 리스트(위키링크) + `oobs ready` —
  막힌 것 없는 작업만 추출. 작업 수가 늘고 순서 의존이 생기면 도입. urgency 에 BLOCKED −5 / BLOCKING +8 반영.
- **review 루프** (tasksh): `reviewed:` 필드 + `oobs review` — 7일+ 미리뷰 작업을 하나씩 넘기며
  유지/종료/병합 결정. 작업 부패 방지. stats 의 정체 감지가 임시 대용.
- **wait/threshold 날짜** (Taskwarrior `wait:` / todo.txt `t:`): 지정일까지 list/next 에서 숨김.
- **rec: 반복** (topydo 방식): 완료 시점에 due 를 미룬 클론 생성. Taskwarrior 의 부모-템플릿 모델은 과함.
- **자연어 날짜** (`dateparser`): `--due 금요일`. 현재는 스킬(Claude)이 변환해주므로 셸 직접 사용 시에만 가치.
- **완료 조건 체크리스트** (Backlog.md): 태스크 템플릿에 `## 완료 조건` 섹션, done 시 미체크 항목 경고.
- **oobs sync** (dstask): 볼트를 git 레포로 만들고 pull→commit→push 한 방. 모바일 동기화 대안이기도 함.
- **상태 전이 자동 로그** (org-mode): status 변경 시 진행 일지에 `(상태: A → B)` 자동 표기.
- **체크박스 서브태스크 주소화** (nb): `oobs check <task> <n>` 으로 본문 `- [ ]` 토글.
- **오래된 완료 작업 다이제스트** (Beads memory decay): 분기마다 완료 노트를 요약 노트로 접어 prime 출력을 가볍게.
- **이벤트 훅** (Taskwarrior hooks / TaskNotes webhooks): `~/.config/oobs/hooks/on-new` 등 —
  노션 미러를 훅의 한 구현으로 일반화 (결합도 추가 하락).

## 비채택 (이유)

- SQLite 인덱스 — 볼트 규모상 glob+파싱으로 충분
- 자체 칸반/웹 UI — Obsidian Bases 가 이미 그 역할 (TaskNotes v4 도 같은 결론으로 자체 UI 폐기)
- 노트 암호화 — Obsidian 렌더링과 충돌
- 해시 ID — 파일명이 ID. 병렬 세션 충돌이 실제로 나면 재검토
