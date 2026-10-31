# 기술 스택·검증 계획 v2.0

## 1. 선택

| 구성 | 기술 | 목적 |
|---|---|---|
| 서버 | Java 17 / Spring Boot 3 | 단일 앱·유스케이스·트랜잭션 |
| DB 접근 | Spring Data JPA / 필요 구간 명시 SQL | 행 잠금·제약·조건부 갱신 |
| 영속 저장 | PostgreSQL / Flyway | 유일한 거래 진실원본·마이그레이션 |
| 대기열 | Redis Sorted Set + 원자 스크립트 | 순번·입장 lease |
| UI | React / Vite / TypeScript | 대기열·단일 좌석 예매 |
| 인증 | Spring Security / JWT | 본인 리소스·ADMIN 권한 |
| 테스트 | JUnit5 / Testcontainers | 실제 PostgreSQL·Redis 계약 |
| 부하 | k6 | 요청률·VU·p95·업무 거절률 |
| 실행·지표 | Docker Compose / Micrometer | 재현 환경·기본 메트릭 |

Prometheus/Grafana는 여유 시 추가한다. Kafka·Redis Stream·재고 write-behind·분산 재고 락·별도 Gateway는 기본 구성에서 제외한다. 버전은 구현 시 BOM·lock 파일로 고정하고 기록한다.

## 2. 검증 원칙

아래는 미실행 테스트 계획이다. 목표 수치를 실측 결과처럼 표기하지 않는다. H2로 PostgreSQL 잠금·부분 인덱스 테스트를 대체하지 않는다. 테스트마다 DB를 초기화하고 최종 원장을 조회해 API 성공 수와 대조한다.

## 3. 필수 정확성 테스트

| ID | 자극 | 합격 조건 |
|---|---|---|
| T01 | 같은 좌석에 서로 다른 사용자 1,000명 동시 선점 | ACTIVE Hold 정확히 1, 나머지는 업무 거절; 실행 중 만료 없음 |
| T02 | 모든 100석에 최소 1개 요청이 도달하고 만료·Mock 실패 없이 모두 결제 | 고유 PAID 좌석 100, 티켓 100, AVAILABLE 0 |
| T03 | 한 사용자가 서로 다른 두 좌석 동시 선점 | 이벤트별 ACTIVE Hold 최대 1; 롤백된 좌석은 AVAILABLE |
| T04 | 만료·재선점을 동일 좌석에서 10회 반복 | EXPIRED 이력 누적 가능, ACTIVE 최대 1 |
| T05 | 같은 holdId 해제·만료 100회 재시도 | AVAILABLE 한 번 전이, 새 Hold 영향 없음 |
| T06 | 만료 경계에서 pay와 expiry를 barrier로 동시 실행 | PAID+SOLD+CONFIRMED+Ticket 또는 EXPIRED+AVAILABLE; 혼합 상태 0 |
| T07 | 잠금 대기 중 expires_at 경과 후 결제 | 잠금 후 DB 시각으로 만료 처리; 승인 0 |
| T08 | 같은 멱등키로 선점·주문·결제 동시 재전송 | 작업별 동일 결과·ID 반환, 부가 생성 0 |
| T09 | 같은 멱등키·다른 요청 본문 | 409, 기존 결과 불변 |
| T10 | 같은 좌석을 서로 다른 상영 회차에 등록 | StockUnit 독립, 양쪽 회차에서 각각 판매 가능 |
| T11 | 타인 Hold/Order/Ticket·ADMIN 접근 | 권한 차단, 거래 변경 0 |

100석 테스트의 '100 성공'은 모든 좌석 도달·성공 결제·만료 없음이라는 조건부 결과다. 일반적인 무작위 부하에서 반드시 100건 성공한다고 단정하지 않는다.

## 4. 장애 주입

