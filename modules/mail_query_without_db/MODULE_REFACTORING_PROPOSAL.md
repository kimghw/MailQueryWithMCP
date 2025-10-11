# Mail Query Without DB Module - 구조 개선 제안

## 현재 구조 분석

### 디렉토리 구조
```
mail_query_without_db/
├── __init__.py
├── attachment_downloader.py (285 lines)
├── email_saver.py (421 lines)
├── file_converter.py (444 lines)
├── system_file_converter.py (407 lines)
├── config.json
├── README.md
├── mcp_server_mail_attachment.py (35 lines)  # HTTP 진입점
├── mcp_server_stdio.py (125 lines)           # STDIO 진입점
├── mcp_server/
│   ├── __init__.py
│   ├── server.py (492 lines)
│   ├── handlers.py (303 lines)
│   ├── tools.py (662 lines)
│   ├── config.py (175 lines)
│   ├── utils.py (78 lines)
│   ├── prompts.py (124 lines)
│   └── account_auth_tools.py (428 lines)
└── scripts/                                   # 실행 스크립트
    ├── run_mcp_server.sh
    ├── run_stdio.sh
    └── run_with_tunnel.sh
```

## 주요 문제점 및 개선 제안

### 1. 🔴 **누락된 OneDrive 모듈 (높은 우선순위)**

**문제점:**
- `email_saver.py`와 `attachment_downloader.py`에서 존재하지 않는 `onedrive_uploader.py` import
- OneDrive 기능이 설정에는 있지만 실제 구현이 없음

**해결책:**
```python
# Option 1: OneDrive 기능 제거
# email_saver.py와 attachment_downloader.py에서 관련 코드 삭제

# Option 2: OneDrive 구현 추가
# onedrive_uploader.py 파일 생성 및 구현
```

### 2. 🟡 **중복된 진입점 파일**

**문제점:**
- 모듈 루트에 두 개의 진입점 파일이 산재
- `mcp_server_mail_attachment.py` (HTTP)
- `mcp_server_stdio.py` (STDIO)

**해결책:**
```bash
# 진입점 통합
mcp_server/
├── __main__.py      # 통합 진입점
└── run_modes/
    ├── http.py      # HTTP 모드
    └── stdio.py     # STDIO 모드
```

### 3. 🟡 **코드 중복: 파일명 정규화**

**문제점:**
- `_sanitize_filename()` 메서드가 여러 파일에 중복

**해결책:**
```python
# core/utils.py 생성
def sanitize_filename(filename: str) -> str:
    """파일명을 안전하게 정규화"""
    dangerous_chars = ['/', '\\', ':', '*', '?', '"', '<', '>', '|']
    # ... 공통 로직
```

### 4. 🟡 **파일 변환기 아키텍처 개선**

**문제점:**
- `FileConverter`와 `SystemFileConverter` 두 개의 유사한 클래스
- 불명확한 책임 분리

**해결책:**
```python
# converters/base.py
class BaseConverter(ABC):
    @abstractmethod
    def convert_to_text(self, file_path: Path) -> str:
        pass

# converters/python_converter.py
class PythonLibraryConverter(BaseConverter):
    """Python 라이브러리 기반 변환"""

# converters/system_converter.py
class SystemCommandConverter(BaseConverter):
    """시스템 명령어 기반 변환"""

# converters/orchestrator.py
class FileConverterOrchestrator:
    """변환 전략 조정"""
```

### 5. 🟢 **대용량 파일 분할**

**문제점:**
- `tools.py` (662줄) - 너무 많은 책임
- 단일 파일에 모든 도구 로직

**해결책:**
```bash
mcp_server/tools/
├── __init__.py
├── email_tools.py      # 이메일 조회
├── attachment_tools.py # 첨부파일 처리
├── export_tools.py     # CSV/파일 내보내기
├── cleanup_tools.py    # 정리 작업
└── account_tools.py    # 계정 관리
```

## 제안하는 새로운 구조

