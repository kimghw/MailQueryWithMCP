# DateTime 사용 가이드

**목적:** 프로젝트 전역에서 timezone-aware UTC 기준 시간 처리 표준화

---

## 핵심 원칙

### ✅ DO (권장 사항)

1. **항상 UTC 기준 사용**
   ```python
   from infra.utils.datetime_utils import utc_now

   now = utc_now()  # ✅ datetime with UTC timezone
   ```

2. **DB 저장 시 ISO format with 'Z'**
   ```python
   from infra.utils.datetime_utils import utc_now_iso

   expires_at = utc_now_iso()  # ✅ "2025-10-26T02:00:00Z"
   ```

3. **HTTP 응답 시 UTC 명시**
   ```python
   from infra.utils.datetime_utils import utc_now_iso

   response = {
       "timestamp": utc_now_iso(),  # ✅ "2025-10-26T02:00:00Z"
       "status": "success"
   }
   ```

4. **파일명은 UTC 기준**
   ```python
   from infra.utils.datetime_utils import to_local_filename

   filename = f"backup_{to_local_filename()}.json"  # ✅ "backup_20251026_020000.json"
   ```

5. **문서/로그는 UTC 표기**
   ```python
   from infra.utils.datetime_utils import format_for_display, utc_now

   log_message = f"Token refreshed at {format_for_display(utc_now())}"
   # ✅ "Token refreshed at 2025-10-26 02:00:00 UTC"
   ```

### ❌ DON'T (금지 사항)

1. **`datetime.now()` 사용 금지**
   ```python
   # ❌ naive datetime (timezone 정보 없음)
   now = datetime.now()

   # ✅ UTC aware datetime
   from infra.utils.datetime_utils import utc_now
   now = utc_now()
   ```

2. **naive ISO 문자열 금지**
   ```python
   # ❌ timezone 정보 없음
   timestamp = datetime.now().isoformat()  # "2025-10-26T02:00:00"

   # ✅ UTC 명시
   from infra.utils.datetime_utils import utc_now_iso
   timestamp = utc_now_iso()  # "2025-10-26T02:00:00Z"
   ```

3. **`.replace(tzinfo=None)` 금지**
   ```python
   # ❌ aware → naive 변환 (안티패턴)
   naive = aware_dt.replace(tzinfo=None)

   # ✅ UTC 유지
   from infra.utils.datetime_utils import ensure_utc
   utc_dt = ensure_utc(aware_dt)
   ```

---

## 헬퍼 함수 가이드

### 1. `utc_now()` - 현재 UTC 시각

**사용 시기:** `datetime.now()` 대체

```python
from infra.utils.datetime_utils import utc_now

# 현재 시각
now = utc_now()
print(now)  # 2025-10-26 02:00:00+00:00

# 시간 계산
expires_at = utc_now() + timedelta(hours=1)
```

**특징:**
- timezone-aware datetime 반환
- UTC timezone 포함
- 다중 서버 환경에서 일관성 보장

---

### 2. `utc_now_iso()` - UTC ISO 문자열

**사용 시기:** DB 저장, API 응답

```python
from infra.utils.datetime_utils import utc_now_iso

# DB 저장
expires_at = utc_now_iso()  # "2025-10-26T02:00:00Z"

db.execute("""
    INSERT INTO tokens (access_token, expires_at)
    VALUES (?, ?)
""", (token, expires_at))

# HTTP 응답
return {
    "token": "abc123",
    "expires_at": utc_now_iso()
}
```

**특징:**
- 'Z' suffix로 UTC 명시
- ISO 8601 표준 형식
- 파싱 시 timezone 정보 보존

---

### 3. `ensure_utc()` - UTC 변환

**사용 시기:** 외부 입력 처리, DB 조회 결과

