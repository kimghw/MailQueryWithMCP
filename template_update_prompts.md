# 템플릿 수정 작업용 프롬프트 모음

## 1. 기본 템플릿 수정 프롬프트
```
### [템플릿 번호]. ✅ [템플릿 ID]

**카테고리**: [카테고리]
**상태**: 성공
**Note**: [수정 요청 내용]
**라우팅 타입**: sql
**에이전트 처리**: [에이전트 메시지]

**자연어 질의**:
1. [질의1] (original)
2. [질의2] (similar1)
3. [질의3] (similar2)
   ... 외 [N]개

**파라미터 정보**:
- 필수 파라미터: [파라미터 목록]

**플레이스홀더**: [플레이스홀더 목록]

**SQL 쿼리**:
```sql
[SQL 쿼리]
```

**실행 결과**: [N]개 행 반환

--- note를 참조해서 템플릿을 업데이트 해주세요.
```

## 2. 자주 사용하는 수정 요청들

### 2.1 body 필드 추가
```
agenda_chair의 body를 조회할 수 있게 해주고.
```

### 2.2 period 파라미터 추가
```
필수 파라미터 및 플레이스홀더에 period를 추가해 주고 기본 90일로 해주세요.
```

### 2.3 to_agent 메시지 변경
```
to_agent는 [새로운 메시지]로 변경해주세요.
```

### 2.4 특정 필드만 출력
```
[테이블명]의 [필드1], [필드2]를 출력할 수 있게 해주세요.
```

### 2.5 기본값 변경
```
기본값은 [값1], [값2], [값3]로 초기값 넣어주세요.
```

### 2.6 조직별 응답 조회
```
/home/kimghw/IACSGRAPH/modules/templates/data/query_templates_split/metadata.json 여기 기관정보가 있으니 이 기관들의 응답을 agenda_responses_content에서 응답한 메일을 참고해주세요.
```

## 3. 템플릿 파일 경로
```
/home/kimghw/IACSGRAPH/modules/templates/data/query_templates_split/query_templates_group_[001-009].json
```

## 4. 테스트 실행 명령어
```bash
python -m modules.templates.validators.test_individual_reports data/iacsgraph.db
```

## 5. Git 커밋 메시지 템플릿
```
Update query templates based on test feedback

- Add body field to [template_name]
- Add period parameter to [template_name]
- Update to_agent message for [template_name]
- Fix SQL query for [template_name]
```