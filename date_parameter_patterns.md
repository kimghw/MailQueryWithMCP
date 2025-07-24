# 날짜 파라미터 처리 패턴 분석

## 1. 날짜 파라미터 사용 케이스

### 케이스 1: 최근 N일 (단일 파라미터)
```sql
-- 장점: 간단하고 직관적
-- 단점: 특정 기간 지정 불가
WHERE created_at >= DATE('now', '-{days} days')
```

### 케이스 2: 시작일-종료일 (두 개 파라미터)
```sql
-- 장점: 정확한 기간 지정 가능
-- 단점: 파라미터 2개 필요
WHERE created_at BETWEEN '{start_date}' AND '{end_date}'
```

### 케이스 3: 하이브리드 접근 (선택적 파라미터)
```sql
-- 장점: 유연성 높음
-- 단점: 로직이 복잡
WHERE created_at >= COALESCE('{start_date}', DATE('now', '-{days} days'))
  AND created_at <= COALESCE('{end_date}', DATE('now'))
```

## 2. 권장 사항

### 2.1 일반적인 경우: days 파라미터 사용
- 대부분의 사용자는 "최근 30일", "최근 90일" 같은 패턴 사용
- 구현이 간단하고 직관적

### 2.2 정밀한 조회가 필요한 경우: date_from/date_to
- 회계 기간, 특정 이벤트 기간 등
- ISO 형식 사용: YYYY-MM-DD

### 2.3 복합 패턴
```json
{
  "optional_params": [
    {
      "name": "days",
      "type": "integer",
      "description": "최근 N일 (date_from이 없을 때만 사용)"
    },
    {
      "name": "date_from",
      "type": "date",
      "description": "시작일 (YYYY-MM-DD)"
    },
    {
      "name": "date_to",
      "type": "date",
      "description": "종료일 (YYYY-MM-DD)"
    }
  ],
  "default_params": {
    "days": 30,
    "date_from": null,
    "date_to": null
  }
}
```

## 3. SQL 쿼리 예시

### 3.1 단순 days 패턴
```sql
SELECT * FROM agendas 
WHERE last_updated >= DATE('now', '-{days} days')
```

### 3.2 날짜 범위 패턴
```sql
SELECT * FROM agendas 
WHERE last_updated >= '{date_from}' 
  AND last_updated <= '{date_to}'
```

### 3.3 스마트 패턴 (권장)
```sql
SELECT * FROM agendas 
WHERE last_updated >= 
  CASE 
    WHEN '{date_from}' != 'null' THEN '{date_from}'
    ELSE DATE('now', '-{days} days')
  END
AND last_updated <= 
  CASE 
    WHEN '{date_to}' != 'null' THEN '{date_to}'
    ELSE DATE('now')
  END
```