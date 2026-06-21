# -*- coding: utf-8 -*-
"""oobs help — 빈 터미널에서 바로 보는 사용 설명서 (argparse --help 보다 예시 중심)."""

OVERVIEW = """\
oobs — 옵시디언 관제탑 볼트(~/vault) 작업 노트 CLI

자주 쓰는 흐름
  작업 시작    oobs new --title "WL-1234 정렬 버그" --due 2026-06-30 --note "원인 파악 중"
  진행 기록    oobs note "정렬" "PR 머지, 스테이징 검증 중" --status "배포 대기"
  완료/취소    oobs done "정렬" "운영 배포 완료"          (취소는 --cancel)
  현황 한눈에  oobs list           진행 작업 표
              oobs next           지금 뭐부터? (urgency 순위)
              oobs stats          마감 초과·정체(14일+) 감지
  세션 시작    oobs prime          새 Claude 세션에 주입할 현황 다이제스트
  세션 관제    oobs watch          작업↔세션 상태 + 드리프트(정체) 감지
              oobs link "정렬" --dir ~/dev/crow-backend   탭에서 띄운 세션을 작업에 등록
              oobs open "정렬"    닫힌 세션 재개 명령 (살아있는 세션은 Agent View 에서 attach)
  빠른 메모    oobs inbox 갑자기 생각난 것

명령 상세     oobs help <명령>     예: oobs help new
상태값        시작 전 | 진행 중 | 배포 대기 | 모니터링 | 의사결정 대기 | 보류 | 취소 | 완료
검색어        note/done 의 <검색어>는 tasks/ 파일명 부분일치 (없으면 본문 검색)
설정          ~/.config/oobs/config.yaml — vault 경로, 노션 미러(auto|true|false)
연동          Claude 세션에서는 /oobs, /oobs-note 슬래시 커맨드가 같은 일을 함\
"""

