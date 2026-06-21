# oobs

옵시디언 관제탑 볼트(`~/vault`)의 작업 노트를 생성·갱신·조회하는 CLI.
nacho(노션)·tako(Jira)와 같은 패턴 — **결정적인 파일 조작은 코드가, 세션 맥락 요약은 Claude 슬래시 커맨드가** 담당한다.

## 설치

```bash
./install.sh
```

venv 설치 + `~/.local/bin/oobs` 링크 + `/oobs`·`/oobs-note`·`/oobs-tower` 슬래시 커맨드 등록 + `~/.config/oobs/config.yaml` 생성.

## 명령

```bash
oobs new --title "WL-1234 정렬 버그" --status "진행 중" --repo danbi_server \
         --due 2026-06-30 --note "원인 파악 중" --body "배경 설명..."
oobs note "정렬 버그" "PR 머지, 스테이징 검증 중" --status "배포 대기"
oobs done "정렬 버그" "운영 배포 완료"        # --cancel 이면 취소 처리
oobs list                                    # 진행 작업만 (--all 로 전체)
oobs next                                    # urgency 상위 — 지금 뭐부터?
oobs stats                                   # 진행/마감초과/정체(14일+) 요약
oobs prime                                   # 세션 시작용 볼트 컨텍스트 다이제스트
oobs inbox 갑자기 생각난 할 일

oobs watch                                   # 작업↔세션 상태 + 드리프트(정체) 감지
oobs link "정렬 버그" --dir ~/dev/crow-backend  # 탭에서 띄운 세션을 작업에 등록
oobs open "정렬 버그"                          # 닫힌 세션 재개 명령 (살아있는 세션은 Agent View)
```

**urgency** 는 Taskwarrior 의 가중합을 볼트 스키마에 번안한 것 — 마감 21일 램프(×12) + 우선순위
+ 상태(진행 중 +4, 보류 −3 등) + 나이. `new` 는 **유사 제목의 진행 작업이 있으면 생성을 거부**한다
(중복 작업 방지, 정말 새 작업이면 `--force`).

모든 쓰기는 원자적(temp + rename) — 모바일 동기화 도입에 대비.
frontmatter 스키마·상태값은 `~/vault/CLAUDE.md` 와 동일하게 유지한다.

## 관제탑 — 작업 ↔ Claude Code 세션 연결

작업 노트를 **Claude Code 세션과 연결**해 볼트를 작업 오케스트레이션 관제탑으로 쓴다.
연결은 노트 frontmatter 의 `session:`(세션 UUID) — **데이터이지 프로세스 소유가 아니다.**
그래서 관제(노트 관찰)와 운전(세션 안 작업)이 서로 독립적으로 굴러간다 — 관제탑을 닫아도 하위 세션은 살아있다.

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
관제탑은 순수 관제 — 하위 세션을 spawn 하거나 운전하지 않는다(띄우기는 사용자가 탭에서, 운전은 Agent View).

- `oobs watch` — 작업+세션 상태를 합친 보드. 진행 중인데 세션이 없거나 2일+ 정체면 **드리프트** 경고
- `oobs link "<작업>" --dir <레포>` — 그 디렉터리에서 방금 띄운 세션을 자동 연결 (uuid 직접 지정도 가능)
- `oobs open "<작업>"` — **닫힌** 세션 재개 명령(`claude --resume`). 살아있는 세션이면 Agent View 에서 attach 하라고 안내
- `/oobs-tower` — 이 세션을 관제탑 운영관으로(종합·드리프트·등록·리포트만)

세션 라이브 상태는 `claude agents --json`(Agent View)에서 읽고, claude 가 없으면 전사파일 mtime 으로 추정한다
(선택 통합 — 코어는 claude 를 모른다, 미러와 같은 subprocess 경계).

## 의존성과 결합도

**oobs 코어는 standalone** — PyYAML 외 의존성이 없고, nacho/tako 없이 볼트만 있으면 완결 동작한다.
nacho 결합은 `mirror.py` 한 파일에 격리돼 있고 import 가 아닌 subprocess 호출(프로세스 경계)이라
nacho 내부를 전혀 모른다. 들어낼 때는:

1. 운영상 끄기: `config.yaml` 의 `mirror: false` (코드 무변경)
2. 완전 제거: `oobs/mirror.py` 삭제 + `main.py` 의 `mirror.enabled()` guard 2곳 삭제 + config `nacho:` 섹션 삭제

## 설계 — 왜 MCP 서버가 아니라 CLI + 얇은 스킬인가

(nacho · tako 와 공통 설계 원칙)

MCP 의 컨텍스트 비용은 호출이 아니라 **상주**에서 나간다. MCP 서버를 붙이면 도구 스키마
(이름·설명·파라미터 JSON)가 모든 세션의 시스템 프롬프트에 실린다 — 공식 Notion/Atlassian
MCP 는 도구 20개 안팎이라 *쓰지 않는 세션에서도* 수천~만 토큰을 차지할 수 있다.
CLI + 얇은 스킬 구조는 그 상주 비용을 호출 시점 비용으로 바꾼다:

- **상주 비용**: 스킬 설명 한 줄(수십 토큰)뿐. 사용법 지식은 `/oobs` 호출 순간에만 로드
- 호출당 비용(도구 호출 + 결과)은 MCP 와 비슷 — 절약분은 전적으로 상주 스키마
- **세션 밖 셸 직접 호출 = 토큰 0** + 결정적 동작 + 테스트/버전 관리 가능
- oobs 는 어차피 로컬 파일 조작이라 MCP 서버를 끼우면 순수 오버헤드

정직한 트레이드오프:

- 최신 Claude Code 는 MCP 도구를 지연 로딩(ToolSearch)하므로 상주 격차가 예전만큼 크지 않다
- MCP 가 이기는 지점도 있다 — 타입 스키마로 잘못된 호출 감소, 인증·상태를 서버가 관리,
  외부 서비스 연동은 벤더가 유지보수. CLI 래핑(nacho 의 Notion API, tako 의 Jira API)은
  API 가 바뀌면 직접 고쳐야 한다 (oobs 는 로컬 파일이라 이 부담이 없음)

## 노션 미러 (병행 기간, 선택 기능)

`new`/`note`/`done` 은 같은 내용을 nacho 로 노션에도 보낼 수 있다.

- 스위치: `~/.config/oobs/config.yaml` 의 `mirror:` — `auto`(기본, nacho 있으면 미러) | `true` | `false`
- 일회성 제외: `--no-mirror`
- 노션 select 옵션에 없는 분류/프로젝트는 미러에서 자동 생략 (볼트에는 자유 값 기록)
- `note`/`done` 의 노션 검색어는 노트 H1 제목 사용 (파일명 하이픈 ↔ 노션 제목 공백 불일치 방지)
- 미러 실패는 경고만 — 볼트 기록(원본)은 항상 성공시킴

## 구조

```
oobs/
├── main.py    서브커맨드·플래그 (new/note/done/list/next/stats/prime/inbox + watch/link/open)
├── vault.py   frontmatter 파싱/직렬화, 원자적 쓰기, 데일리 노트, 검색, 세션 연결/관찰
├── mirror.py  nacho 비인터랙티브 호출 (빈 입력 stdin 공급)
└── config.py  ~/.config/oobs/config.yaml + 상태/우선순위 상수
commands/
├── oobs.md        /oobs       — 세션 맥락으로 작업 노트 생성
├── oobs-note.md   /oobs-note  — 진행 일지 기록
└── oobs-tower.md  /oobs-tower — 관제탑(종합·드리프트·등록·리포트)
```
