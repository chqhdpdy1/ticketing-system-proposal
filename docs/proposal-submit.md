# Term Project Proposal — Ticketing System

> 국민대학교 · Software Architecture · HW1 Project Proposal

---

## 1. 프로젝트 팀 명

**Ticketing System**

---

## 2. 프로젝트 주제

**주제명:** Ticketing System — 범용 선착순(First-Come-First-Served) 판매 플랫폼 (첫 도메인: 영화관 티켓 예매)

**설명:** 한정된 재고를 짧은 시간에 다수의 사용자가 동시에 구매하려는 선착순 판매 상황을
안정적으로 처리하는 범용 판매 플랫폼을 설계·구현한다. 선착순 판매는 도메인(영화 좌석,
공연 좌석, 한정판 상품)이 달라도 동시성·폭주 트래픽·공정성·정합성이라는 공통 문제를
공유한다. 본 프로젝트는 이를 해결하는 도메인 독립적 판매 코어를 만들고, 그 위에
영화관 티켓 예매 도메인을 첫 번째로 구현한다. 결제·알림 등 외부 연동은 더미(Mock)로
처리한다.

---

## 3. 팀 구성

**1인 팀**으로 진행한다.

| 이름 | 학번 | 소속 | 학년 | 역할 |
|------|------|------|------|------|
| 홍석준 | 20213098 | 소프트웨어학과 | 4학년 | 전체(설계·개발·문서) |

- **강점 및 경험:** 소프트웨어 아키텍처·설계 원칙(SOLID/GRASP/디자인 패턴) 학습,
  Spring Boot/JPA 기반 REST API 및 관계형 DB 트랜잭션·락 학습 경험.

---

## 4. 시스템 목표 (Vision & Scope)

**Vision:** 도메인에 종속되지 않는 재사용 가능한 선착순 판매 코어를 만들어, 초과 판매 없이
(정확성), 폭주 트래픽에서도 안정적으로(가용성), 먼저 온 사용자가 먼저 사도록(공정성)
보장하는 시스템을 목표로 한다.

**Scope:**

- **포함:** 선착순 판매 코어(판매/재고/선점/주문), 동시성 제어, 영화관 도메인(상영/좌석/예매/발권), 간단한 인증, Mock 결제·알림.
- **제외:** 실제 결제(PG)·SMS 연동, 추천·정산 등 부가 기능, 모바일 네이티브 앱.

**As-Is / To-Be:**

| 구분 | As-Is | To-Be |
|------|-------|-------|
| 아키텍처 | 도메인마다 판매 로직을 새로 구현 | 범용 코어 + 도메인 어댑터로 재사용 |
| 동시성 | 단순 조회 후 갱신 → 초과 판매 발생 | 원자적 재고 차감으로 초과 판매 0 |
| 폭주 대응 | 오픈 순간 과부하로 장애 | 대기열로 유입 제어 |
| 정합성 | 결제 실패 시 재고 누수 | 선점 만료 시 재고 자동 복원 |

---

## 5. 시스템 개요 및 특성

**개요·특성:**

- 레이어드 + 헥사고날(Ports & Adapters) 구조로 코어/도메인/인프라 분리.
- 재고 차감은 원자적 연산으로 처리하여 초과 판매를 방지.
- 판매 오픈 시 대기열로 유입량을 제어.
- 선점(Hold)은 TTL을 가지며 만료 시 자동 반환.
- 결제·알림은 인터페이스 + Mock 구현으로 대체.

**Use Case 별 Functional Requirements (FR):**

