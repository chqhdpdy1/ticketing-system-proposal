# Term Project Proposal — Ticketing System

> 국민대학교 · Software Architecture · HW1 Project Proposal
> 제출 양식(강의자료)에 따라 1~7 항목으로 구성한 제안서입니다.

---

## 1. 프로젝트 팀 명

**Ticketing System**

---

## 2. 프로젝트 주제

### 주제명
**Ticketing System — 범용 선착순(First-Come-First-Served) 판매 플랫폼 (첫 번째 도메인: 영화관 티켓 예매)**

### 프로젝트 설명

한정된 재고를 **짧은 시간에 다수의 사용자가 동시에 구매하려는** 상황(선착순 판매)을
안정적으로 처리하는 **범용 판매 플랫폼**을 설계·구현한다.

선착순 판매는 도메인(영화 좌석, 공연 좌석, 한정판 상품)이 달라도 다음과 같은
**공통 문제**를 공유한다.

- **동시성(Concurrency):** 같은 재고 단위(좌석/상품)를 여러 사용자가 동시에 구매 → **정확히 1명에게만** 판매되어야 함 (초과 판매 = 재고 -1 은 절대 금지).
- **폭주(Burst Traffic):** 판매 오픈(예: 인기 영화 예매 시작) 순간 트래픽이 평소의 수십~수백 배로 급증.
- **공정성(Fairness):** 먼저 온 요청이 먼저 처리되어야 함(대기열).
- **일관성(Consistency):** 결제 실패/타임아웃 시 선점한 재고를 되돌려야 함.

본 프로젝트는 이 공통 문제를 해결하는 **도메인 독립적 판매 엔진(Core Sales Engine)** 을
설계하고, 그 위에 **영화관 티켓 예매 도메인**을 첫 번째 어댑터로 구현한다.
이후 공연 티켓·한정판 상품 도메인은 **어댑터 추가만으로 확장**되도록 한다.

- 결제·문자·PG 등 외부 연동은 **더미(Mock)** 로 처리하여 학습 목적에 집중한다.
- 대규모 트래픽 대응(대기열, 재고 캐시, 분산 락)을 아키텍처 차원에서 다룬다.

---

## 3. 팀 구성

**1인 팀**으로 진행한다.

| 이름 | 학번 | 소속 | 학년 | 역할 |
|------|------|------|------|------|
| 홍석준 | 20213098 | 소프트웨어학과 | 4학년 | 전체(설계·백엔드·인프라·문서) |

### 프로젝트에서의 역할 (1인 팀, 단계적 수행)

- **아키텍처 설계:** 범용 판매 코어와 도메인 어댑터 구조 설계, 아키텍처 스타일·패턴 선정.
- **백엔드 개발:** 동시성 제어 엔진(재고 원자 차감·대기열·선점), 도메인 어댑터·REST API 구현.
- **인프라·검증:** Redis/PostgreSQL/Docker 구성, 부하 테스트 및 관측성 세팅.
- **문서화:** 제안서·설계서·검증 결과 정리.

### 강점 및 경험

- 소프트웨어학과 4학년으로 소프트웨어 아키텍처·설계 원칙(SOLID/GRASP/디자인 패턴) 학습.
- Spring Boot / JPA 기반 REST API 및 관계형 DB 트랜잭션·락 학습 경험.
- 동시성 제어와 대규모 트래픽 처리 아키텍처에 대한 관심과 학습 의지.

---

## 4. 목적하는 소프트웨어 시스템의 목표 (Vision & Scope)

### 4.1 Vision (비전)

> "**하나의 판매 엔진으로 모든 선착순 판매를 공정하고 정확하게.**"
>
> 도메인에 종속되지 않는 **재사용 가능한 선착순 판매 코어**를 만들고,
> 초과 판매 없이(정확성), 폭주 트래픽에서도 죽지 않고(가용성),
> 먼저 온 사용자가 먼저 사도록(공정성) 보장하는 시스템을 목표로 한다.

### 4.2 Scope (범위)

**In Scope (이번 프로젝트 범위)**

- 범용 선착순 판매 코어 엔진 (판매 이벤트 / 재고 / 선점 / 주문)
- 동시성 제어 (DB 비관적 락 → Redis 원자적 재고 차감 → 대기열)
- 영화관 도메인 어댑터 (상영/좌석/예매/발권)
- 사용자·인증(간단), 판매자(어드민) 최소 기능
- Mock 결제, Mock 알림
- 부하 테스트 및 관측성(메트릭/로그) 최소 구성

**Out of Scope (제외)**

- 실제 PG(결제대행) 연동, 실제 SMS/이메일 발송
- 추천, 광고, 정산·세금계산서 등 커머스 부가 기능
- 모바일 네이티브 앱 (웹으로 대체)

### 4.3 As-Is / To-Be