```python
from infra.utils.datetime_utils import ensure_utc

# naive datetime → UTC aware
naive = datetime(2025, 10, 26, 10, 0, 0)
aware = ensure_utc(naive)
print(aware)  # 2025-10-26 10:00:00+00:00

# KST → UTC 변환
kst = timezone(timedelta(hours=9))
kst_dt = datetime(2025, 10, 26, 11, 0, 0, tzinfo=kst)
utc_dt = ensure_utc(kst_dt)
print(utc_dt.hour)  # 2 (11:00 KST = 02:00 UTC)
```

**특징:**
- naive 입력: UTC로 가정
- aware 입력: UTC로 변환
- 멱등성 보장 (이미 UTC면 그대로 반환)

---

### 4. `parse_iso_to_utc()` - ISO 문자열 파싱

**사용 시기:** DB 조회, API 요청 처리

```python
from infra.utils.datetime_utils import parse_iso_to_utc

# 'Z' suffix
dt = parse_iso_to_utc("2025-10-26T02:00:00Z")

# offset 포함
dt = parse_iso_to_utc("2025-10-26T11:00:00+09:00")
print(dt.hour)  # 2 (UTC로 자동 변환)

# naive (UTC로 가정)
dt = parse_iso_to_utc("2025-10-26T02:00:00")
print(dt.tzinfo)  # timezone.utc
```

**특징:**
- 다양한 ISO 형식 지원
- 항상 UTC datetime 반환
- DB 저장값 파싱에 이상적

---

### 5. `to_local_filename()` - 파일명 생성

**사용 시기:** 파일/폴더명 생성

```python
from infra.utils.datetime_utils import to_local_filename

# 기본 (YYYYmmdd_HHMMSS)
filename = f"backup_{to_local_filename()}.json"
# "backup_20251026_020000.json"

# 밀리초 포함
filename = f"temp_{to_local_filename(include_ms=True)}.tmp"
# "temp_20251026_020000_123.tmp"

# 특정 datetime 사용
dt = utc_now()
folder = f"logs/{to_local_filename(dt)}"
# "logs/20251026_020000"
```

**특징:**
- UTC 기준 생성 (서버 시간대 무관)
- 정렬 가능한 형식
- 파일명 충돌 방지

---

### 6. `format_for_display()` - 사용자 표시용

**사용 시기:** 로그, 문서, HTTP 응답 본문

```python
from infra.utils.datetime_utils import format_for_display, utc_now

# UTC suffix 포함 (권장)
dt = utc_now()
text = format_for_display(dt)
print(text)  # "2025-10-26 02:00:00 UTC"

# UTC suffix 제외
text = format_for_display(dt, include_tz=False)
print(text)  # "2025-10-26 02:00:00"

# 로그 예시
logger.info(f"Token refreshed at {format_for_display(utc_now())}")
```

**특징:**
- 사람이 읽기 쉬운 형식
- UTC 명시로 혼란 방지
- 로그 분석 용이

---

### 7. `is_expired()` - 만료 검사

**사용 시기:** 토큰/세션 만료 체크

```python
from infra.utils.datetime_utils import is_expired, utc_now
from datetime import timedelta

# 기본 사용
expires_at = "2025-10-26T02:00:00Z"
if is_expired(expires_at):
    print("Token expired")

# 버퍼 시간 적용 (만료 60초 전에 갱신)
near_expiry = utc_now() + timedelta(seconds=30)
if is_expired(near_expiry, buffer_seconds=60):
    print("Renew token soon")  # True

# datetime 객체도 지원
expires_dt = utc_now() - timedelta(hours=1)
is_expired(expires_dt)  # True
```

**특징:**
- ISO 문자열, datetime 모두 지원
- 버퍼 시간으로 사전 갱신 가능
- UTC 비교로 정확성 보장

---

### 8. `time_until_expiry()` - 남은 시간 계산

**사용 시기:** 모니터링, 로그

```python
from infra.utils.datetime_utils import time_until_expiry, utc_now
from datetime import timedelta

# 남은 시간 계산
expires_at = utc_now() + timedelta(hours=2)
remaining = time_until_expiry(expires_at)

print(remaining.total_seconds())  # ~7200
print(remaining.total_seconds() / 60)  # ~120 minutes

# 만료된 경우 음수
past = utc_now() - timedelta(hours=1)
remaining = time_until_expiry(past)
print(remaining.total_seconds())  # -3600

# 로그 예시
logger.info(f"Token expires in {time_until_expiry(expires_at).total_seconds()/60:.1f} minutes")
```

