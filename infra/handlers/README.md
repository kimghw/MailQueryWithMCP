# MCP Handlers

재사용 가능한 MCP 핸들러 모듈입니다. Mixin 패턴을 사용하여 다중 상속으로 조합할 수 있습니다.

## 📦 Available Handlers

### 1. **AuthHandlers**
인증 및 계정 관리 기능을 제공합니다.

**제공 도구:**
- `register_account`: 새 계정 등록
- `get_account_status`: 계정 상태 조회
- `start_authentication`: OAuth 인증 시작
- `list_active_accounts`: 활성 계정 목록

### 2. **AttachmentFilterHandlers**
첨부파일 필터링 및 저장 기능을 제공합니다.

**제공 도구:**
- `filter_and_save_attachments`: 키워드 기반 첨부파일 필터링 및 저장

**주요 기능:**
- ✅ 특정 기간 메일 조회
- ✅ 첨부파일명 키워드 필터링 (2개 이상, OR 조건)
- ✅ 여러 경로에 동시 저장 (1개 이상)
- ✅ 대소문자 구분 옵션
- ✅ 발신자 필터 (옵션)
- ✅ 제목 필터 (옵션)

---

## 🚀 Usage

### 기본 사용법

```python
from infra.handlers import AuthHandlers, AttachmentFilterHandlers

class MyHandlers(AuthHandlers, AttachmentFilterHandlers):
    """인증 + 첨부파일 필터링 기능 제공"""

    def __init__(self):
        super().__init__()

    async def handle_list_tools(self):
        # 인증 도구
        auth_tools = self.get_auth_tools()

        # 첨부파일 필터링 도구
        attachment_tools = self.get_attachment_filter_tools()

        return auth_tools + attachment_tools

    async def handle_call_tool(self, name, arguments):
        # 인증 도구 처리
        if self.is_auth_tool(name):
            return await self.handle_auth_tool(name, arguments)

        # 첨부파일 필터링 도구 처리
        elif self.is_attachment_filter_tool(name):
            return await self.handle_attachment_filter_tool(name, arguments)
```

---

## 📎 AttachmentFilterHandlers 상세

### Tool: `filter_and_save_attachments`

특정 기간의 메일을 조회하여 첨부파일명에 키워드가 포함된 파일만 지정된 경로에 저장합니다.

#### 파라미터

| 파라미터 | 타입 | 필수 | 설명 |
|---------|------|------|------|
| `user_id` | string | ✅ | 사용자 ID |
| `start_date` | string | ✅ | 시작 날짜 (ISO: YYYY-MM-DD) |
| `end_date` | string | ✅ | 종료 날짜 (ISO: YYYY-MM-DD) |
| `filename_keywords` | array | ✅ | 키워드 리스트 (2개 이상, OR 조건) |
| `save_paths` | array | ✅ | 저장 경로 리스트 (1개 이상) |
| `case_sensitive` | boolean | ❌ | 대소문자 구분 (기본: false) |
| `sender_filter` | string | ❌ | 발신자 이메일 필터 |
| `subject_filter` | string | ❌ | 메일 제목 키워드 필터 (부분 매칭) |

#### 사용 예시

```python
arguments = {
    "user_id": "kimghw",
    "start_date": "2025-01-01",
    "end_date": "2025-01-31",
    "filename_keywords": ["invoice", "계약서", "receipt"],  # OR 조건
    "save_paths": [
        "/home/kimghw/invoices",
        "/mnt/c/Users/GEOHWA KIM/Documents/invoices"
    ],
    "case_sensitive": False,
    "sender_filter": "billing@company.com",  # 옵션: 발신자 필터
    "subject_filter": "payment due"  # 옵션: 제목 필터
}

result = await handlers.handle_call_tool(
    name="filter_and_save_attachments",
    arguments=arguments
)
```

#### 동작 흐름

```
1. 메일 조회
   └─ 기간: start_date ~ end_date
   └─ 필터: sender_filter (옵션)
   └─ 필터: subject_filter (옵션)
   └─ 필드: attachments 포함

2. 첨부파일 필터링
   └─ 제목 필터 적용 (클라이언트 사이드)
   └─ 첨부파일명에 keywords 포함 확인 (OR)
   └─ 대소문자 구분 옵션 적용

3. 다운로드 & 저장
   └─ Microsoft Graph API에서 다운로드
   └─ 모든 save_paths에 복사
   └─ 중복 파일명 자동 처리 (file_1.pdf, file_2.pdf)

4. 결과 반환
   └─ 저장된 파일 목록
   └─ 통계 정보
```