| Use Case | 하는 역할 | 처리 정보 | Functional Requirements | 적용 Architecture/GRASP/SOLID/Design Pattern | NFR (Quality Attributes) |
|---|---|---|---|---|---|
| 판매 조회 | 판매(상영) 목록·상세 조회 | 판매정보, 잔여수량 | 목록/상세 조회, 오픈 카운트다운 | Layered / Information Expert / Repository | 성능 |
| 대기열 진입 | 몰린 사용자를 순서대로 입장 | 사용자, 순번, 토큰 | 대기표 발급, 순번 안내, 입장 허용 | 큐 / Controller / Strategy | 공정성, 가용성 |
| 재고 선점 | 좌석을 임시 점유 | 좌석, 사용자, TTL | 원자적 재고 차감, 중복 선점 방지 | Ports&Adapters / Low Coupling / State | 정확성, 동시성 |
| 주문·결제 | 선점을 구매로 확정(Mock) | 주문, 금액, 결제 | 결제 요청, 성공 시 확정·실패 시 해제 | Facade / Adapter / Template Method | 신뢰성, 정합성 |
| 발권 | 티켓 발급·조회 | 티켓, 좌석, 상영 | 티켓 코드 발급, 예매 내역 조회 | Factory Method / Creator | 유지보수성 |
| 판매 등록 | 상영·좌석·재고 등록(관리자) | 상영, 좌석, 가격 | 상영·가격·오픈시각 등록, 재고 초기화 | Layered / Builder | 보안(권한) |
| 취소·환불 | 예매 취소(Mock) | 주문·티켓 상태 | 취소, 재고 복원, 환불(Mock) | Command / Observer | 정합성 |

**추가 NFR (Quality Attributes):**

| Quality Attribute | 요구 시나리오 | 달성 전술 |
|---|---|---|
| 정확성 | 동시 요청에도 재고 초과 판매 = 0 | 원자적 차감, 유니크 제약 |
| 가용성 | 판매 오픈 피크에도 정상 응답 | 대기열로 유입 제어, 타임아웃 |
| 성능 | 재고 조회·선점 빠른 응답 | 캐시(Redis), 인덱스 |
| 확장성 | 인스턴스 수평 확장 | 무상태 API, 분산 락 |
| 공정성 | 요청 도착 순서대로 처리 | 대기열 순번 토큰 |
| 정합성 | 결제 실패 시 재고 복원 | 선점 TTL + 보상 트랜잭션 |
| 유지보수성 | 새 도메인 추가 시 코어 무수정 | Ports & Adapters, DIP |
| 보안 | 인증·권한 분리, 중복요청 방지 | JWT, 멱등키 |

---

## 6. 사용 기술 및 Framework

대규모 선착순 판매를 다루는 티켓팅 플랫폼(인터파크, Ticketmaster 등)과 한정판 판매
시스템은 공통적으로 **가상 대기열, 인메모리 재고 관리, 메시지 큐 기반 비동기 처리**
아키텍처를 사용한다. 본 프로젝트는 이 개념들을 참고하여 아래 기술로 구현한다.

**참조 아키텍처 스타일:** Layered, Ports & Adapters(Hexagonal), Event-Driven.

| 구분 | 기술 | 이유 |
|------|------|------|
| Language / Framework | Java 17 + Spring Boot 3 | 트랜잭션·동시성 자료 풍부 |
| Persistence | Spring Data JPA + PostgreSQL | 관계형 정합성, 락 지원 |
| Cache / Lock / Queue | Redis | 원자 연산, 분산 락, 대기열 |
| API | REST (Swagger) | 표준적·검증 용이 |
| Frontend | React (최소 화면) | 대기열·예매 흐름 데모 |
| Test / Load | JUnit5, k6 | 동시성·부하 검증 |
| Infra | Docker Compose | 로컬 재현, 다중 인스턴스 |

**차용할 부분:** 티켓팅 플랫폼의 가상 대기열 개념을 대기열 모듈로, 인메모리 재고 관리
개념을 Redis 재고 차감으로 구현한다.

---

## 참고문헌

1. Bass, L., Clements, P., Kazman, R. *Software Architecture in Practice* (4th ed.), Addison-Wesley.
2. Larman, C. *Applying UML and Patterns* (GRASP), Prentice Hall.
3. Gamma et al. *Design Patterns* (GoF), Addison-Wesley.
4. Evans, E. *Domain-Driven Design*, Addison-Wesley.
5. Redis 공식 문서 — Distributed Locks, Lua scripting. https://redis.io/docs/
6. Spring Framework Reference — Transaction Management. https://docs.spring.io/
7. AWS — Virtual Waiting Room. https://aws.amazon.com/solutions/implementations/virtual-waiting-room-on-aws/