- F01: 선점 커밋 전 프로세스 종료 → 거래 전체 롤백.
- F02: 결제 변경 중 Ticket 생성 직전 오류 → Payment·Order·Hold·StockUnit 전부 롤백.
- F03: 결제 커밋 후 응답 전 연결 종료 → 동일 키 재시도로 같은 티켓 조회.
- F04: 만료 스케줄러 중단·앱 재시작 → 만료 후보 처리 재개, 복구 후 수렴 시간 기록.
- F05: Redis 중단 → 신규 대기·선점 503, 기존 Hold 결제·해제 가능.
- F06: Redis 데이터 유실 → NOT_READY, epoch 변경·예전 토큰 무효화, 원래 대기 순서 보장 불가 안내.
- F07: Outbox 처리 후 완료 표시 전 종료 → 재전달 시 거래 상태 불변·Mock 알림 멱등 처리.
- F08: DB 타임아웃·데드락 → 부분 커밋 0, 제한 재시도 후 명확한 오류.

## 5. 불변식 검사

각 테스트 종료 시 다음 건수를 0으로 확인한다.

- 동일 StockUnit의 ACTIVE 또는 CONFIRMED Hold 중복.
- HELD인데 ACTIVE Hold 없음 / AVAILABLE인데 ACTIVE Hold 존재.
- SOLD인데 CONFIRMED Hold·PAID Order·APPROVED Payment·Ticket 중 하나 누락.
- PAID인데 좌석이 SOLD가 아님 / FAILED·EXPIRED·CANCELLED인데 Ticket 존재.
- 사용자·이벤트별 ACTIVE Hold 중복.
- 회차와 다른 상영관 좌석 또는 다른 판매 이벤트 StockUnit 매핑.

일관된 DB 스냅샷에서 검사한다. 마이그레이션 구현 시 위 검사를 실제 SQL로 추가한다.

## 6. 성능·공정성

먼저 1 API 인스턴스에서 50→100→300 RPS 등 단계 부하로 포화점을 찾고, 그 다음 5,000 VU burst를 **스트레스 실험**으로 수행한다. VU를 동시 실제 요청 수나 달성 처리량으로 혼동하지 않는다.

기록: CPU·RAM·DB/Redis 버전·연결 풀·인스턴스 수·요청률·지속시간·좌석 분포·인증 사용자 수·대기열 입장률/lease 상한. 네트워크·k6 실행 위치도 명시한다.

측정: 조회/선점/결제 p50·p95·p99, 409/429/503/5xx 비율, 실제 구매 처리량, DB 잠금 대기, 커넥션 풀 대기, 대기열 길이·입장 지연, 만료 처리 지연, Outbox 지연.

목표: 합의한 허용 부하에서 조회 p95 <300ms, 선점 <500ms, 예상 밖 5xx <1%. 대기열 대기시간은 별도다. 409·429를 숨기거나 성공 처리량에 합산하지 않는다.

서버 순번과 실제 입장 권한 부여 로그를 비교하여 단일 epoch의 순서 역전 0을 확인한다. 구매 완료 순서는 평가 대상이 아니다.

인스턴스 1→2→3은 추가 실험이며 처리량 선형 증가를 보장하지 않는다. DB 병목과 여러 스케줄러의 중복 작업 안전성을 함께 측정한다.

## 7. 재사용성 검증

소형 지정 단위 도메인 fixture와 별도 Descriptor로 동일 Hold/Order 계약 테스트를 수행한다. 코어 변경 파일 수·새 어댑터 수를 기록한다. 수량 상품과 실제 PG는 이 검증으로 지원된 것으로 간주하지 않는다.

## 8. 참고 자료

PostgreSQL 행 잠금·부분 인덱스, Spring 트랜잭션, Redis 스크립트와 Sorted Set 공식 문서를 구현 시 대조한다. 상용 예매 업체의 비공개 내부 구조를 직접 확인한 것처럼 인용하지 않는다. 외부 성능 수치를 본 프로젝트 예상 성능의 근거로 대체하지 않는다.
