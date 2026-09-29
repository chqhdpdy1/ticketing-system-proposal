# 기술 스택 및 참조 시스템 조사

> 범용 선착순(FCFS) 판매 플랫폼 — 사용 기술과 조사한 참조 아키텍처 정리
> (제안서 6번 항목 상세 뒷받침 문서)

---

## 1. 참조 시스템 조사

### 1.1 가상 대기열 (Virtual Waiting Room)

대규모 티켓팅/한정판 판매 시스템은 오픈 순간 트래픽 폭주를 견디기 위해
**가상 대기열**을 둔다. 사용자는 실제 판매 서버 앞에서 대기표를 받고,
서버가 처리 가능한 속도로만 순차 입장시킨다.

- **핵심 아이디어:** 유입량(rate)을 제어해 백엔드가 감당 가능한 부하만 통과시킴.
- **본 프로젝트 차용:** Redis Sorted Set으로 순번 관리, 초당 입장 허용량(admission rate) 설정.

### 1.2 인메모리 재고 관리 + write-behind

커머스/티켓팅에서 재고 판정을 매번 RDB에서 하면 락 경합으로 병목이 생긴다.
따라서 **인메모리(Redis)에서 원자적으로 재고를 판정**하고, 실제 DB 반영은
이벤트로 **비동기 후행 처리(write-behind)** 한다.

- **본 프로젝트 차용:** Redis Lua로 재고 차감 즉시 판정 → 이벤트 → Worker가 DB 반영.

### 1.3 Saga / Outbox 패턴

분산·비동기 환경에서 "재고 차감"과 "결제"의 정합성을 트랜잭션 하나로 묶기 어렵다.
**Saga(보상 트랜잭션)** 로 단계별 진행/롤백을 관리하고, 이벤트 발행 유실을 막기 위해
**Outbox 패턴**(같은 트랜잭션에서 이벤트를 outbox 테이블에 기록)을 쓴다.

- **본 프로젝트 차용:** 결제 실패/만료 시 재고 복원을 보상 이벤트로 처리, Outbox로 발행 보장.

---

## 2. 사용 기술 스택 및 선정 이유

| 계층 | 기술 | 선정 이유 | 대안 |
|------|------|-----------|------|
| Language | **Java 17** (또는 Kotlin) | 동시성/트랜잭션 학습자원 풍부 | Kotlin, Go |
| Framework | **Spring Boot 3** | REST/JPA/트랜잭션/스케줄러 통합 | Micronaut, Quarkus |
| ORM | **Spring Data JPA** | 비관적/낙관적 락 지원, 생산성 | MyBatis, jOOQ |
| RDB | **PostgreSQL** | 강한 정합성, `SELECT FOR UPDATE`, 부분 유니크 인덱스, JSONB | MySQL |
| Cache/Lock/Queue | **Redis** | Lua 원자연산, 분산 락, Sorted Set 대기열, Stream | Hazelcast |
| Messaging | **Redis Stream** (기본), Kafka(선택) | 경량 이벤트 소비, 학습 난이도↓ | RabbitMQ, Kafka |
| API 문서 | **springdoc-openapi (Swagger UI)** | 표준 API 스펙 자동화 | - |
| Auth | **Spring Security + JWT** | 무상태 인증, 확장 용이 | 세션 |
| Frontend | **React + Vite + TypeScript** | 대기열/좌석맵 데모 UI | Vue |
| Test | **JUnit5, Testcontainers** | 실제 PG/Redis로 통합 테스트 | H2(단순) |
| Load Test | **k6** (또는 JMeter) | 코드형 부하 시나리오, 동시성 재현 | Gatling |
| Container | **Docker Compose** | 다중 인스턴스·의존성 로컬 재현 | k8s(과함) |
| Observability | **Micrometer + Prometheus + Grafana** | 재고/대기열/오류 지표 시각화 | ELK |

---

## 3. 조사 시스템에서 실제 사용할 부분(계획)

| 참조 개념 | 본 프로젝트 적용 모듈 | 구현 방식 |
|-----------|----------------------|-----------|
| Virtual Waiting Room | `WaitingQueueService` | Redis Sorted Set + 입장 토큰 |
| In-memory stock | `RedisStockAdapter` | Lua script 원자 차감 |
| write-behind | `StockSyncWorker` | Stream 소비 → DB 반영 |
| Saga | `OrderSaga` (Application Layer) | 상태 기반 오케스트레이션 |
| Outbox | `outbox_event` 테이블 + `OutboxRelay` | tx 내 기록 → 폴링 발행 |
| Distributed Lock | `RedisLockAdapter` | SET NX PX / Redisson(선택) |

---

## 4. 검증 계획 (부하·정확성)

- **정확성 테스트:** 좌석 100석에 동시 사용자 5,000명 → 성공 정확히 100, 초과 0.
- **부하 테스트(k6):** 오픈 순간 VU 5,000, ramp-up 10s → p95 지연/오류율 측정.
- **장애 주입:** 결제 Mock을 랜덤 실패/지연시켜 보상 트랜잭션·재고 복원 검증.
- **수평 확장:** api 인스턴스 1→3 확장 시 처리량 증가 관측(무상태 확인).

---

## 5. Reference

1. AWS Solutions — *Virtual Waiting Room on AWS*. https://aws.amazon.com/solutions/implementations/virtual-waiting-room-on-aws/
2. Redis Docs — *Distributed Locks (Redlock)*, *Lua scripting*, *Streams*. https://redis.io/docs/
3. Chris Richardson — *Microservices Patterns* (Saga, Outbox, CQRS), Manning.
4. Spring — *Transaction Management & Locking*. https://docs.spring.io/spring-framework/reference/data-access/transaction.html
5. Martin Fowler — *CQRS*, *Event-Driven Architecture*. https://martinfowler.com/
6. PostgreSQL Docs — *Explicit Locking / Partial Indexes*. https://www.postgresql.org/docs/

> ※ 각 URL 접속일과 판본은 최종 제출 시 확정하세요. 내용은 라이선스 준수를 위해 요약·재구성했습니다.