| 구분 | As-Is (기존 관행) | To-Be (본 프로젝트) |
|------|-------------------|---------------------|
| 아키텍처 | 도메인마다 판매 로직을 매번 새로 구현 | **범용 판매 코어 + 도메인 어댑터**로 재사용 |
| 동시성 | 단순 `SELECT then UPDATE` → 초과 판매 발생 | **원자적 차감 + 락 + 대기열**로 초과 판매 0 |
| 폭주 대응 | 오픈 순간 DB 과부하로 응답 지연/장애 | **대기열 + 캐시**로 DB 부하 평탄화 |
| 재고 정합성 | 결제 실패 시 재고 누수/유령 좌석 | **TTL 선점 + 보상 트랜잭션**으로 자동 복구 |
| 확장성 | 새 도메인 = 전체 재개발 | 새 도메인 = **어댑터 1개 추가** |

---

## 5. 시스템 개요 및 특성

### 5.1 개요 및 특성 리스트

- **레이어드 + 헥사고날(Ports & Adapters)** 구조로 코어/도메인/인프라 분리.
- 판매 코어는 **도메인 이벤트 기반**으로 도메인 어댑터와 느슨하게 결합.
- 재고 차감은 **원자적 연산**(DB row lock 또는 Redis Lua)으로 초과 판매 방지.
- 판매 오픈 시 **가상 대기열(Waiting Queue)** 로 유입량을 제어.
- 선점(Hold)은 **TTL**을 가지며 만료 시 자동 반환(스케줄러/이벤트).
- 결제/알림은 **인터페이스 + Mock 구현체**로 대체(테스트 용이).

### 5.2 Use Case 별 Functional Requirements (FR)

> 강의자료 표 양식: Use Case / Role & Responsibility / Attributes / FR / 적용 가능한 Architecture Style·GRASP·SOLID·Design Pattern / NFR(Quality Attributes)

| Use Case | Role & Responsibility | 처리 정보 (Attributes) | Functional Requirements | Architecture / GRASP / SOLID / Design Pattern | NFR (Quality Attributes) |
|---|---|---|---|---|---|
| **UC-1 판매 이벤트 조회** | 사용자가 오픈 예정/진행 중 판매(상영) 목록을 본다 | SalesEvent(id, title, openAt, status), Inventory 요약 | 판매 목록/상세 조회, 오픈 카운트다운 | Layered / **Information Expert** / Repository, DTO | 성능(응답 300ms), 캐시 활용 |
| **UC-2 대기열 진입** | 오픈 순간 몰린 사용자를 순서대로 입장시킨다 | 사용자ID, 대기순번, 토큰, 진입시각 | 대기표 발급, 순번·예상시간 안내, 입장 허용 | Pipe(큐) / **Controller** / **Strategy**(입장정책) | 공정성(FIFO), 가용성, 확장성 |
| **UC-3 재고(좌석) 선점** | 사용자가 좌석/상품을 임시 점유한다 | Seat/Item id, hold TTL, userId | **원자적** 재고 차감, 중복 선점 방지, TTL 만료 반환 | **Ports&Adapters** / **Low Coupling** / **State**(재고상태) | **정확성(초과판매 0)**, 동시성, 신뢰성 |
| **UC-4 주문·결제(Mock)** | 선점을 확정 구매로 전환한다 | Order(id, amount, status), payment token | 결제 요청(Mock), 성공 시 확정·실패 시 선점 해제 | **Facade** / **Adapter**(PG) / **Template Method** | 신뢰성(보상 트랜잭션), 정합성 |
| **UC-5 발권/확인** | 구매 완료 후 티켓을 발급/조회한다 | Ticket(code, seat, screening) | 티켓 코드 발급, 예매 내역 조회 | **Factory Method** / **Creator** | 유지보수성, 성능 |
| **UC-6 판매 등록(어드민)** | 판매자가 상영/좌석/재고를 등록한다 | Screening, Seat layout, price, openAt | 상영·좌석·가격·오픈시각 등록, 재고 초기화 | Layered / **Builder** / **Repository** | 보안(권한), 유지보수성 |
| **UC-7 취소·환불(Mock)** | 사용자가 예매를 취소한다 | Order/Ticket status, refund(Mock) | 취소 요청, 재고 복원, 환불(Mock) | **Command** / **Observer**(재고복원 이벤트) | 정합성, 신뢰성 |

### 5.3 추가 NFR (Quality Attributes)

