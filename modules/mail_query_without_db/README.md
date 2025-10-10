# Mail Query Without DB Module

이 모듈은 Microsoft Graph API를 통해 이메일의 첨부파일을 다운로드하고 텍스트로 변환하며, 데이터베이스 없이 이메일을 저장하는 기능을 제공합니다.

## 주요 컴포넌트

### 1. AttachmentDownloader
첨부파일을 다운로드하고 로컬에 저장하는 클래스입니다.

- **주요 기능**:
  - Microsoft Graph API를 통한 첨부파일 다운로드
  - Base64 디코딩
  - 안전한 파일명 생성
  - 사용자별 디렉토리 구조 관리
  - 대용량 첨부파일 처리 지원

### 2. FileConverter
다양한 문서 형식을 텍스트로 변환하는 클래스입니다.

- **지원 형식**:
  - **텍스트**: `.txt`, `.log`, `.md`, `.csv`
  - **PDF**: `.pdf` (PyPDF2 필요)
  - **Word**: `.doc`, `.docx` (python-docx 필요)
  - **Excel**: `.xls`, `.xlsx` (openpyxl 필요)
  - **HWP**: `.hwp` (hwp5html 권장, pyhwp 또는 hwp5 대체 가능)
  - **이미지**: `.jpg`, `.jpeg`, `.png`, `.gif`, `.bmp`, `.tiff` (pytesseract, PIL 필요)

- **시스템 변환기 우선 사용**:
  - `SystemFileConverter`를 통해 시스템 명령어 기반 변환 시도
  - hwp5html, hwp5txt, pdftotext 등 시스템 도구 활용
  - 시스템 변환 실패 시 Python 라이브러리로 폴백

### 3. EmailSaver
이메일 본문과 메타데이터를 파일로 저장하는 클래스입니다.

- **주요 기능**:
  - 이메일 본문을 텍스트 파일로 저장
  - 메타데이터 CSV 파일 생성 및 관리
  - 폴더명 생성 시 날짜, 시간, 발신자 정보 포함
  - 중복 파일 방지를 위한 순번 추가

## 사용 방법

### mail_query_attachment.py 스크립트 사용

통합 메일 조회 스크립트로 본문과 첨부파일을 함께 처리할 수 있습니다.

#### 기본 사용법
```bash
# 기본 조회 (모든 계정, 최근 30일, 10개)
python -m scripts.mail_query_attachment

# 특정 사용자만 조회
python -m scripts.mail_query_attachment -u kimghw

# 본문과 첨부파일 모두 포함
python -m scripts.mail_query_attachment -u kimghw -b -a
```

#### 명령줄 옵션

**계정 옵션**:
- `-u, --user`: 조회할 사용자 ID - 이메일 주소의 @ 앞부분만 입력 (미지정시 모든 활성 계정)
  ```bash
  # kimghw@krs.co.kr 계정 조회시 'kimghw'만 입력
  python -m scripts.mail_query_attachment -u kimghw
  
  # 여러 계정 조회
  python -m scripts.mail_query_attachment -u kimghw krsdtp
  ```

**조회 옵션**:
- `-d, --days`: 조회할 기간 (일 단위, 기본값: 30)
- `-n, --number`: 계정당 최대 메일 수 (기본값: 10)
- `--start-date`: 시작 날짜 (YYYY-MM-DD 형식)
- `--end-date`: 종료 날짜 (YYYY-MM-DD 형식)
  
  **날짜 우선순위**: 날짜 범위가 지정되면 `-d/--days`는 무시됨
  ```bash
  # days_back 사용
  python -m scripts.mail_query_attachment -d 7 -n 20
  
  # 날짜 범위 지정 (days는 무시됨)
  python -m scripts.mail_query_attachment --start-date 2025-01-01 --end-date 2025-01-31
  
  # 시작날짜만 지정 (오늘까지)
  python -m scripts.mail_query_attachment --start-date 2025-01-15
  
  # 종료날짜만 지정 (days_back 적용)
  python -m scripts.mail_query_attachment --end-date 2025-01-20 -d 7
  ```

