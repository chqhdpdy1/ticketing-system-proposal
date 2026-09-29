# 도메인 모델 및 데이터 설계

> 범용 선착순(FCFS) 판매 플랫폼 — 첫 도메인: 영화관 티켓 예매
> 범용 코어 모델과 영화관 도메인 매핑, ERD, 상태 전이를 정의한다.

---

## 1. 모델링 원칙

- **범용 코어**는 "판매 이벤트 / 재고 단위 / 선점 / 주문"이라는 **도메인 중립 개념**만 안다.
- **도메인(영화관)** 은 코어 개념을 **구체화**한다: 판매이벤트=상영, 재고단위=좌석.
- 코어 테이블과 도메인 테이블을 분리하고, `stock_unit`이 둘을 잇는 **연결점**이 된다.

```
 [범용 코어 개념]            [영화관 도메인 개념]
  SalesEvent      ◄────────►  Screening (상영 회차)
  StockUnit       ◄────────►  Seat      (좌석)
  Hold            (그대로)     좌석 임시 점유
  Order / Payment (그대로)     예매 결제
  Ticket          ◄────────►  MovieTicket (좌석/상영 정보 포함)
```

---

## 2. 범용 코어 도메인 모델

### 2.1 주요 애그리거트/엔티티

| 개념 | 설명 | 핵심 속성 |
|------|------|-----------|
| **SalesEvent** | 하나의 선착순 판매 단위(상영/공연회차/드롭) | id, domainType, title, status, openAt, closeAt |
| **Inventory** | 판매 이벤트의 재고 총괄 | salesEventId, totalQty, remainingQty(캐시 동기화) |
| **StockUnit** | 개별 재고 단위(좌석/상품 옵션) | id, salesEventId, code, status, version |
| **Hold** | 재고 단위 임시 선점 | id, stockUnitId, userId, expiresAt, status |
| **Order** | 구매 주문 | id, userId, salesEventId, amount, status |
| **OrderLine** | 주문 항목(선점→확정) | orderId, stockUnitId, holdId, price |
| **Payment** | 결제(Mock) | id, orderId, status, provider, paidAt |
| **Ticket** | 발권 결과 | id, orderId, stockUnitId, code, issuedAt |
| **User** | 구매자/판매자(어드민) | id, email, role |
| **OutboxEvent** | 이벤트 발행 원장 | id, type, payload, status, createdAt |

### 2.2 상태(enum)

- `SalesEvent.status`: `SCHEDULED` → `OPEN` → `CLOSED` / `SOLD_OUT`
- `StockUnit.status`: `AVAILABLE` → `HELD` → `SOLD` / (복원 시) `AVAILABLE`
- `Hold.status`: `ACTIVE` → `CONFIRMED` / `EXPIRED` / `RELEASED`
- `Order.status`: `PENDING` → `PAID`(=CONFIRMED) / `FAILED` / `EXPIRED` / `CANCELLED`
- `Payment.status`: `REQUESTED` → `APPROVED` / `DECLINED`

---

## 3. 영화관 도메인 모델 (첫 어댑터)

| 개념 | 매핑 | 핵심 속성 |
|------|------|-----------|
| **Movie** | 부가 | id, title, runningTime, rating |
| **Theater / Screen** | 상영관 | id, name, screenType(2D/IMAX), seatLayout |
| **Screening** | = SalesEvent | id, movieId, screenId, startAt, salesEventId, price |
| **Seat** | = StockUnit | id, screenId, row, col, seatType(일반/커플/장애인석) |
| **MovieTicket** | = Ticket 확장 | ticketId, screeningId, seatCode, entryCode(QR) |

> 좌석 지정 예매를 지원하므로 `DomainDescriptorPort.supportsSeatSelection()=true`.
> 한정판 상품 도메인(향후)은 `false`(선착순 수량만).

---

## 4. ERD (개념)