#### 결과 예시

```
📎 첨부파일 필터링 결과 - kimghw
================================================================================

📅 조회 기간: 2025-01-01 ~ 2025-01-31
🔍 키워드: 'invoice', '계약서'
📁 저장 경로:
  • /home/kimghw/invoices
  • /mnt/c/Users/GEOHWA KIM/Documents/invoices

🔧 필터:
  • 발신자: billing@company.com
  • 제목: 'payment'

📊 통계:
  • 조회된 메일: 150개
  • 전체 첨부파일: 87개
  • 키워드 매칭: 12개
  • 저장된 파일: 24개 (경로별 2개씩)

================================================================================
💾 저장된 파일 목록:

[1] invoice_202501.pdf
   경로: /home/kimghw/invoices/invoice_202501.pdf
   크기: 245,123 bytes
   메일: January Invoice - Payment Due
   날짜: 2025-01-15T09:30:00

[2] 계약서_최종.docx
   경로: /home/kimghw/invoices/계약서_최종.docx
   크기: 128,456 bytes
   메일: 계약서 검토 요청
   날짜: 2025-01-20T14:22:00

...

================================================================================
✅ 첨부파일 필터링 완료
```

---

## 🏗️ Architecture

### Handler + Tool 통합 패턴

각 핸들러는 **MCP 레이어**(Handler)와 **비즈니스 로직**(Tool)을 하나의 클래스에 통합합니다.

```python
class SomeHandlers:
    """Handler + Tool 통합"""

    def __init__(self):
        # Tool 의존성 주입
        self.downloader = AttachmentDownloader()

    # ========== Handler 부분 (MCP 레이어) ==========

    def get_tools(self) -> List[Tool]:
        """Tool 정의"""
        return [Tool(name="some_tool", ...)]

    async def handle_tool(self, name, arguments):
        """라우팅"""
        return await self._some_tool(arguments)

    def is_tool(self, tool_name: str) -> bool:
        """Tool 체크"""
        return tool_name in ["some_tool"]

    # ========== Tool 부분 (비즈니스 로직) ==========

    async def _some_tool(self, arguments):
        """실제 비즈니스 로직"""
        ...
```

### 장점

1. ✅ **재사용성**: 다중 상속으로 기능 조합
2. ✅ **일관성**: AuthHandlers와 동일한 패턴
3. ✅ **간결성**: Handler + Tool 한 곳에서 관리

---

## 📚 Examples

전체 예시 코드는 `examples/attachment_filter_example.py`를 참고하세요.

---

## 🔧 Configuration

### AttachmentFilterConfig

첨부파일 필터링 설정 클래스입니다.

```python
from infra.handlers import AttachmentFilterConfig

config = AttachmentFilterConfig(
    keywords=["invoice", "계약서"],
    save_paths=["/path/to/save1", "/path/to/save2"],
    case_sensitive=False
)
```

**파라미터:**
- `keywords`: 키워드 리스트 (2개 이상)
- `save_paths`: 저장 경로 리스트 (1개 이상)
- `case_sensitive`: 대소문자 구분 여부 (기본: False)

---

## 🧪 Testing

```python
# 테스트 실행
python examples/attachment_filter_example.py
```

---

## 📝 Notes

### 키워드 매칭 규칙

- **OR 조건**: 키워드 중 하나라도 포함되면 매칭
- **부분 매칭**: "invoice" 키워드는 "monthly_invoice.pdf", "invoice_2025.pdf" 모두 매칭
- **대소문자**: `case_sensitive=False`면 "Invoice", "INVOICE", "invoice" 모두 동일

### 파일 저장 규칙

- **경로별 복사**: 모든 `save_paths`에 파일 복사
- **중복 처리**: 파일명이 존재하면 `_1`, `_2` 등 자동 추가
- **디렉토리 생성**: 존재하지 않는 경로는 자동 생성

### 의존성

- `modules/mail_query`: 메일 조회 (MailQueryOrchestrator)
- `modules/mail_process`: 첨부파일 다운로드 (AttachmentDownloader)
- Microsoft Graph API 인증 필요

---

## 🤝 Contributing

새로운 핸들러를 추가하려면:

1. `infra/handlers/your_handler.py` 생성
2. AuthHandlers 패턴 따르기 (Handler + Tool 통합)
3. `infra/handlers/__init__.py`에 export 추가
4. 예시 코드 및 문서 작성
