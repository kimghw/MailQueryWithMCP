# Windows 실행 파일 빌드 가이드

## 📋 준비사항

1. **Python 설치** (3.9 이상)
   - https://www.python.org/downloads/ 에서 다운로드
   - 설치 시 "Add Python to PATH" 체크

2. **프로젝트 복사**
   - 이 프로젝트를 Windows 컴퓨터로 복사

## 🚀 빌드 방법

### 방법 1: 자동 빌드 (권장)

Windows에서 다음 파일을 더블클릭:
```
build_windows_exe.bat
```

또는 명령 프롬프트에서:
```cmd
build_windows_exe.bat
```

### 방법 2: 수동 빌드

1. **PyInstaller 설치**
   ```cmd
   pip install pyinstaller
   ```

2. **의존성 설치**
   ```cmd
   pip install -r requirements.txt
   ```

3. **빌드 실행**
   ```cmd
   pyinstaller build_exe.spec
   ```

## 📦 빌드 결과

빌드가 완료되면 `dist` 폴더에 생성됩니다:
```
dist/
  └── mcp_mail_server.exe  (실행 파일)
```

## ▶️ 실행 방법

### HTTP 모드 (기본)
```cmd
dist\mcp_mail_server.exe --mode http --port 3000
```

### STDIO 모드 (Claude Desktop 연동)
```cmd
dist\mcp_mail_server.exe --mode stdio
```

### 옵션

- `--mode`: 서버 모드 (`http` 또는 `stdio`)
- `--port`: HTTP 모드 포트 번호 (기본값: 3000)
- `--host`: HTTP 모드 호스트 (기본값: 0.0.0.0)

## 🔧 환경 설정

실행 전 필요한 파일들:

1. **config.json** (필수)
   - `modules/mail_query_without_db/config.json`
   - 또는 `config.user.json`

2. **.env 파일** (선택)
   - 환경변수 설정

3. **enrollment 폴더**
   - 계정 정보 YAML 파일

4. **데이터베이스**
   - SQLite DB 파일 (자동 생성)

## 📝 실행 예제

### 1. HTTP 서버로 실행
```cmd
cd dist
mcp_mail_server.exe --mode http --port 3000
```

브라우저에서 `http://localhost:3000` 접속

### 2. STDIO 모드로 실행 (Claude Desktop용)
```cmd
mcp_mail_server.exe --mode stdio
```

Claude Desktop의 `claude_desktop_config.json`에 추가:
```json
{
  "mcpServers": {
    "mail-query": {
      "command": "C:\\path\\to\\dist\\mcp_mail_server.exe",
      "args": ["--mode", "stdio"]
    }
  }
}
```

## ⚠️ 주의사항

1. **바이러스 백신 경고**
   - PyInstaller로 만든 .exe는 백신 프로그램이 오탐할 수 있습니다
   - Windows Defender에서 예외 추가 필요할 수 있음

2. **파일 크기**
   - 생성된 .exe는 모든 의존성을 포함하여 크기가 큽니다 (50-100MB)

3. **실행 속도**
   - 첫 실행 시 압축 해제로 인해 느릴 수 있습니다

4. **경로 문제**
   - config.json, enrollment 폴더 등이 exe와 같은 위치에 있어야 합니다

## 🐛 문제 해결

### PyInstaller 설치 실패
```cmd
python -m pip install --upgrade pip
pip install pyinstaller
```

### 빌드 실패 - 모듈 누락
spec 파일의 `hiddenimports`에 누락된 모듈 추가:
```python
hiddenimports = [
    'your_missing_module',
    # ...
]
```

### 실행 시 DLL 오류
Visual C++ Redistributable 설치 필요:
- https://aka.ms/vs/17/release/vc_redist.x64.exe

### 실행 파일이 너무 큰 경우
불필요한 의존성 제거 또는 UPX 압축 사용

## 📚 추가 정보

- PyInstaller 문서: https://pyinstaller.org/
- 프로젝트 GitHub: https://github.com/kimghw/MailQueryWithMCP