**내용 옵션**:
- `-b, --body`: 메일 본문 포함
- `-a, --attachments`: 첨부파일 다운로드
- `--has-attachments`: 첨부파일이 있는 메일만 조회
- `--no-attachments`: 첨부파일이 없는 메일만 조회
  ```bash
  python -m scripts.mail_query_attachment -b --has-attachments -a
  ```

**출력 옵션**:
- `-s, --summary`: 요약만 표시 (상세 내용 생략)
- `-e, --export-csv`: 메일 메타데이터를 CSV 파일로 저장
- `-o, --output`: 첨부파일 저장 디렉토리 (기본값: ./attachments)
  ```bash
  python -m scripts.mail_query_attachment -a -o ./downloads
  ```

### 프로그래밍 방식 사용

```python
from modules.mail_query_without_db import AttachmentDownloader, FileConverter

# 첨부파일 다운로더 초기화
downloader = AttachmentDownloader(output_dir="./attachments")

# 파일 변환기 초기화
converter = FileConverter()

# 첨부파일 다운로드 및 저장
file_path = await downloader.download_and_save(
    graph_client,
    message_id,
    attachment_metadata,
    user_id
)

# 텍스트로 변환
if converter.is_supported(file_path):
    text_content = converter.convert_to_text(file_path)
    text_file_path = converter.save_as_text(file_path, text_content)
```

## 필수 라이브러리 설치

### 기본 패키지
```bash
pip install PyPDF2 python-docx openpyxl pillow pytesseract
```

### HWP 지원 (권장)
```bash
# hwp5html (최상의 변환 품질)
sudo apt-get install hwp5html

# Python 라이브러리 (대체 옵션)
pip install pyhwp hwp5
```

### OCR 지원을 위한 Tesseract 설치
```bash
# Ubuntu
sudo apt-get install tesseract-ocr tesseract-ocr-kor

# macOS
brew install tesseract tesseract-lang

# Windows
# https://github.com/UB-Mannheim/tesseract/wiki 에서 설치
```

## 디렉토리 구조

이메일과 첨부파일은 다음과 같은 구조로 저장됩니다:
```
attachments/
├── kimghw/
│   ├── email_metadata_20250826_131500.csv
│   ├── [제목]_20250826_103045_sender@domain.com/
│   │   ├── email_content.txt
│   │   ├── attachment1.pdf
│   │   ├── attachment1.txt
│   │   └── attachment2.hwp
│   └── [다른제목]_20250827_141530_other@domain.com/
│       ├── email_content.txt
│       └── document.xlsx
└── krsdtp/
    ├── email_metadata_20250826_141500.csv
    └── [회의록]_20250826_090000_meeting@company.com/
        ├── email_content.txt
        └── minutes.docx
```

## 주요 기능

### 1. 메일 조회 및 필터링
- 날짜 범위 지정
- 첨부파일 유무 필터링
- 읽음/안읽음 상태 필터링
- 중요도별 필터링

### 2. 첨부파일 처리
- 자동 다운로드 및 저장
- 안전한 파일명 생성
- 중복 파일명 처리
- 사용자별 디렉토리 분리

### 3. 텍스트 변환
- 다양한 문서 형식 지원
- 인코딩 자동 감지 (UTF-8, CP949, EUC-KR 등)
- OCR을 통한 이미지 텍스트 추출
- 변환된 텍스트 파일 저장
- HWP 파일의 표 데이터 완벽 추출 (hwp5html 사용 시)

### 4. 출력 형식
- 상세 모드: 각 메일의 전체 정보 출력
- 요약 모드: 통계 정보만 출력
- 본문 미리보기 또는 전체 본문 표시
- CSV 파일: 메일 메타데이터 (번호, 제목, 발신자, 수신일시, 첨부파일 등)

## 예제 시나리오

