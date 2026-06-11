# oobs

옵시디언 관제탑 볼트(`~/vault`)의 작업 노트를 생성·갱신·조회하는 CLI.
nacho(노션)·tako(Jira)와 같은 패턴 — **결정적인 파일 조작은 코드가, 세션 맥락 요약은 Claude 슬래시 커맨드가** 담당한다.

## 설치

```bash
./install.sh
```

venv 설치 + `~/.local/bin/oobs` 링크 + `/oobs`·`/oobs-note` 슬래시 커맨드 등록 + `~/.config/oobs/config.yaml` 생성.

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
```

**urgency** 는 Taskwarrior 의 가중합을 볼트 스키마에 번안한 것 — 마감 21일 램프(×12) + 우선순위
+ 상태(진행 중 +4, 보류 −3 등) + 나이. `new` 는 **유사 제목의 진행 작업이 있으면 생성을 거부**한다
(중복 작업 방지, 정말 새 작업이면 `--force`).

모든 쓰기는 원자적(temp + rename) — 모바일 동기화 도입에 대비.
frontmatter 스키마·상태값은 `~/vault/CLAUDE.md` 와 동일하게 유지한다.

## 의존성과 결합도

**oobs 코어는 standalone** — PyYAML 외 의존성이 없고, nacho/tako 없이 볼트만 있으면 완결 동작한다.
nacho 결합은 `mirror.py` 한 파일에 격리돼 있고 import 가 아닌 subprocess 호출(프로세스 경계)이라
nacho 내부를 전혀 모른다. 들어낼 때는:

1. 운영상 끄기: `config.yaml` 의 `mirror: false` (코드 무변경)
2. 완전 제거: `oobs/mirror.py` 삭제 + `main.py` 의 `mirror.enabled()` guard 2곳 삭제 + config `nacho:` 섹션 삭제

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
├── main.py    서브커맨드·플래그
├── vault.py   frontmatter 파싱/직렬화, 원자적 쓰기, 데일리 노트, 검색
├── mirror.py  nacho 비인터랙티브 호출 (빈 입력 stdin 공급)
└── config.py  ~/.config/oobs/config.yaml + 상태/우선순위 상수
```
