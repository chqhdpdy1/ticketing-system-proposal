# PROJECT STATE — 설계 v2.0

## 프로젝트

Ticketing System / 국민대학교 Software Architecture Term Project.
홍석준 / 20213098 / 소프트웨어학과 4학년 / 1인 팀.
재사용 가능한 판매 코어를 지향하며 첫 구현은 영화관 지정 좌석 예매다.

## 진행 상태

- v1 제안서·설계: 작성 완료. 기존 HTML은 v1 산출물.
- v2 DB-first 설계: 2026-10-31 문서 리팩터링.
- 서비스 구현·마이그레이션·자동화 테스트·성능 검증: 미착수.
- v2 Markdown에 대한 HTML 재생성·인쇄 검수: 미실행.

## 현재 설계 결정

1. Spring Boot 모듈러 모놀리스. 별도 Gateway/Queue 서비스/Worker 불필요.
2. PostgreSQL만 재고·선점·주문·결제·티켓의 진실원본.
3. 단일 좌석 선점; StockUnit 잠금 후 Hold/Order를 일관된 순서로 잠근다.
4. 결제는 외부 I/O 없는 결정적 Mock. 동일 트랜잭션에서 PAID/SOLD/CONFIRMED 및 Ticket 생성.
5. 만료는 DB 시간과 expires_at으로 판정. 복원은 holdId 기반 조건부 전이.
6. Outbox는 알림 등 후속 효과에만 사용. 재고 복원·발권은 비동기 이벤트에 의존하지 않는다.
7. Redis는 대기열과 선택적 조회 캐시. 장애 시 신규 구매 입장을 차단하되 기존 Hold의 결제·해제는 DB에서 계속 처리.
8. 구매 시도 권한의 접수 순서만 보장. 수량 상품·다좌석·환불은 후속 범위.

## 읽기 순서

`design/current/01~05` → `design/changes/2026-10-31-v2.md` → `report/proposal-submit.md`.
기존 CHANGELOG에는 v1 이력이 있고 v2 상세 변경 기록은 위 changes 파일에 있다.

## 이전 버전 보존

기존 `design/versions/v1.0-2026-09-29/`는 변경하지 않았다.
변경 직전 저장소 전체 상태는 Git 커밋 `8a56deac30b8da2a039111af1b6e4e30141b8453`에 보존되어 있다.
이번 작업은 별도 브랜치 `refactor/db-first-design-2026-10-31`에서 수행하며 main은 변경하지 않는다.

## 다음 구현 TODO

1. Spring Boot 패키지 구조 및 Flyway 마이그레이션.
2. Testcontainers PostgreSQL로 ACTIVE 유니크·잠금·롤백 검증.
3. Hold/Order/Payment/Ticket 유스케이스와 만료 스케줄러.
4. 멱등 요청 기록과 동시 재시도 테스트.
5. Redis 대기열 원자 연산·epoch 및 장애 복구.
6. React 최소 화면, k6, HTML 재생성.

과거 문서에 적힌 실행 환경·권한 제한은 현재 환경에서 검증된 사실로 간주하지 않는다.