### 시나리오 1: 최근 첨부파일 확인
```bash
# 최근 7일간 받은 첨부파일이 있는 메일 조회 및 다운로드
python -m scripts.mail_query_attachment -d 7 --has-attachments -a
```

### 시나리오 2: 특정 사용자의 메일 상세 조회
```bash
# kimghw 계정의 최근 30일 메일을 본문 포함하여 조회
python -m scripts.mail_query_attachment -u kimghw -b
```

### 시나리오 3: 대량 메일 요약 조회
```bash
# 모든 계정의 최근 60일 메일을 요약만 표시
python -m scripts.mail_query_attachment -d 60 -s
```

### 시나리오 4: 첨부파일 텍스트 변환
```bash
# 첨부파일을 다운로드하고 텍스트로 변환
python -m scripts.mail_query_attachment -u kimghw -a -n 5
```

### 시나리오 5: 본문과 첨부파일 모두 포함한 완전한 메일 조회
```bash
# kimghw 계정의 최근 30일간 메일 20개를 본문과 첨부파일 포함하여 조회
python -m scripts.mail_query_attachment -u kimghw -e -b -a -d 30 -n 20

# 파라미터 설명:
# -u kimghw: 조회할 사용자 ID (kimghw@krs.co.kr의 @ 앞부분만 입력)
# -e: --export-csv의 약어, 메일 메타데이터를 CSV 파일로 저장
# -b: --body의 약어, 메일 본문 내용을 포함하여 조회
# -a: --attachments의 약어, 첨부파일을 다운로드하고 텍스트로 변환
# -d 30: --days의 약어, 최근 30일간의 메일 조회
# -n 20: --number의 약어, 계정당 최대 20개의 메일 조회
```

### 시나리오 6: 날짜 범위를 지정한 메일 조회
```bash
# 2025년 1월의 메일만 조회
python -m scripts.mail_query_attachment -u kimghw --start-date 2025-01-01 --end-date 2025-01-31 -b -a

# 특정 기간의 메일 조회 (2025-01-15부터 현재까지)
python -m scripts.mail_query_attachment -u kimghw --start-date 2025-01-15
```

### 시나리오 7: 특정 파일 형식 분석
```bash
# HWP 파일을 텍스트로 변환
python -c "from modules.mail_query_without_db import FileConverter; fc = FileConverter(); print(fc.convert_to_text('/path/to/file.hwp'))"
```

## 주의사항

1. **권한**: Microsoft Graph API 액세스 권한이 필요합니다.
2. **용량**: 대용량 첨부파일은 다운로드에 시간이 걸릴 수 있습니다.
3. **변환 제한**: 
   - 암호화된 PDF는 변환할 수 없습니다.
   - 복잡한 서식의 문서는 일부 내용이 손실될 수 있습니다.
   - OCR 정확도는 이미지 품질에 따라 달라집니다.
4. **디스크 공간**: 첨부파일 저장을 위한 충분한 디스크 공간이 필요합니다.
5. **폴더명 규칙**: 
   - 폴더명에는 제목, 날짜(시간), 발신자 이메일이 포함됩니다.
   - 공백은 언더스코어(_)로 대체됩니다.
   - 동일한 시간에 동일 제목의 메일은 별개 폴더에 저장됩니다.

## 문제 해결

### 라이브러리 설치 오류
```bash
# 가상환경 사용 권장
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```

### OCR 오류
- Tesseract가 설치되어 있는지 확인
- 한국어 데이터 파일이 설치되어 있는지 확인
- 이미지 품질이 충분한지 확인

### 메모리 부족
- `-n` 옵션으로 한 번에 처리할 메일 수 제한
- 대용량 파일은 별도로 처리

## 최근 업데이트

### 2025-09-05 업데이트
1. **HTTP Streaming MCP 서버 추가** (포트 8002)
   - Claude.ai 웹 인터페이스와 완벽 호환
   - chunked transfer encoding 기반 실시간 스트리밍
   - 자동 파일 정리 기능 추가

