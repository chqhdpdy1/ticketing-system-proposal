# Term Project Proposal — Ticketing System

> 설계 v2.0 / 2026-10-31 / 구현 전 계획

## 1. 프로젝트 팀 명

Ticketing System

## 2. 프로젝트 주제

**재사용 가능한 선착순 판매 코어와 영화관 지정 좌석 예매 시스템**

같은 좌석에 대한 동시 요청, 판매 시작 시 유입 급증, 임시 선점 만료를 처리한다. 판매 코어는 영화 제목·상영관 배치 등 표시 정보를 모르며, 영화관 모듈이 이를 제공한다. 범용성은 설계 목표이고 모든 판매 유형에 대한 코어 무수정은 검증 전 가설이다.

## 3. 팀 구성

| 이름 | 학번 | 소속 | 학년 | 역할 |
|---|---|---|---|---|
| 홍석준 | 20213098 | 소프트웨어학과 | 4학년 | 설계·개발·검증·문서 |

SOLID·GRASP·디자인 패턴 학습 경험과 Spring Boot·DB 학습을 바탕으로 단계적으로 구현한다.

## 4. Vision & Scope

### Vision

동시 요청에도 하나의 회차별 좌석이 중복 판매되지 않고, 미결제 좌석을 다시 판매할 수 있는 시스템을 만든다. 대기열은 먼저 접수된 사용자에게 구매 시도 권한을 먼저 부여한다. 구매 완료 순서는 보장하지 않는다.

### Scope

- 포함: 단일 좌석 선점, 주문, 결정적 Mock 결제, 티켓 발급·조회, 선점 해제·만료, 대기열, 최소 로그인·관리자 상영 등록.
- 제외: 실제 PG·SMS, 결제 완료 후 취소·환불, 다좌석 원자 예매, 수량형 상품, 추천·정산, 네이티브 앱, 별도 마이크로서비스.
- 후속: 소규모 두 번째 지정 단위 도메인 계약 테스트로 재사용 범위를 평가. 수량 상품은 별도 모델 검토 후 확장.

### As-Is / To-Be

비교 대상은 특정 상용 서비스가 아니라 동시성 제어 없는 단순 구현이다.

| 구분 | 단순 구현 | 제안 설계 |
|---|---|---|
| 동시성 | 조회 후 잠금 없이 판매 | StockUnit 잠금·제약·단일 DB 트랜잭션 |
| 선점 만료 | 프로세스 메모리·TTL 알림에 의존 | DB 만료 시각과 재시도 가능한 스케줄러 |
| 폭주 | 모든 구매 요청을 즉시 처리 | Redis 대기열로 신규 구매 시도 제한 |
| 변경 | 표시 정보와 거래 로직 결합 | 판매 코어와 영화관 모듈의 의존성 분리 |

## 5. 시스템 개요 및 특성

Spring Boot 모듈러 모놀리스에 계층 구조와 Ports & Adapters를 적용한다. PostgreSQL이 거래 진실원본이며 Redis는 대기열에만 필수다. 정확성에 필요한 상태 변경은 DB 트랜잭션으로 처리한다.

| UC | 역할·정보 | FR | 설계 근거 | NFR |
|---|---|---|---|---|
| UC-1 조회 | 상영·좌석 상태 표시 | 목록·상세·좌석맵 | Layered, Information Expert, Repository | 조회 p95 목표 |
| UC-2 대기열 | 사용자·순번·입장권 | 중복 입장 방지·순차 권한 발급 | QueuePort, Redis Adapter, Controller | 접수 순서·장애 차단 |
| UC-3 선점 | 좌석·소유자·expires_at | 단일 좌석 선점·해제·만료 | SRP, Repository, DB 트랜잭션 | 중복 ACTIVE 0 |
| UC-4 주문·결제 | 주문·금액·Mock 결과 | 소유권 검증·멱등 확정 | PaymentPort/Adapter, Application Service | 중복 판매·결제 0 |
| UC-5 티켓 | 주문·티켓 코드 | 결제와 함께 발권·본인 조회 | Creator 책임, UNIQUE 제약 | 결제 후 티켓 누락 0 |
| UC-6 판매 등록 | 상영·회차별 좌석 | ADMIN 등록·오픈 후 재고 정의 변경 금지 | Layered, Repository, 권한 분리 | 회차별 매핑 무결성 |
| UC-7 미결제 취소 | Hold·PENDING Order | 해제·주문 종료 | 조건부 상태 전이 | 중복 복원 0 |

상태 enum을 State 패턴으로 부르지 않는다. 실제 구조가 없는 GoF 패턴은 나열하지 않는다.

### 품질 시나리오

- Q1 정확성: 동일 좌석 1,000개 동시 요청에서 ACTIVE Hold 최대 1개. 이미 SOLD인 좌석 선점 성공 0.
- Q2 복구성: DB·앱 정상 상태에서 1초 주기 만료 작업을 사용하고, 만료 후 5초 이내 재판매 가능을 목표로 한다. 장애 중 지연과 복구 후 수렴 시간을 별도 기록한다.
- Q3 성능: 명시된 테스트 환경·허용 부하에서 조회 p95 < 300ms, 선점 p95 < 500ms 목표. 대기시간 제외·API 처리시간 기준. 미달 시 그대로 보고한다.
- Q4 오류: 409 재고 충돌·429 제한을 정상 업무 거절로 별도 집계하며 예상하지 않은 5xx 비율 < 1% 목표. 전체 거절률도 공개한다.
- Q5 공정성: 단일 queue epoch 안에서 아직 대기 중인 낮은 순번을 건너뛰어 높은 순번을 입장시키는 횟수 0. 만료·탈퇴 사용자는 제외.
- Q6 변경 용이성: 두 번째 지정 단위 도메인 추가 시 코어 변경 파일 수를 측정한다. 0을 목표로 하되 결과 전 보장하지 않는다.
- Q7 보안: 타인 Hold/Order/Ticket 접근 및 관리자 API 무권한 호출 차단. 멱등키는 인증·봇 차단의 대체 수단이 아니다.

## 6. 기술 및 참조

Java 17, Spring Boot 3, Spring Data JPA, PostgreSQL, Flyway, Redis, React/Vite/TypeScript, JUnit5/Testcontainers, k6, Docker Compose.

핵심 근거는 PostgreSQL의 행 잠금·부분 인덱스, Spring의 트랜잭션, Redis의 원자적 스크립트 및 가상 대기실 개념이다. 특정 상용 업체 내부 구현을 확인한 것으로 주장하지 않는다. Redis 재고·write-behind·브로커·Saga는 1차 구현에서 사용하지 않는다.

## 7. 참고문헌

- Bass et al., Software Architecture in Practice, 4th ed.
- Larman, Applying UML and Patterns.
- Gamma et al., Design Patterns.
- PostgreSQL: https://www.postgresql.org/docs/current/explicit-locking.html
- PostgreSQL: https://www.postgresql.org/docs/current/indexes-partial.html
- Spring: https://docs.spring.io/spring-framework/reference/data-access/transaction.html
- Redis: https://redis.io/docs/latest/develop/programmability/eval-intro/

위 자료는 설계 참고 목록이다. 버전별 세부 API·설정은 구현 착수 시 공식 문서와 대조한다.
