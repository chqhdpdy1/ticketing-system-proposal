# 시스템 아키텍처 설계

> 범용 선착순(FCFS) 판매 플랫폼 — 첫 도메인: 영화관 티켓 예매
> 본 문서는 아키텍처 스타일, 컴포넌트 구조, 대규모 트래픽 대응 설계, 핵심 시나리오를 다룬다.

---

## 1. 아키텍처 목표(요약)

| 목표 | 핵심 결정 |
|------|-----------|
| **초과 판매 0** | 재고 차감을 단일 원자적 연산으로 (Redis Lua / DB row-lock) |
| **폭주 대응** | 가상 대기열로 유입 평탄화 → DB/코어 보호 |
| **정합성** | TTL 선점 + 보상 트랜잭션(Saga) + Outbox |
| **확장성** | 무상태 API + 분산 락 + 수평 확장 |
| **도메인 확장** | 코어와 도메인을 Ports & Adapters로 분리 |

---

## 2. 아키텍처 스타일

본 시스템은 **복합 스타일**을 사용한다.

1. **Layered Architecture** — 관심사 분리(표현/응용/도메인/인프라).
2. **Ports & Adapters (Hexagonal)** — 판매 코어를 외부 기술·도메인으로부터 격리.
3. **Event-Driven** — 재고 복원/발권/알림을 도메인 이벤트로 비동기 처리.
4. **경량 CQRS** — 조회(캐시 우선)와 명령(선점/주문) 경로 분리.

### 왜 Hexagonal 인가 (범용성의 핵심)

"범용 선착순 판매"의 요구사항은 **코어 로직은 도메인을 몰라야 한다**는 것이다.
코어는 `재고를 원자적으로 1 줄인다`만 알고, 그 재고가 "영화 좌석"인지 "한정판 신발"인지는
**도메인 어댑터**가 결정한다. 이를 위해 코어는 **포트(인터페이스)** 만 노출하고,
도메인/기술은 **어댑터**로 그 포트를 구현한다 → **DIP(의존성 역전)** 적용.

---

## 3. 상위 수준 구성도 (C4 - Context / Container)

```
                          ┌─────────────────────────────────────────────┐
                          │                 Client (Web)                  │
                          │        React SPA (대기열/예매/좌석맵)          │
                          └───────────────────────┬───────────────────────┘
                                                  │ HTTPS / REST
                          ┌───────────────────────▼───────────────────────┐
                          │                  API Gateway                    │
                          │      (인증 JWT, Rate Limit, 라우팅)             │
                          └───────┬───────────────────────────────┬────────┘
                                  │                               │
             ┌────────────────────▼─────────┐        ┌────────────▼───────────────┐
             │       Waiting Queue Service   │        │      Sales API (Core)        │
             │  - 대기표 발급/입장 토큰        │        │  - 판매/재고/선점/주문       │
             │  - Redis Sorted Set 순번        │        │  - 도메인 어댑터 로딩         │
             └───────────────┬───────────────┘        └───┬──────────────┬──────────┘
                             │                            │              │
                             │           ┌────────────────▼───┐   ┌──────▼──────────┐
                             └──────────►│      Redis          │   │   PostgreSQL     │
                                         │  - 재고 캐시(원자차감)│   │  - 영속 상태     │
                                         │  - 분산 락           │   │  - 주문/결제원장 │
                                         │  - 대기열/스트림      │   └──────┬──────────┘
                                         └──────────┬──────────┘          │
                                                    │ Stream(event)        │
                                    ┌───────────────▼──────────────┐       │
                                    │        Worker / Consumer       │◄──────┘
                                    │  - 재고 DB 반영(write-behind)  │
                                    │  - 발권, 알림(Mock)            │
                                    │  - 선점 만료 복원, 보상 트랜잭션│
                                    └────────────────────────────────┘
```

---

## 4. 논리 컴포넌트 (레이어 + 헥사고날)