```
User 1───∞ Order 1───∞ OrderLine ∞───1 StockUnit ∞───1 SalesEvent
  │                     │                   │                 │
  │                     1                   1                 1
  │                  Payment              Hold            Inventory
  │                                         
  Order 1───∞ Ticket ∞───1 StockUnit

[영화관 확장]
Movie 1───∞ Screening ∞───1 Screen 1───∞ Seat
Screening 1───1 SalesEvent   (매핑)
Seat      1───1 StockUnit    (매핑)
```

### 4.1 핵심 테이블 스키마 (PostgreSQL, 요약)

```sql
-- 범용 코어
CREATE TABLE sales_event (
    id           BIGSERIAL PRIMARY KEY,
    domain_type  VARCHAR(20)  NOT NULL,        -- 'CINEMA' | 'CONCERT' | 'PRODUCT'
    title        VARCHAR(200) NOT NULL,
    status       VARCHAR(20)  NOT NULL DEFAULT 'SCHEDULED',
    open_at      TIMESTAMPTZ  NOT NULL,
    close_at     TIMESTAMPTZ,
    total_qty    INT          NOT NULL,
    remaining_qty INT         NOT NULL          -- DB 진실원본(캐시와 동기화)
);

CREATE TABLE stock_unit (
    id            BIGSERIAL PRIMARY KEY,
    sales_event_id BIGINT NOT NULL REFERENCES sales_event(id),
    code          VARCHAR(40) NOT NULL,          -- 좌석코드 'A12' 등
    status        VARCHAR(20) NOT NULL DEFAULT 'AVAILABLE',
    version       INT         NOT NULL DEFAULT 0, -- 낙관적 락
    UNIQUE (sales_event_id, code)                 -- 중복 좌석 방지
);

CREATE TABLE hold (
    id            BIGSERIAL PRIMARY KEY,
    stock_unit_id BIGINT NOT NULL REFERENCES stock_unit(id),
    user_id       BIGINT NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'ACTIVE',
    expires_at    TIMESTAMPTZ NOT NULL,
    UNIQUE (stock_unit_id, status)                -- 동일 재고 중복 ACTIVE 방지(부분 인덱스로 강화)
);

CREATE TABLE orders (
    id            BIGSERIAL PRIMARY KEY,
    user_id       BIGINT NOT NULL,
    sales_event_id BIGINT NOT NULL REFERENCES sales_event(id),
    amount        NUMERIC(12,2) NOT NULL,
    status        VARCHAR(20) NOT NULL DEFAULT 'PENDING',
    idempotency_key VARCHAR(80) UNIQUE,            -- 중복요청 방지(멱등)
    created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE order_line (
    id            BIGSERIAL PRIMARY KEY,
    order_id      BIGINT NOT NULL REFERENCES orders(id),
    stock_unit_id BIGINT NOT NULL REFERENCES stock_unit(id),
    hold_id       BIGINT REFERENCES hold(id),
    price         NUMERIC(12,2) NOT NULL
);

CREATE TABLE payment (
    id        BIGSERIAL PRIMARY KEY,
    order_id  BIGINT NOT NULL REFERENCES orders(id),
    status    VARCHAR(20) NOT NULL DEFAULT 'REQUESTED',
    provider  VARCHAR(20) NOT NULL DEFAULT 'MOCK',
    paid_at   TIMESTAMPTZ
);

CREATE TABLE ticket (
    id            BIGSERIAL PRIMARY KEY,
    order_id      BIGINT NOT NULL REFERENCES orders(id),
    stock_unit_id BIGINT NOT NULL REFERENCES stock_unit(id),
    code          VARCHAR(60) UNIQUE NOT NULL,
    issued_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE outbox_event (
    id         BIGSERIAL PRIMARY KEY,
    type       VARCHAR(50) NOT NULL,
    payload    JSONB       NOT NULL,
    status     VARCHAR(20) NOT NULL DEFAULT 'NEW',   -- NEW | SENT
    created_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

-- 영화관 도메인
CREATE TABLE movie (
    id BIGSERIAL PRIMARY KEY, title VARCHAR(200), running_time INT, rating VARCHAR(10));
CREATE TABLE screen (
    id BIGSERIAL PRIMARY KEY, name VARCHAR(80), screen_type VARCHAR(20));
CREATE TABLE seat (
    id BIGSERIAL PRIMARY KEY, screen_id BIGINT REFERENCES screen(id),
    row_label VARCHAR(3), col_no INT, seat_type VARCHAR(20),
    stock_unit_id BIGINT REFERENCES stock_unit(id));   -- 매핑
CREATE TABLE screening (
    id BIGSERIAL PRIMARY KEY, movie_id BIGINT REFERENCES movie(id),
    screen_id BIGINT REFERENCES screen(id), start_at TIMESTAMPTZ,
    price NUMERIC(12,2), sales_event_id BIGINT REFERENCES sales_event(id)); -- 매핑
```