2. **텍스트 변환 기능 개선**
   - SystemFileConverter 추가로 시스템 명령어 우선 사용
   - 텍스트 미리보기 3000자로 확장
   - FileConverter 초기화 버그 수정

3. **LLM 응답 최적화**
   - 응답 중요도 2단계로 단순화 (important/general)
   - 형식화 프롬프트 추가로 일관된 응답 형식
   - 이모지 타이틀 추가로 가독성 향상

## 향후 개선사항

1. 병렬 다운로드 지원
2. 압축 파일 내부 문서 처리
3. 더 많은 문서 형식 지원
4. 변환 품질 개선
5. 캐싱 메커니즘 추가

## MCP 서버 지원

이 모듈은 Model Context Protocol (MCP) 서버를 통해 AI 모델에 이메일 및 첨부파일 조회 기능을 제공합니다.

### MCP 서버 구현 방식

#### HTTP Streaming 기반 서버 (포트 8002)
- **구현 방식**: HTTP chunked transfer encoding을 사용한 스트리밍 통신
- **호환성**: Claude.ai 웹 인터페이스와 완벽 호환
- **특징**: 
  - 실시간 스트리밍 응답 지원
  - 자동 파일 정리 기능 (응답 후 다운로드 파일 삭제)
  - 텍스트 미리보기 3000자로 확장
  - LLM 응답 형식화 프롬프트 포함

### MCP 서버 실행

#### 1. 로컬 실행
```bash
# HTTP Streaming MCP 서버 시작 (포트 8002)
python -m modules.mail_query_without_db.mcp_server_mail_attachment

# 또는 스크립트 사용
./run_mcp_server.sh
```

#### 2. Cloudflare 터널을 통한 원격 접속

##### 방법 1: 자동 실행 (권장)
```bash
# 서버와 터널을 함께 실행
./run_mcp_server.sh --tunnel

# 또는
./run_mcp_server.sh -t
```

##### 방법 2: 수동 실행
```bash
# 터미널 1: MCP 서버 실행
python -m modules.mail_query_without_db.mcp_server_mail_attachment

# 터미널 2: Cloudflare 터널 실행
cloudflared tunnel --url http://localhost:8002
```

##### 접속 방법
1. Cloudflare 터널 실행 시 생성되는 URL 확인:
   ```
   https://example-random-words.trycloudflare.com
   ```

2. Claude.ai 또는 MCP 클라이언트에서 위 URL을 MCP 서버로 등록

3. 접속 확인:
   - 헬스체크: `https://[your-tunnel-url]/health`
   - 서버 정보: `https://[your-tunnel-url]/info`

##### 주의사항
- 터널 URL은 실행할 때마다 변경됨
- 두 프로세스(서버 & 터널) 모두 실행 중이어야 함
- 무료 서비스로 임시/개발 용도에 적합

### 제공되는 MCP 도구

#### 1. query_email (📧 Query Email)
메일 조회 및 첨부파일 자동 텍스트 변환
- **기능**: 
  - 이메일 본문 조회
  - 첨부파일 다운로드 및 텍스트 변환
  - 중요도별 응답 형식화 (중요/일반)
  - 자동 파일 정리
- **옵션**:
  - `user_id`: 사용자 ID (이메일 @ 앞부분)
  - `days_back`: 조회 기간
  - `start_date/end_date`: 날짜 범위 지정
  - `include_body`: 본문 포함 여부
  - `download_attachments`: 첨부파일 처리 여부
  - `urgency_level`: 응답 중요도 (important/general)

#### 2. list_active_accounts (👥 List Active Accounts)
활성 이메일 계정 목록 조회

#### 3. convert_file_to_text (📄 Convert File to Text)
로컬 파일을 텍스트로 변환
- **지원 형식**: PDF, Word, Excel, HWP, 이미지 등
- **시스템 변환기 우선 사용**: hwp5html, hwp5txt 등