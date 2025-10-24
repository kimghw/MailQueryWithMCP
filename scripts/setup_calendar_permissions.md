# Calendar API 권한 설정 가이드

## 문제 상황

Calendar API 호출 시 403 Forbidden 오류 발생:
```
"ErrorAccessDenied": "Access is denied. Check credentials and try again."
```

## 해결 방법

Azure AD 앱 등록에 Calendar 권한을 추가해야 합니다.

### 1. Azure Portal에서 앱 등록 열기

1. Azure Portal (https://portal.azure.com) 접속
2. **Azure Active Directory** → **앱 등록** 이동
3. 사용 중인 앱 선택 (예: `MailQueryWithMCP`)

### 2. API 권한 추가

1. 왼쪽 메뉴에서 **API 권한** 클릭
2. **권한 추가** 버튼 클릭
3. **Microsoft Graph** 선택
4. **위임된 권한** 선택

### 3. Calendar 권한 추가

다음 권한을 검색하여 추가:

**필수 권한:**
- ✅ `Calendars.ReadWrite` - 사용자의 일정 읽기 및 쓰기
  - 일정 조회, 생성, 수정, 삭제에 필요

**선택적 권한 (온라인 회의 사용 시):**
- ✅ `OnlineMeetings.ReadWrite` - 온라인 회의 생성
  - `is_online_meeting=true` 사용 시 필요

**읽기 전용 (조회만 하는 경우):**
- ✅ `Calendars.Read` - 사용자의 일정 읽기만
  - list_events, get_event만 사용하는 경우

### 4. 관리자 동의 부여

1. **권한 추가 후** 권한 목록에서 **"... 에 대한 관리자 동의 부여"** 클릭
2. 동의 확인 팝업에서 **예** 클릭
3. 권한 옆에 녹색 체크 표시 확인

### 5. 토큰 재발급

권한을 추가한 후 기존 토큰은 새 권한을 포함하지 않으므로 재인증이 필요합니다:

```bash
# 방법 1: 계정 재등록
# enrollment 페이지에서 다시 로그인

# 방법 2: 토큰 갱신 (refresh_token이 있는 경우)
# 자동으로 다음 API 호출 시 갱신됨
```

### 6. 권한 확인

현재 설정된 권한 확인:

```bash
# 토큰에 포함된 권한 확인
python3 scripts/check_token_permissions.py
```

## 현재 앱의 권한 상태

**확인된 권한 (정상 작동 중):**
- ✅ Mail.ReadWrite
- ✅ Mail.Send
- ✅ Notes.ReadWrite
- ✅ User.Read
- ✅ Files.ReadWrite.All

**추가 필요:**
- ❌ Calendars.ReadWrite - **지금 추가 필요!**
- ❌ OnlineMeetings.ReadWrite - (선택적)

## 테스트 재실행

권한 추가 및 재인증 후:

```bash
python3 scripts/test_calendar_create.py
```

## 참고

- Azure AD 관리자 권한이 필요할 수 있습니다
- 개인 Microsoft 계정은 OnlineMeetings 권한이 제한될 수 있습니다
- 권한 변경 후 최대 5분까지 전파 시간이 걸릴 수 있습니다
