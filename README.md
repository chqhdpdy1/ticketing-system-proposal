# Ticketing System — 선착순 판매 코어와 영화관 예매

국민대학교 Software Architecture Term Project / 1인 팀 / 설계 v2.0.

## 현재 상태

설계 문서 리팩터링 완료. 서비스 코드·DB 마이그레이션·테스트는 아직 구현하지 않았다. 성능 수치는 검증 전 목표이며 달성 결과가 아니다.

## 설계 요약

- **배포:** Spring Boot 모듈러 모놀리스 1개 + PostgreSQL + Redis + React.
- **재고 진실원본:** PostgreSQL. Redis는 대기열과 선택적 조회 캐시에만 사용한다.
- **정확성:** StockUnit 행 잠금 + ACTIVE Hold 부분 유니크 인덱스 + 동일 DB 트랜잭션.
- **결제:** 외부 I/O 없는 결정적 Mock. 결제 확정·좌석 판매·발권을 한 트랜잭션으로 커밋한다.
- **만료:** DB expires_at 기준 스케줄러. Redis TTL 삭제를 재고 복원 신호로 사용하지 않는다.
- **공정성:** 서버 접수 순번에 따른 구매 시도 권한 부여. 좌석 확보·결제 완료 순서는 보장하지 않는다.
- **확장성:** Ports & Adapters로 기술 의존성을 분리한다. 모든 도메인의 코어 무수정을 미리 보장하지 않는다.

## 문서

1. [진행 상태](PROJECT_STATE.md)
2. [제안서](design/current/01-project-proposal.md)
3. [아키텍처·트랜잭션](design/current/02-architecture.md)
4. [도메인 모델·DB 계약·API](design/current/03-domain-model.md)
5. [기술 스택·검증 계획](design/current/04-tech-stack.md)
6. [설계 결정 기록](design/current/05-decisions.md)
7. [제출용 Markdown](report/proposal-submit.md)
8. [v2 변경 기록](design/changes/2026-10-31-v2.md)

## 범위

이번 구현: 지정 좌석 1개 선점, 주문, Mock 결제, 동기 발권, 선점 해제·만료, 대기열, 최소 인증·관리자 등록.

이후 확장: 결제 완료 후 취소·환불, 다좌석 일괄 예매, 수량형 상품, 실제 PG, Redis 재고, 별도 메시지 브로커·Worker.

## HTML 주의

기존 `design/full-design.html`과 `report/Ticketing-System-Proposal.html`은 **v1 산출물**이며 v2 설계의 근거가 아니다. 이번 커밋은 Markdown 설계 변경만 반영한다. 제출 전 기존 빌드 스크립트로 재생성하고 표·페이지 나눔을 확인해야 한다.

```sh
python3 tools/build_submit.py
python3 tools/build_html.py
```

## 구현 순서

DB 제약·트랜잭션 테스트 → 선점/만료 → 주문/Mock 결제/발권 → 대기열 → UI → 부하·장애 테스트.
