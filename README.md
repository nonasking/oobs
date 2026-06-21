# oobs

옵시디언 관제탑 볼트(`~/vault`)의 작업 노트를 만들고, **Claude Code 세션과 연결**해 작업 오케스트레이션 관제탑으로 쓰는 CLI.
nacho(노션)·tako(Jira)와 같은 패턴 — **결정적인 파일 조작은 코드가, 세션 맥락 요약은 Claude 슬래시 커맨드가** 담당한다.

## 세 기둥

작업은 세 표면에서 다뤄지고, 셋 다 **같은 데이터(볼트 + Claude Code 세션)** 위에 있다. 안 겹친다.

```
 Obsidian          = 장기기억·아카이브·검색   (과거+현재, frontmatter 뷰 / Bases)
 관제탑 /oobs-tower  = 능동 대화형 관리        (현황 종합·드리프트·등록·리포트)
 Agent View        = 라이브 운전              (claude agents, attach/detach)
```

핵심 원칙: 작업 ↔ 세션 연결은 **데이터**(frontmatter `session:` UUID)이지 프로세스 소유가 아니다.
→ 관제(노트 관찰)와 운전(세션 안 작업)이 독립적으로 굴러간다. 관제탑을 닫아도 하위 세션은 살아있다.

## 설치

```bash
./install.sh
```

venv 설치 + `~/.local/bin/oobs` 링크 + `/oobs`·`/oobs-note`·`/oobs-tower` 슬래시 커맨드 등록
+ `~/.config/oobs/config.yaml` 생성 + 볼트에 `작업보드.base`(Obsidian Bases 대시보드) 배치.

## 명령

```bash
# 작업
oobs new --title "WL-1234 정렬 버그" --status "진행 중" --repo crow-backend \
         --due 2026-06-30 --priority high --note "원인 파악 중" --body "배경..."
oobs note "정렬 버그" "PR 머지, 스테이징 검증 중" --status "배포 대기"
oobs done "정렬 버그" "운영 배포 완료"          # --cancel 이면 취소

# 조회
oobs list [--all | --status "보류"]            # 작업 표 (기본: 진행만)
oobs next [N]                                  # urgency 상위 N — 지금 뭐부터?
oobs stats                                     # 진행/마감초과/정체(14일+) 요약
oobs prime                                     # 세션 시작용 볼트 컨텍스트 다이제스트
oobs watch                                     # 작업 ↔ 세션 상태 + 드리프트 감지

# 세션 연결 (관제탑)
oobs link "정렬 버그" --dir ~/dev/crow-backend  # 그 디렉터리 최근 세션 자동 연결
oobs open "정렬 버그"                           # 닫힌 세션 재개 명령 (살아있는 세션은 Agent View)

# 기타
oobs inbox 갑자기 생각난 할 일                  # 분류 전 빠른 메모
oobs help [명령]                               # 예시 중심 설명서
```

상태값: `시작 전 | 진행 중 | 배포 대기 | 모니터링 | 의사결정 대기 | 보류 | 취소 | 완료`.
`new` 는 **유사 제목의 진행 작업이 있으면 생성을 거부**한다(중복 방지, 정말 새 작업이면 `--force`).
모든 쓰기는 원자적(temp + rename) — 모바일 동기화 도입에 대비. frontmatter 스키마는 `~/vault/CLAUDE.md` 와 동일하게 유지.

## 관제탑 — 작업 ↔ Claude Code 세션

작업 노트를 세션과 연결해 볼트를 관제탑으로 쓴다. 연결은 frontmatter 의 `session:`(UUID) — 데이터이지 프로세스가 아니다.

```
                         ~/vault  (진실)
        tasks/<작업>.md ──frontmatter  session: <uuid>──┐
                  ▲                                      │  데이터 링크
       oobs 읽기/쓰기 (watch·link·note)                  │ (프로세스 소유 아님)
                  │                                      ▼
   ┌──────────────┴──────────────┐         ┌────────────────────────────┐
   │ 관제탑 세션  /oobs-tower      │  관찰   │ 하위 작업 세션 N개 (독립)    │
   │ = 비행 스트립 보드           │ ──────▶ │ = 실제 운전 (코드·실행)      │
   │ 종합·드리프트·등록·리포트    │         └──────────────┬─────────────┘
   │ (운전·들어가기는 안 함)      │           살아있으면 등장 │
   └─────────────────────────────┘         ┌──────────────▼─────────────┐
                                           │ Agent View (claude agents)  │
                                           │ = 레이더: 라이브 상태+attach │
                                           └─────────────────────────────┘
```

두 화면이 상보적이다 — **Agent View**(레이더)는 "세션이 작업중/대기"와 attach해 운전을,
**관제탑**(스트립 보드)은 "그게 WL-1234, 금요일 마감, 3일 정체"와 **세션 없는 작업까지** 보여준다.

- `oobs watch` — 작업+세션 상태를 합친 보드. 진행 중인데 세션이 없거나 2일+ 정체면 **드리프트** 경고
- `oobs link "<작업>" --dir <레포>` — 그 디렉터리에서 방금 띄운 세션을 자동 연결 (uuid 직접 지정도 가능)
- `oobs open "<작업>"` — **닫힌** 세션 재개 명령(`claude --resume`). 살아있는 세션이면 Agent View 에서 attach 하라고 안내
- `/oobs-tower` — 이 세션을 관제탑 운영관으로 (종합·드리프트·등록·리포트만, 운전은 Agent View)