> **정합성 장치:** `stock_unit`의 `UNIQUE(sales_event_id, code)`,
> `orders.idempotency_key UNIQUE`, `ticket.code UNIQUE`,
> `hold`의 ACTIVE 상태 부분 유니크 인덱스로 DB 레벨에서도 초과 판매/중복을 차단.

부분 유니크 인덱스 예:
```sql
CREATE UNIQUE INDEX uq_hold_active
    ON hold (stock_unit_id) WHERE status = 'ACTIVE';
```

---

## 5. 상태 전이 다이어그램

### 5.1 StockUnit (좌석)

```
        tryHold(성공)          payment 성공
AVAILABLE ─────────► HELD ───────────────► SOLD
    ▲                 │
    │  TTL 만료 /      │
    │  결제 실패 /     │
    └── 취소(복원) ────┘
```

### 5.2 Order

```
PENDING ──pay 성공──► PAID ──발권──► (Ticket 생성)
   │                    │
   │ pay 실패/타임아웃    │ 사용자 취소
   ▼                    ▼
FAILED/EXPIRED       CANCELLED  ──► 재고 복원 이벤트
```

---

## 6. 대표 API (REST 초안)

| Method | Path | 설명 | 관련 UC |
|--------|------|------|---------|
| GET | `/api/sales-events` | 판매(상영) 목록/상세 | UC-1 |
| POST | `/api/queue/{eventId}/enter` | 대기열 진입, 대기토큰 발급 | UC-2 |
| GET | `/api/queue/{eventId}/status` | 순번/입장 가능 여부 | UC-2 |
| POST | `/api/events/{eventId}/holds` | 재고(좌석) 선점 (입장토큰 필요) | UC-3 |
| DELETE | `/api/holds/{holdId}` | 선점 해제 | UC-3 |
| POST | `/api/orders` | 주문 생성(선점→주문, 멱등키) | UC-4 |
| POST | `/api/orders/{id}/pay` | 결제(Mock) 요청 | UC-4 |
| GET | `/api/orders/{id}/ticket` | 발권/티켓 조회 | UC-5 |
| POST | `/api/admin/sales-events` | 판매(상영) 등록 (ADMIN) | UC-6 |
| POST | `/api/orders/{id}/cancel` | 취소/환불(Mock) | UC-7 |

### 요청 예시 — 좌석 선점

```http
POST /api/events/1001/holds
Authorization: Bearer <jwt>
X-Queue-Token: <입장토큰>
Content-Type: application/json

{ "stockUnitId": 55012 }     // 좌석 A12
```
응답:
```json
{ "holdId": 88123, "stockUnitCode": "A12", "expiresInSeconds": 300, "remaining": 42 }
```

---

## 7. 확장 시나리오 (범용성 검증)

| 새 도메인 | SalesEvent | StockUnit | 좌석지정 | 추가 작업 |
|-----------|-----------|-----------|----------|-----------|
| 영화관(구현) | 상영 회차 | 좌석 | O | CinemaAdapter |
| 공연 티켓(향후) | 공연 회차 | 좌석/구역 | O | ConcertAdapter |
| 한정판 상품(향후) | 드롭 이벤트 | 상품 옵션(사이즈) | X (수량만) | ProductAdapter |

세 경우 모두 **코어(재고 차감/대기열/주문/결제) 코드는 동일**하며,
`DomainDescriptorPort` 구현과 초기 재고 세팅만 달라진다 → **OCP/DIP 충족**.