```
┌──────────────────────────── Presentation Layer ────────────────────────────┐
│  REST Controllers  |  DTO / Request-Response  |  Exception Handler          │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                    │  (uses Application Ports)
┌──────────────────────────── Application Layer ─────────────────────────────┐
│  Use Case Services:  EnterQueue, HoldStock, PlaceOrder, ConfirmPayment,     │
│                      CancelOrder, RegisterSalesEvent                        │
│  Transaction 경계 / 오케스트레이션 / 이벤트 발행                             │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                    │  (depends on Domain + Ports)
┌───────────────── Domain Layer (Core, 도메인 비종속) ────────────────────────┐
│  Entities/Aggregates:  SalesEvent, Inventory, StockUnit, Hold, Order        │
│  Domain Services:      StockDeductionPolicy, FairnessPolicy                 │
│  Domain Events:        StockHeld, OrderPlaced, PaymentConfirmed,            │
│                        HoldExpired, StockRestored                           │
│  Ports (interfaces):                                                        │
│    - StockRepositoryPort        (재고 원자 차감/복원)                        │
│    - QueuePort                  (대기열)                                     │
│    - PaymentPort                (결제)                                       │
│    - NotificationPort           (알림)                                       │
│    - DomainDescriptorPort       (도메인별 재고 단위 의미 해석)               │
└──────────────────────────────────┬──────────────────────────────────────────┘
                                    │  (implemented by Adapters)
┌──────────────────── Infrastructure / Adapters Layer ───────────────────────┐
│  Persistence Adapter (JPA/PostgreSQL)   │  Redis Adapter (Lua/Lock/Queue)   │
│  Payment Adapter (Mock)                 │  Notification Adapter (Mock)      │
│  ── Domain Adapters ──                                                       │
│    CinemaAdapter (상영/좌석)  |  ConcertAdapter(향후)  |  ProductAdapter(향후)│
└──────────────────────────────────────────────────────────────────────────────┘
```

### 핵심 포트 정의 (개념)

```java
// 재고 포트: 코어는 "원자적으로 1 줄인다"만 안다
public interface StockRepositoryPort {
    HoldResult tryHold(long stockUnitId, String userId, Duration ttl); // 원자적
    void restore(long stockUnitId);                                    // 복원
    int remaining(long salesEventId);                                  // 잔여 조회(캐시)
}

// 도메인 기술자 포트: 재고 단위가 "무엇"인지 도메인이 해석
public interface DomainDescriptorPort {
    String domainType();                       // "CINEMA", "CONCERT", "PRODUCT"
    StockUnitView describe(long stockUnitId);  // 좌석 A12 / 신발 270mm 등
    boolean supportsSeatSelection();           // 좌석 지정 여부
}
```

> 새 도메인 추가 = `DomainDescriptorPort` 구현 + 재고 초기화 로직 추가. **코어 무수정.**

---

## 5. 대규모 트래픽 대응 설계 (핵심)

선착순 판매의 난이도는 **동시성 × 폭주**에 있다. 3단계 방어선을 둔다.

### 방어선 1 — 가상 대기열 (유입 평탄화)

- 판매 오픈 시 모든 사용자는 **대기열 토큰**을 먼저 받는다 (Redis Sorted Set, score=진입시각).
- 서버는 초당 N명씩만 **입장 허용(active token)** → 코어/DB가 처리 가능한 양만 유입.
- 사용자는 순번·예상 대기시간을 폴링/SSE로 안내받음.
- 효과: 오픈 순간 100k 동시 요청 → 코어에는 초당 처리 가능량만 도달.

### 방어선 2 — 원자적 재고 차감 (초과 판매 0)

두 가지 전략을 계층적으로 제공(도메인/부하에 따라 선택):

| 전략 | 방법 | 특징 |
|------|------|------|
| **A. DB 비관적 락** | `SELECT ... FOR UPDATE` 후 `remaining--` | 강한 정합성, 소규모/좌석지정에 적합 |
| **B. DB 원자 UPDATE** | `UPDATE ... SET remaining=remaining-1 WHERE remaining>0` (영향행수 확인) | 락 경합↓, 단순 |
| **C. Redis 원자 차감** | Lua script로 `재고 확인+차감+선점 등록`을 원자 실행 | 초고성능, 대규모 선착순에 적합 |

> 대규모 시나리오에서는 **C(Redis Lua)** 로 즉시 판정하고, 실제 DB 반영은
> **Worker가 이벤트 스트림을 소비하여 비동기 반영**(write-behind)한다.

Redis Lua (개념):
```lua
-- KEYS[1]=stock:{eventId}, KEYS[2]=hold:{eventId}:{userId}
-- ARGV[1]=ttl(sec)
if redis.call('EXISTS', KEYS[2]) == 1 then return -2 end   -- 중복 선점 방지
local remaining = tonumber(redis.call('GET', KEYS[1]))
if not remaining or remaining <= 0 then return -1 end        -- 품절
redis.call('DECR', KEYS[1])                                  -- 원자 차감
redis.call('SET', KEYS[2], '1', 'EX', ARGV[1])              -- TTL 선점
return remaining - 1
```

