# nodes Phase Debug History
> Gen: bronze
> Last Updated: 2026-04-30

## [2026-04-30] [Step 6] API 예외 무음 처리 → saturation 카운터 오염

- **증상**: OPENAI_API_KEY 미설정 상태에서 entity_gen 실행 시 8개 카테고리 전체 `consecutive_failures=1` — 실제 LLM 호출 없이 포화 카운터 증가
- **원인**: `_llm_generate_candidate`의 `except Exception: return None` 가 인증 오류(401)도 `None`으로 처리 → `candidate is None` 분기 → failures +1
- **수정**: `except` 범위를 `except ValueError`로 한정 (extract_json 파싱 실패만 처리). API/네트워크 오류는 호출 스택으로 propagate
- **교훈**: LLM 호출 래퍼에서 광범위 except는 사용 금지. "LLM이 null을 반환했다"와 "LLM 호출 자체가 실패했다"는 별도 경로로 처리해야 saturation 상태가 오염되지 않음

## [2026-04-30] [Step 6] entity_gen 출력 품질 — 추상 entity 및 크로스-카테고리 중복

- **증상**: 초기 프롬프트로 실행 시 `dining:sushi` (음식 종류, 추상 개념), `pass-ticket:jr-pass` (transport:jr-pass와 크로스-카테고리 중복) 생성
- **원인 1 (추상)**: 프롬프트에 "구체적 실명 entity" 조건이 충분히 명시되지 않음
- **원인 2 (중복)**: 카테고리 내 de-dup만 수행, 전역(모든 카테고리) de-dup 없음
- **수정 1**: 프롬프트에 전체 레지스트리 entity 목록 + "추상 카테고리명·음식 종류 금지" 조건 추가
- **수정 2**: 후보 slug를 전체 레지스트리 slug와 비교하는 전역 de-dup 추가
- **교훈**: entity_gen은 아티팩트 품질 검토(실제 LLM 실행)가 필수. L1 mock 테스트만으로는 프롬프트 품질 이슈를 발견할 수 없음

---

<!-- 형식:
## [날짜] [Step N] [버그 요약]
- **증상**: 
- **원인**: 
- **수정**: 
- **교훈**: 
-->