DETAILS = {
    "new": """\
oobs new — 작업 노트 생성 (tasks/ 노트 + 데일리 로그 + 노션 미러)

  oobs new --title "WL-1234 정렬 버그 수정"
  oobs new --title "캐싱 도입" --status "시작 전" --due 2026-06-30 \\
           --repo danbi_server --priority high --note "설계 검토부터"

주요 플래그
  --title     (필수) 노트 제목 — 파일명이 됨. : / \\ | # ^ [ ] 금지
  --status    기본 "진행 중"
  --due / --scheduled   YYYY-MM-DD
  --note      현황 요약 한 줄 (대시보드 컬럼에 표시)
  --category  리팩토링|기존기능개선|신규기능개발|운영 외 자유 값도 가능 (미러에선 생략됨)
  --link      Jira 등 대표 URL 1개
  --body      본문 마크다운 (진행 일지 섹션은 자동 생성되니 넣지 말 것)
  --force     유사 제목 진행 작업이 있어도 강제 생성 (기본은 중복 감지로 거부)
  --no-mirror / --no-daily

비슷한 작업이 이미 있다고 거부되면 → 그 작업의 연장이면 oobs note 로 기록\
""",
    "note": """\
oobs note — 진행 일지 한 줄 + 현황 요약 갱신

  oobs note "정렬 버그" "PR 머지, 스테이징 검증 중"
  oobs note "정렬" "기획 검토 요청 보냄" --status "의사결정 대기"

  <검색어>   tasks/ 파일명 부분일치. 여러 개 걸리면 번호 선택 (--first 로 첫 결과)
  <메모>     한 줄 (60자 권장) — 진행 일지에 append + 현황 요약 덮어쓰기 + 노션 미러
  --status   상태도 같이 변경. 완료/취소로 바꾸면 completed 기록 + 데일리 로그까지\
""",
    "done": """\
oobs done — 완료/취소 처리 (completed 날짜 + 데일리 로그 + 노션 미러)

  oobs done "정렬 버그" "운영 배포 완료"
  oobs done "캐싱" --cancel            # 취소 처리
  메모 생략 시 "완료"/"취소" 로 기록\
""",
    "list": """\
oobs list — 작업 현황 표 (옵시디언 앱 꺼져 있어도 동작)

  oobs list                    진행 작업만
  oobs list --all              완료/취소 포함 전체
  oobs list --status "보류"    특정 상태만\
""",
    "next": """\
oobs next — 지금 뭐부터? urgency 상위 N (기본 5)

  oobs next
  oobs next 3

urgency = 마감 근접도(21일 램프 ×12) + 우선순위(high 6 / normal 3.9 / low 1.8)
        + 상태(배포 대기 +5, 진행 중 +4, 보류 -3 등) + 작업 나이(최대 +2)\
""",
    "stats": """\
oobs stats — 한 줄 건강 진단

  진행/종료 카운트(상태별) + ⚠️ 마감 초과 + 💤 14일 이상 진행 일지 미갱신(정체) 목록\
""",
    "prime": """\
oobs prime — 세션 시작용 볼트 현황 다이제스트 (markdown)

  oobs prime              # 진행 작업(urgency 순+플래그) + 오늘/어제 데일리 로그 + inbox
  oobs prime --log-lines 20

새 Claude 세션 첫마디로 "oobs prime 봐줘" 하면 작업 맥락이 바로 복원됨\
""",
    "inbox": """\
oobs inbox — 분류 고민 없이 일단 던져두기

  oobs inbox 결제 모듈 리팩토링 아이디어
  → inbox/2026-06-11-결제-모듈-리팩토링-아이디어.md 생성
  나중에 Claude 세션에서 "inbox 정리해줘" 로 task 승격/폐기\
""",
    "link": """\
oobs link — 작업 노트에 Claude Code 세션 연결 (관제탑 ↔ 운전 세션)

  oobs link "정렬 버그" ae09087-...           # uuid 직접 지정
  oobs link "정렬 버그" --dir ~/dev/crow-backend  # uuid 생략 → 그 디렉터리 최근 세션 자동
  oobs link "정렬 버그" --name WL-1234         # Agent View 표시명

연결은 '데이터'(노트 frontmatter 의 session/session_dir)이지 프로세스가 아님 —
관제(노트 관찰)와 운전(세션 안 작업)이 독립적으로 굴러간다.\
""",
    "open": """\
oobs open — 닫힌 세션 재개 명령 (들어가기/운전은 Agent View 담당)

  oobs open "정렬 버그"        # cd <dir> && claude --resume <uuid> -n <이름> 출력
  oobs open "정렬 버그" --exec # 출력 대신 직접 실행 (셸에서만, 관제탑 세션 안에선 금지)

세션 상태로 갈린다:
  - 살아있는 세션  → 'claude agents'(Agent View)에서 attach 안내 + 필요 시 --fork-session
  - 닫힌 세션      → claude --resume 명령 출력 (open 의 본래 용도)
미연결이면 oobs link 안내. 살아있는 세션 운전은 Agent View 가 이미 잘 하므로 open 은 보조.\
""",
    "watch": """\
oobs watch — 작업 + 연결 세션 상태를 합친 관제 보드

  oobs watch
  🔵 진행 중  정렬버그  세션 ae09087 · 활성(방금)        ~2026-06-30
  🔵 진행 중  캐싱도입  세션 없음 ⚠️ 드리프트

진행 중인데 세션이 없거나 2일+ 정체면 '드리프트'로 경고 — 멈춘 일이 조용히 썩는 걸 먼저 집어줌.\
""",
    "help": "oobs help [명령] — 이 설명서. 명령 이름을 주면 상세 + 예시.",
}


def show(topic: str | None) -> int:
    if not topic:
        print(OVERVIEW)
        return 0
    text = DETAILS.get(topic)
    if not text:
        print(f"'{topic}' 은 모르는 명령. 가능: {', '.join(DETAILS)}")
        return 1
    print(text)
    return 0