| # | Quality Attribute | 요구 시나리오 (측정 가능한 목표) | 달성 전술(Tactic) |
|---|---|---|---|
| NFR-1 | **정확성 / 데이터 무결성** | 동시 1만 요청에도 **재고 초과 판매 = 0** | 원자적 차감(Redis Lua/DB row lock), 유니크 제약 |
| NFR-2 | **가용성(Availability)** | 판매 오픈 피크에도 오류율 < 1% | 대기열로 유입 제어, 서킷브레이커, 타임아웃 |
| NFR-3 | **성능(Performance)** | 재고 조회 p95 < 300ms, 선점 p95 < 500ms | 캐시(Redis), 커넥션 풀, 인덱스 |
| NFR-4 | **확장성(Scalability)** | 인스턴스 수평 확장으로 처리량 선형 증가 | 무상태 API, 분산 락, 큐 |
| NFR-5 | **공정성(Fairness)** | 요청 도착 순서대로 처리(FIFO 근사) | 대기열 순번 토큰 |
| NFR-6 | **일관성(Consistency)** | 결제 실패/타임아웃 시 100% 재고 복원 | TTL 선점 + 보상 트랜잭션 + 아웃박스 |
| NFR-7 | **유지보수성/확장성(Modifiability)** | 새 도메인 추가 시 코어 코드 수정 0 | Ports & Adapters, DIP |
| NFR-8 | **관측성(Observability)** | 재고/대기열/오류를 실시간 지표로 확인 | 메트릭, 구조적 로그, 트레이스 |
| NFR-9 | **보안(Security)** | 인증·권한 분리, 봇/중복요청 방지 | JWT, 요청 rate limit, 멱등키 |

---

## 6. 사용 기술 및 Framework

> 상세 내용은 `docs/02-architecture.md`, `docs/04-tech-stack.md` 참고.

### 6.1 관심 있는 소프트웨어 시스템 조사 개요

대규모 선착순/이벤트성 판매를 다루는 대표 시스템으로 **인터파크 티켓, 예스24, 
Ticketmaster** 등 티켓팅 플랫폼과, 한정판 판매를 다루는 **Nike SNKRS**,
급증 트래픽을 다루는 커머스 **쿠팡·배달의민족(주문)** 등이 참고 대상이다.
이들은 공통적으로 **대기열(Virtual Waiting Room)**, **인메모리 재고 캐시**,
**메시지 큐 기반 비동기 처리**, **읽기/쓰기 분리** 아키텍처를 사용한다.

### 6.2 참조 아키텍처 스타일

- **Layered Architecture** — Presentation / Application / Domain / Infrastructure 분리.
- **Ports & Adapters (Hexagonal)** — 코어를 외부(DB, PG, 도메인)로부터 격리.
- **Event-Driven** — 재고 복원·발권·알림을 도메인 이벤트로 비동기 처리.
- **CQRS 경량 적용** — 조회(캐시)와 명령(선점/주문) 경로 분리.

### 6.3 사용 기술 스택 (안)

| 구분 | 기술 | 이유 |
|------|------|------|
| Language / Framework | **Java 17 + Spring Boot 3** (또는 Kotlin) | 트랜잭션·동시성 자료 풍부, 학습 자원 많음 |
| Persistence | **Spring Data JPA + PostgreSQL** | 관계형 정합성, 비관적/낙관적 락 지원 |
| Cache / Lock / Queue | **Redis** (Lua 원자 연산, 분산 락, 대기열) | 대규모 트래픽 재고·대기열 처리 핵심 |
| Async Messaging | **Redis Stream / (선택)Kafka** | 이벤트 기반 비동기 처리 |
| API | **REST (OpenAPI/Swagger)** | 표준적·검증 용이 |
| Frontend | **React + Vite** (최소 화면) | 대기열·예매 흐름 데모 |
| Test / Load | **JUnit5, Testcontainers, k6/JMeter** | 동시성·부하 검증 |
| Infra | **Docker Compose** | 로컬 재현, 다중 인스턴스 데모 |
| Observability | **Micrometer + Prometheus + Grafana** | 재고/대기열/오류 지표 |

### 6.4 조사 시스템에서 차용할 부분

- 티켓팅 플랫폼의 **가상 대기열(Virtual Waiting Room)** 개념 → 대기열 모듈로 구현.
- 커머스의 **인메모리 재고 차감 + 후속 DB 반영(write-behind)** 패턴 차용.
- **아웃박스 패턴 / 보상 트랜잭션**으로 결제-재고 정합성 확보.

---

## 7. Reference (참고문헌)

1. Bass, L., Clements, P., Kazman, R. *Software Architecture in Practice* (4th ed.), Addison-Wesley.
2. Larman, C. *Applying UML and Patterns* (GRASP), Prentice Hall.
3. Gamma et al. *Design Patterns: Elements of Reusable OO Software* (GoF).
4. Evans, E. *Domain-Driven Design*, Addison-Wesley.
5. Redis 공식 문서 — Distributed Locks, Lua scripting, Streams. https://redis.io/docs/
6. Spring Framework Reference — Transaction Management, Locking. https://docs.spring.io/
7. Richardson, C. *Microservices Patterns* (Saga, Outbox), Manning.
8. Cloudflare / AWS "Virtual Waiting Room" 아키텍처 문서. https://aws.amazon.com/solutions/implementations/virtual-waiting-room-on-aws/

> ※ 참고 자료의 서지정보는 실제 인용 판본/URL 접속일에 맞춰 최종 확정하세요.