```bash
mail_query_without_db/
├── __init__.py                    # 공개 API 정의
├── README.md                      # 모듈 문서
├── config/                        # 설정 관리
│   ├── __init__.py
│   ├── config.json               # 기본 설정
│   └── schema.py                 # 설정 스키마 검증
│
├── core/                          # 핵심 기능
│   ├── __init__.py
│   ├── attachment_downloader.py  # 첨부파일 다운로드
│   ├── email_saver.py            # 이메일 저장
│   ├── converters/               # 파일 변환기
│   │   ├── __init__.py
│   │   ├── base.py              # 기본 인터페이스
│   │   ├── python_converter.py  # Python 라이브러리 기반
│   │   ├── system_converter.py  # 시스템 명령어 기반
│   │   └── orchestrator.py     # 변환 조정자
│   └── utils.py                 # 공통 유틸리티
│
├── mcp_server/                   # MCP 서버 구현
│   ├── __init__.py
│   ├── __main__.py              # 통합 진입점
│   ├── server.py                # HTTP 서버
│   ├── stdio_server.py          # STDIO 서버
│   ├── handlers.py              # 프로토콜 핸들러
│   ├── prompts.py               # MCP 프롬프트
│   │
│   ├── tools/                   # 도구 구현 (분할)
│   │   ├── __init__.py
│   │   ├── base.py             # 기본 도구 클래스
│   │   ├── email_query.py      # 이메일 조회
│   │   ├── attachments.py      # 첨부파일 처리
│   │   ├── export.py           # 내보내기 기능
│   │   ├── cleanup.py          # 정리 작업
│   │   └── accounts.py         # 계정 관리
│   │
│   └── auth/                    # 인증 관련
│       ├── __init__.py
│       └── account_manager.py   # 계정 인증 관리
│
├── scripts/                      # 실행 스크립트
│   ├── run_server.sh            # 통합 실행 스크립트
│   ├── run_http.sh              # HTTP 모드
│   ├── run_stdio.sh             # STDIO 모드
│   └── run_tunnel.sh            # 터널 모드
│
└── tests/                        # 테스트 코드
    ├── __init__.py
    ├── test_converters.py
    ├── test_email_saver.py
    └── test_tools.py
```

## 단계별 리팩토링 계획

### Phase 1: 긴급 수정 (1일)
1. ✅ 스크립트를 `scripts/` 폴더로 이동 (완료)
2. OneDrive 관련 코드 정리 또는 구현
3. 중복 코드를 `core/utils.py`로 추출

### Phase 2: 구조 개선 (2-3일)
1. 파일 변환기 아키텍처 재설계
2. `tools.py` 파일을 여러 모듈로 분할
3. 진입점 파일 통합 및 정리

### Phase 3: 품질 개선 (3-5일)
1. 타입 힌트 전체 적용
2. 단위 테스트 추가
3. 문서화 개선
4. 의존성 주입 패턴 적용

## 예상 효과

### 개선 전
- 코드 중복으로 인한 유지보수 어려움
- 불명확한 모듈 구조
- 큰 파일로 인한 낮은 가독성
- 테스트 어려움

### 개선 후
- ✅ 명확한 책임 분리
- ✅ 코드 재사용성 향상
- ✅ 테스트 용이성 증가
- ✅ 유지보수성 개선
- ✅ 확장 가능한 구조

## 추가 권장사항

### 1. **설정 관리 개선**
```python
# config/schema.py
from pydantic import BaseModel

class MCPServerConfig(BaseModel):
    save_directory: str
    max_file_size_mb: int = 50
    blocked_senders: list[str] = []

    class Config:
        validate_assignment = True
```

### 2. **로깅 통합**
```python
# core/logging.py
import logging

def setup_module_logger(name: str) -> logging.Logger:
    """모듈 전용 로거 설정"""
    logger = logging.getLogger(f"mail_query.{name}")
    # ... 설정
    return logger
```

### 3. **에러 처리 표준화**
```python
# core/exceptions.py
class MailQueryError(Exception):
    """기본 예외 클래스"""

class AttachmentError(MailQueryError):
    """첨부파일 관련 에러"""

class ConversionError(MailQueryError):
    """파일 변환 에러"""
```

### 4. **의존성 주입**
```python
# mcp_server/dependencies.py
from typing import Protocol

class DatabaseProtocol(Protocol):
    """데이터베이스 인터페이스"""
    async def get_user(self, user_id: str): ...

class LoggerProtocol(Protocol):
    """로거 인터페이스"""
    def info(self, message: str): ...
```

## 마이그레이션 체크리스트

- [ ] OneDrive 기능 결정 (제거/구현)
- [ ] 중복 코드 제거
- [ ] 파일 변환기 재구조화
- [ ] tools.py 분할
- [ ] 진입점 통합
- [ ] 테스트 코드 추가
- [ ] 문서 업데이트
- [ ] 설정 스키마 검증 추가
- [ ] 타입 힌트 완성
- [ ] CI/CD 파이프라인 구성

## 결론

이 리팩토링을 통해 모듈은:
- 더 명확한 구조를 갖게 됨
- 유지보수가 용이해짐
- 테스트 가능성이 높아짐
- 확장 가능한 아키텍처를 갖게 됨

단계별 접근으로 서비스 중단 없이 점진적 개선이 가능합니다.