세션 라이브 상태는 `claude agents --json`(Agent View)에서 읽고, claude 가 없으면 전사파일 mtime 으로 추정한다
(선택 통합 — 코어는 claude 를 모른다, 미러와 같은 subprocess 경계). bg 세션 생성은 세션 내 인터랙티브 동작이라
oobs 는 띄우지 않고 `link` 로 **등록**만 한다.

## Obsidian 대시보드 (Bases)

볼트의 `작업보드.base` 를 Obsidian 에서 열면 **진행 보드 / 마감순 / 완료 아카이브 / 레포별** 뷰가 뜬다.

- Bases 는 oobs 가 쓰는 **frontmatter 를 라이브로 읽는다** → `oobs new/note/done` 하면 보드에 **자동 반영**(export/sync 없음)
- 완료해도 노트는 안 지움(`status: 완료`로 남음) → 과거 작업이 영구 누적, 전역 검색·백링크로 탐색
- 단 **라이브 세션 상태(작업중/대기)는 frontmatter 밖**이라 보드는 "연결된 세션명"까지만 — 실시간은 `oobs watch`

노션에서 하던 것(검색·DB 뷰·관계·속성)은 Obsidian(전역 검색·Bases·백링크·frontmatter)으로 그대로 대체된다.

## urgency

Taskwarrior 의 가중합을 볼트 스키마에 번안 — 마감 21일 램프(×12) + 우선순위(high 6 / normal 3.9 / low 1.8)
+ 상태(배포 대기 +5, 진행 중 +4, 보류 −3 등) + 작업 나이(최대 +2). `oobs next` 가 이 점수 상위를 뽑는다.

## 의존성과 결합도

**oobs 코어는 standalone** — PyYAML 외 의존성이 없고, nacho/tako 없이 볼트만 있으면 완결 동작한다.
세션 연결은 `claude agents --json` 을 subprocess 로 부르지만(선택 통합), claude 가 없으면 mtime 으로 폴백 — 코어는 claude 를 import 하지 않는다.
nacho 미러도 `mirror.py` 한 파일에 격리돼 subprocess 호출이라 nacho 내부를 모른다. 들어낼 때:

1. 운영상 끄기: `config.yaml` 의 `mirror: false` (코드 무변경)
2. 완전 제거: `oobs/mirror.py` 삭제 + `main.py` 의 `mirror.enabled()` guard 2곳 삭제 + config `nacho:` 섹션 삭제

## 설계 — 왜 MCP 서버가 아니라 CLI + 얇은 스킬인가

MCP 의 컨텍스트 비용은 호출이 아니라 **상주**에서 나간다. MCP 서버를 붙이면 도구 스키마가 모든 세션의
시스템 프롬프트에 실린다 — 쓰지 않는 세션에서도 수천~만 토큰. CLI + 얇은 스킬은 그 상주 비용을 호출 시점 비용으로 바꾼다:

- **상주 비용**: 스킬 설명 한 줄(수십 토큰)뿐. 사용법 지식은 `/oobs` 호출 순간에만 로드
- **세션 밖 셸 직접 호출 = 토큰 0** + 결정적 동작 + 테스트/버전 관리 가능
- oobs 는 어차피 로컬 파일 조작이라 MCP 서버를 끼우면 순수 오버헤드

트레이드오프: 최신 Claude Code 는 MCP 도구를 지연 로딩(ToolSearch)하므로 상주 격차가 예전만큼 크지 않고,
타입 스키마로 잘못된 호출을 줄이는 이점도 있다. 다만 oobs 는 로컬 파일이라 그 이점이 작다.

## 노션 미러 (병행 기간, 선택)

`new`/`note`/`done` 은 같은 내용을 nacho 로 노션에도 보낼 수 있다.

- 스위치: `~/.config/oobs/config.yaml` 의 `mirror:` — `auto`(기본, nacho 있으면 미러) | `true` | `false`
- 일회성 제외: `--no-mirror`. 노션 옵션에 없는 분류/프로젝트는 미러에서 자동 생략(볼트엔 자유 값 기록)
- 미러 실패는 경고만 — 볼트 기록(원본)은 항상 성공시킴

## 구조

```
oobs/
├── main.py    서브커맨드·플래그 (new/note/done/list/next/stats/prime/inbox + watch/link/open)
├── vault.py   frontmatter 파싱/직렬화, 원자적 쓰기, 데일리 노트, 검색, urgency, 세션 연결/관찰
├── mirror.py  nacho 비인터랙티브 호출 (빈 입력 stdin 공급)
└── config.py  ~/.config/oobs/config.yaml + 상태/우선순위 상수
commands/
├── oobs.md        /oobs       — 세션 맥락으로 작업 노트 생성
├── oobs-note.md   /oobs-note  — 진행 일지 기록
└── oobs-tower.md  /oobs-tower — 관제탑 (종합·드리프트·등록·리포트)
templates/
└── 작업보드.base  Obsidian Bases 대시보드 (install.sh 가 볼트에 배치)
```