### 방어선 3 — 선점 TTL + 보상 트랜잭션 (정합성)

- 선점(Hold)은 **TTL(예: 5분)** 을 가진다. 결제 미완료로 만료되면 **재고 자동 복원**.
- 결제 흐름은 **Saga(보상 트랜잭션)**:
  1. Hold(재고 차감) → 2. Order 생성 → 3. Payment(Mock) →
  - 성공: Order CONFIRMED, Ticket 발권
  - 실패/타임아웃: 보상 이벤트 발행 → **재고 복원 + Hold 해제**
- 재고 차감과 이벤트 발행의 원자성은 **Outbox 패턴**으로 보장(같은 트랜잭션에 outbox insert).

---

## 6. 핵심 시퀀스 — "좌석 선점 → 결제 → 발권"

```
User        API(Core)        Redis           DB           Worker         Payment(Mock)
 │  hold(seat) │               │              │              │                │
 │────────────►│  Lua tryHold  │              │              │                │
 │             │──────────────►│ (원자 차감+   │              │                │
 │             │◄──────────────│  TTL 선점 OK) │              │                │
 │             │  outbox+order (tx)           │              │                │
 │             │─────────────────────────────►│(order=PENDING)              │
 │◄────────────│  holdId, 남은시간            │              │                │
 │  pay(order) │               │              │              │                │
 │────────────►│               │              │              │  charge(mock)  │
 │             │──────────────────────────────────────────────────────────►│
 │             │◄──────────────────────────────────────────────────────────│(OK)
 │             │  order=CONFIRMED (tx)        │              │                │
 │             │─────────────────────────────►│              │                │
 │             │  emit PaymentConfirmed ──────────────► stream ──► issue ticket
 │◄────────────│  ticketCode                 │              │                │

[타임아웃 시] Redis TTL 만료 → Worker가 HoldExpired 감지 → StockRestored 이벤트
            → Redis 재고 +1, DB order=EXPIRED, 좌석 재판매 가능
```

---

## 7. 적용한 설계 원칙 (과제 평가 포인트)

### SOLID
- **SRP:** UseCase 서비스 1개 = 1 시나리오. Controller는 변환만.
- **OCP:** 새 도메인/새 재고전략을 어댑터·전략 추가로 확장(코어 수정 X).
- **LSP:** 모든 `DomainDescriptorPort` 구현은 동일 계약 준수.
- **ISP:** Payment/Notification/Queue 포트를 잘게 분리.
- **DIP:** 코어(고수준)가 인터페이스에 의존, 인프라(저수준)가 이를 구현.

### GRASP
- **Information Expert:** 재고 판단은 `Inventory` 애그리거트가 책임.
- **Creator:** `Ticket`은 확정된 `Order`가 생성.
- **Controller:** UseCase 서비스가 시스템 오퍼레이션 조율.
- **Low Coupling / High Cohesion:** 포트로 결합도↓, 레이어별 응집도↑.
- **Polymorphism:** 도메인/재고전략을 다형성으로 분기.
- **Pure Fabrication:** `StockRepositoryPort` 등은 도메인에 없는 순수 조립물.

### Design Patterns (GoF 등)
| 패턴 | 적용 위치 |
|------|-----------|
| **Strategy** | 재고 차감 전략(DB락/원자UPDATE/RedisLua), 대기열 입장 정책 |
| **Adapter** | Payment(Mock), Notification(Mock), 도메인 어댑터 |
| **Facade** | 결제 플로우(Hold+Order+Pay 오케스트레이션) |
| **State** | Order/Hold 상태 전이 |
| **Observer / Pub-Sub** | 도메인 이벤트(재고복원, 발권, 알림) |
| **Template Method** | 판매 처리 공통 골격 + 도메인별 훅 |
| **Factory Method** | Ticket 생성 |
| **Command** | 취소/환불 요청 |

> 아키텍처 패턴: **Saga(보상 트랜잭션)**, **Outbox**, **CQRS(경량)**, **Virtual Waiting Room**.

---

## 8. 배포 뷰 (데모용)

```
docker-compose:
  - api          x N (수평 확장 데모, 무상태)
  - worker       x M (이벤트 소비)
  - postgres     x 1
  - redis        x 1
  - prometheus + grafana (지표)
  - k6 (부하 시나리오: 오픈 순간 동시 접속)
```

부하 테스트 시나리오(예): 좌석 100석, 동시 사용자 5,000명 → **판매 성공 정확히 100건,
초과 판매 0건, 오류율 < 1%** 를 검증.