**특징:**
- timedelta 반환
- 음수 = 이미 만료
- 로깅/모니터링에 유용

---

## 실전 예시

### 토큰 발급 및 검증

```python
from infra.utils.datetime_utils import utc_now, utc_now_iso, is_expired
from datetime import timedelta

# 1. 토큰 발급
access_token = "abc123"
expires_in = 3600  # seconds
expires_at = utc_now() + timedelta(seconds=expires_in)

# DB 저장 (ISO with 'Z')
db.execute("""
    INSERT INTO tokens (token, expires_at)
    VALUES (?, ?)
""", (access_token, expires_at.isoformat().replace('+00:00', 'Z')))

# 또는 헬퍼 사용
db.execute("""
    INSERT INTO tokens (token, expires_at, created_at)
    VALUES (?, ?, ?)
""", (access_token, utc_now_iso(), utc_now_iso()))

# 2. 토큰 검증
token_row = db.fetch_one("SELECT expires_at FROM tokens WHERE token = ?", (access_token,))
expires_at_str = token_row[0]

if is_expired(expires_at_str):
    raise TokenExpiredError("Token has expired")

# 3. 갱신 필요 여부 (60초 버퍼)
if is_expired(expires_at_str, buffer_seconds=60):
    refresh_token()
```

---

### 메일 저장 폴더 생성

```python
from infra.utils.datetime_utils import utc_now, to_local_filename

# 메일 수신 시각
received_time = utc_now()

# 폴더명 생성 (UTC 기준)
folder_name = f"{subject}_{to_local_filename(received_time)}_{sender}"
# "Meeting_20251026_020000_john@example.com"

# 폴더 생성
email_dir = base_dir / folder_name
email_dir.mkdir(parents=True, exist_ok=True)

# 메일 저장
email_file = email_dir / "email.txt"
email_file.write_text(email_content)
```

**장점:**
- 모든 서버에서 동일한 폴더명
- 정렬 가능 (시간순)
- 충돌 없음 (초 단위 구분)

---

### HTTP API 응답

```python
from infra.utils.datetime_utils import utc_now_iso, format_for_display

# JSON 응답
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": utc_now_iso(),  # "2025-10-26T02:00:00Z"
        "server": "mail-server"
    }

# 문서 생성
def export_summary(emails):
    with open(output_file, 'w') as f:
        f.write(f"# Email Summary\n\n")
        f.write(f"Generated: {format_for_display(utc_now())}\n\n")
        # "Generated: 2025-10-26 02:00:00 UTC"

        for email in emails:
            f.write(f"- {email['subject']}\n")
```

---

### 날짜 범위 쿼리

```python
from infra.utils.datetime_utils import utc_now
from datetime import timedelta

# 최근 7일간 메일 조회
end_date = utc_now()
start_date = end_date - timedelta(days=7)

emails = query_emails(
    user_id="john@example.com",
    start_date=start_date.isoformat(),
    end_date=end_date.isoformat()
)

# 또는 datetime_parser 사용 (KST 입력 지원)
from infra.utils.datetime_parser import parse_date_range

start, end, days = parse_date_range(
    start_date_str="2025-10-01",
    end_date_str="2025-10-26",
    input_tz=Timezone.KST,
    output_tz=Timezone.UTC
)
```

---

## 마이그레이션 가이드

### 기존 코드 업데이트

#### Before (naive)
```python
from datetime import datetime, timedelta

# 현재 시각
now = datetime.now()

# 토큰 만료
expires_at = datetime.now() + timedelta(hours=1)
expires_str = expires_at.isoformat()  # "2025-10-26T10:00:00"

# DB 저장
db.execute("INSERT INTO tokens (expires_at) VALUES (?)", (expires_str,))

# 만료 검사
db_expires = datetime.fromisoformat(expires_str)
if db_expires < datetime.now():
    raise TokenExpiredError()
```

