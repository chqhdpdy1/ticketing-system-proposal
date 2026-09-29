# Ticketing System — 범용 선착순 판매 플랫폼

> 한정된 재고를 다수의 사용자가 동시에 구매하는 **선착순(First-Come-First-Served) 판매**를
> 정확·공정·안정적으로 처리하는 **도메인 독립적 판매 플랫폼**.
> 첫 번째 도메인으로 **영화관 티켓 예매**를 구현하며, 공연 티켓·한정판 상품으로 확장 가능하도록 설계.

국민대학교 Software Architecture Term Project (현재: HW1 Proposal / 설계 단계).

> 🧭 **새 세션에서 이어가려면 [`PROJECT_STATE.md`](PROJECT_STATE.md) 를 먼저 읽으세요.**
> 변경 이력은 [`CHANGELOG.md`](CHANGELOG.md) 에 있습니다.

---

## 핵심 아이디어

- **범용 코어 + 도메인 어댑터**: 판매 코어(재고/선점/주문/결제)는 도메인을 모르고,
  영화관·공연·상품은 어댑터로 붙는다. → 새 도메인 추가 시 **코어 무수정**.
- **초과 판매 0**: 재고 차감을 단일 원자적 연산(Redis Lua / DB row-lock)으로.
- **폭주 대응**: 가상 대기열로 유입을 평탄화.
- **정합성**: TTL 선점 + 보상 트랜잭션(Saga) + Outbox.

## 아키텍처 한눈에

```
Client(React) → API Gateway(JWT, RateLimit)
        ├─ Waiting Queue Service (Redis Sorted Set)
        └─ Sales Core (Hexagonal: Ports & Adapters)
               ├─ Redis (재고 원자차감/락/대기열/스트림)
               ├─ PostgreSQL (영속 상태/주문원장/Outbox)
               └─ Worker (write-behind, 발권, 선점만료 복원, 보상 Tx)
```

- 스타일: **Layered + Hexagonal + Event-Driven + 경량 CQRS**
- 방어선 3단계: **가상 대기열 → 원자적 재고 차감 → TTL 선점 + Saga**

## 폴더 구조

```
├── PROJECT_STATE.md   이어가기 진입점 (새 세션은 여기부터)
├── CHANGELOG.md       변경 이력 (무엇을/왜)
├── report/            📄 제출용 보고서 (proposal-submit.md + HTML)
├── design/
│   ├── current/       🏗️ 최신 설계 (여기를 수정)
│   ├── versions/      과거 설계 스냅샷 (읽기전용 보존)
│   └── full-design.html  전체 설계 HTML
└── tools/             문서→HTML 빌드 스크립트
```

## 설계 문서 (design/current/)

| 문서 | 내용 |
|------|------|
| [01-project-proposal.md](design/current/01-project-proposal.md) | **제안서** (팀/주제/Vision·Scope/As-Is·To-Be/UC별 FR·NFR 표/기술) |
| [02-architecture.md](design/current/02-architecture.md) | **아키텍처 설계** (구성도, 컴포넌트, 대규모 트래픽 대응, 시퀀스, SOLID/GRASP/패턴) |
| [03-domain-model.md](design/current/03-domain-model.md) | **도메인 모델/데이터** (코어↔영화관 매핑, ERD, 스키마, 상태전이, REST API) |
| [04-tech-stack.md](design/current/04-tech-stack.md) | **기술 스택/참조 시스템 조사** + 검증 계획 |

## 제출용 보고서 (report/)

- [report/proposal-submit.md](report/proposal-submit.md) — 과제 요구 항목만 담은 간결 제안서.
- `report/Ticketing-System-Proposal.html` — 브라우저에서 열고 `Ctrl+P → PDF로 저장`.

## 문서 → HTML 생성

```
python3 tools/build_submit.py   # report/ 제출용 HTML 재생성
python3 tools/build_html.py     # design/ 전체 설계 HTML 재생성
```

## 기술 스택 (안)

Java 17 · Spring Boot 3 · Spring Data JPA · PostgreSQL · Redis · React(Vite) ·
JUnit5/Testcontainers · k6 · Docker Compose · Prometheus/Grafana

## 확장 로드맵

1. **영화관 티켓** (첫 도메인, 좌석 지정) ← 현재
2. 공연 티켓 (좌석/구역)
3. 한정판 상품 드롭 (수량 선착순)

각 단계는 `DomainDescriptorPort` 구현 + 재고 초기화만 추가.

---

### 다음 단계(구현 착수 시)

- [ ] Spring Boot 프로젝트 스캐폴딩 (멀티모듈: core / cinema-adapter / api / worker)
- [ ] 코어 포트/도메인 엔티티 + JPA 매핑
- [ ] Redis Lua 재고 차감 + 대기열
- [ ] Mock 결제/알림 어댑터
- [ ] docker-compose + k6 부하 시나리오
