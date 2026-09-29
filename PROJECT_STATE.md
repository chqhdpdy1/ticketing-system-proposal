# PROJECT STATE — 다음 세션이 가장 먼저 읽는 파일

> 이 파일은 새 대화(세션)에서 작업을 이어가기 위한 진입점입니다.
> 새 세션을 시작하면 이 파일 → CHANGELOG.md → design/current/ 순서로 읽으세요.

---

## 1. 프로젝트 한 줄 요약

**Ticketing System** — 범용 선착순(First-Come-First-Served) 판매 플랫폼.
첫 도메인은 **영화관 티켓 예매**이며, 이후 공연 티켓·한정판 상품으로 확장 가능하게 설계.
국민대 Software Architecture 과목 Term Project.

- 팀: 1인 (홍석준 / 20213098 / 소프트웨어학과 4학년)
- 대규모 트래픽 대응 + 초과 판매 0 이 핵심 도전 과제.
- 결제/알림 등 외부 연동은 Mock(더미)으로 처리.

## 2. 지금까지 진행 상황 (현재 단계)

- **[완료] HW1 제안서(Project Proposal)** — 제출용 문서 작성 완료.
- **[완료] 설계 문서 v1.0** — 아키텍처/도메인모델/기술스택 초안 작성 완료.
- **[예정] 향후** — 설계 상세화, 코드 스캐폴딩(Spring Boot), 동시성 엔진 구현.

> 아직 실제 코드 구현은 시작 전. 문서/설계 단계.

## 3. 폴더 구조 (중요)

```
/
├── PROJECT_STATE.md          ← (이 파일) 이어가기 진입점
├── CHANGELOG.md              ← 무엇을/왜 바꿨는지 변경 이력
├── README.md                 ← 프로젝트 개요
│
├── report/                   ← 📄 제출용 보고서 (과제 제출물)
│   ├── proposal-submit.md            제출용 간결 제안서 (원본)
│   └── Ticketing-System-Proposal.html 제출용 HTML (브라우저 인쇄→PDF)
│
├── design/                   ← 🏗️ 설계 문서
│   ├── current/                      최신 설계 (여기를 수정하며 발전)
│   │   ├── 01-project-proposal.md
│   │   ├── 02-architecture.md
│   │   ├── 03-domain-model.md
│   │   └── 04-tech-stack.md
│   ├── versions/                     설계 버전 스냅샷 (과거 보존, 읽기전용)
│   │   └── v1.0-2026-09-29/           ← v1.0 스냅샷
│   └── full-design.html              전체 설계 HTML (참고용)
│
└── tools/                    ← 🔧 문서→HTML 빌드 스크립트
    ├── build_submit.py               report/ HTML 생성
    └── build_html.py                 design/ 전체 HTML 생성
```

## 4. 핵심 설계 결정 (요약 — 상세는 design/current/)

- **아키텍처 스타일:** Layered + Ports & Adapters(Hexagonal) + Event-Driven + 경량 CQRS.
- **범용성:** 도메인 독립 코어 + 도메인 어댑터. 새 도메인 = `DomainDescriptorPort` 구현만 추가(코어 무수정).
- **대규모 트래픽 3단계 방어선:**
  1. 가상 대기열(Redis Sorted Set)로 유입 평탄화
  2. 원자적 재고 차감(Redis Lua / DB row-lock)으로 초과 판매 0
  3. TTL 선점 + 보상 트랜잭션(Saga) + Outbox 로 정합성
- **기술 스택:** Java 17 + Spring Boot 3 + PostgreSQL + Redis + React, Docker Compose, k6.

## 5. 작업 규칙 (다음 세션이 지킬 것)

1. **설계를 수정할 때:**
   - `design/current/` 의 파일을 수정한다.
   - 의미 있는 변경(구조/결정이 바뀜)이면, 수정 **전** 상태를 `design/versions/vX.Y-YYYY-MM-DD/` 에 스냅샷으로 복사해 보존한다.
   - `CHANGELOG.md` 에 **무엇을 / 왜** 바꿨는지 한 항목 추가한다.
   - 필요 시 이 `PROJECT_STATE.md` 의 요약도 갱신한다.
2. **보고서를 갱신할 때:**
   - `report/proposal-submit.md` 수정 → `python3 tools/build_submit.py` 로 HTML 재생성.
3. **HTML 재생성 명령:**
   - 제출본: `python3 tools/build_submit.py` → `report/Ticketing-System-Proposal.html`
   - 상세본: `python3 tools/build_html.py` → `design/full-design.html`
4. **커밋 메시지:** `<type>: <무엇>` + 본문에 **왜**. type 예: `docs`, `design`, `report`, `chore`.
5. **PDF 생성:** 이 환경(클라우드 샌드박스)은 한글 폰트/네트워크가 없어 PDF 직접 생성 불가.
   → HTML을 브라우저에서 열고 `Ctrl+P → PDF로 저장` (사용자 PC에서).

## 6. 알려진 환경 제약

- 샌드박스에 **한글 폰트 없음 + 외부 네트워크 차단** → PDF·패키지 설치 불가. 브라우저 인쇄로 우회.
- GitHub **리포 생성 권한 없음**(403). 기존 리포 push/PR 은 가능.
- 리포: `chqhdpdy1/ticketing-system-proposal` (default branch: main)