#### After (UTC aware)
```python
from datetime import timedelta
from infra.utils.datetime_utils import utc_now, utc_now_iso, is_expired

# 현재 시각
now = utc_now()

# 토큰 만료
expires_at = utc_now() + timedelta(hours=1)
expires_str = expires_at.isoformat().replace('+00:00', 'Z')
# 또는
expires_str = utc_now_iso()  # "2025-10-26T02:00:00Z"

# DB 저장
db.execute("INSERT INTO tokens (expires_at) VALUES (?)", (expires_str,))

# 만료 검사
if is_expired(expires_str):
    raise TokenExpiredError()
```

---

## FAQ

### Q1: 기존 naive timestamp는 어떻게 처리하나요?

**A:** `ensure_utc()` 사용
```python
from infra.utils.datetime_utils import ensure_utc

# DB에서 조회한 naive timestamp
db_time = datetime.fromisoformat("2025-10-26T10:00:00")

# UTC aware로 변환
aware_time = ensure_utc(db_time)
```

### Q2: KST 시간을 입력받으면 어떻게 하나요?

**A:** `datetime_parser` 사용
```python
from infra.utils.datetime_parser import parse_start_date, Timezone

# KST 입력 → UTC 변환
kst_input = "2025-10-26"
utc_dt = parse_start_date(kst_input, input_tz=Timezone.KST, output_tz=Timezone.UTC)
```

### Q3: 로컬 파일명에 KST를 사용하고 싶어요

**A:** 명시적 변환 필요 (권장하지 않음)
```python
from infra.utils.datetime_utils import utc_now
from datetime import timezone, timedelta

# UTC → KST 변환 (예외적 사용)
utc = utc_now()
KST = timezone(timedelta(hours=9))
kst = utc.astimezone(KST)

filename = f"backup_{kst.strftime('%Y%m%d_%H%M%S_KST')}.json"
```

**참고:** 일관성을 위해 UTC 사용 권장

### Q4: DB migration은 필수인가요?

**A:** 기존 데이터가 있다면 권장
```bash
# 마이그레이션 실행
python3 infra/migrations/migrate_timezone_aware.py

# 자동 백업 생성됨
# data/graphapi_backup_YYYYmmdd_HHMMSS.db
```

### Q5: 테스트 코드는 어떻게 작성하나요?

**A:** `utc_now()` 사용
```python
from infra.utils.datetime_utils import utc_now
from datetime import timedelta

def test_token_expiry():
    # 미래 시각 생성
    future = utc_now() + timedelta(hours=1)

    # 과거 시각 생성
    past = utc_now() - timedelta(hours=1)

    assert not is_expired(future)
    assert is_expired(past)
```

---

## 체크리스트

새로운 코드 작성 시 확인하세요:

- [ ] `datetime.now()` 대신 `utc_now()` 사용
- [ ] DB 저장 시 `utc_now_iso()` 또는 `isoformat().replace('+00:00', 'Z')` 사용
- [ ] HTTP 응답에 timezone 정보 포함 ('Z' suffix)
- [ ] 파일명은 `to_local_filename()` 사용
- [ ] 문서/로그는 `format_for_display()` 사용
- [ ] 만료 검사는 `is_expired()` 사용
- [ ] naive datetime 발견 시 `ensure_utc()` 사용
- [ ] `.replace(tzinfo=None)` 패턴 제거

---

## 참고 문서

- [TIMEZONE_ANALYSIS.md](./TIMEZONE_ANALYSIS.md) - 상세 분석 및 마이그레이션 계획
- [infra/utils/datetime_utils.py](../infra/utils/datetime_utils.py) - 헬퍼 함수 구현
- [infra/utils/datetime_parser.py](../infra/utils/datetime_parser.py) - 날짜 파싱 유틸리티

---

**마지막 업데이트:** 2025-10-26
**작성자:** Claude Code
