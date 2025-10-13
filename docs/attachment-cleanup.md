# 첨부파일 자동 정리 기능

## 개요

첨부파일을 텍스트로 변환한 후 **자동으로 원본 파일을 삭제**하는 기능입니다. 디스크 공간을 절약하고 임시 파일이 쌓이는 것을 방지합니다.

## 설정

### 기본 설정 ([config.json:41](modules/mail_query_without_db/config.json#L41))

```json
{
  "file_handling": {
    "cleanup_after_query": true
  }
}
```

- **`true`** (기본값): 텍스트 변환 후 원본 파일 삭제
- **`false`**: 파일 보관 (삭제하지 않음)

## 동작 방식

### 1. 첨부파일 다운로드 및 처리

```
메일 조회 요청 (download_attachments=true)
    ↓
첨부파일 다운로드
    ↓
attachments/{user_id}/{메일제목_날짜_발신자}/파일명 에 저장
    ↓
텍스트 변환 (FileConverterOrchestrator)
    ↓
변환된 텍스트 반환 (최대 5000자)
```

### 2. 자동 정리 (cleanup_after_query=true)

```
텍스트 변환 성공
    ↓
원본 첨부파일 삭제
    ↓
폴더가 비어있는지 확인
    ↓
비어있으면 폴더 삭제
    ↓
상위 폴더(user_id)도 비어있으면 삭제
```

## 구현 세부사항

### 코드 위치

[email_query.py:524-553](modules/mail_query_without_db/mcp_server/tools/email_query.py#L524-L553)

```python
# Delete attachment file after successful conversion if cleanup is enabled
if self.config.cleanup_after_query:
    try:
        import os
        file_path = Path(saved_path)
        parent_dir = file_path.parent

        # Delete the file
        os.remove(saved_path)
        logger.info(f"Deleted attachment file after conversion: {saved_path}")
        result["file_deleted"] = True

        # Try to delete parent directory if empty
        try:
            if parent_dir.exists() and not any(parent_dir.iterdir()):
                parent_dir.rmdir()
                logger.info(f"Deleted empty directory: {parent_dir}")

                # Try to delete grandparent directory if empty (user_id folder)
                grandparent_dir = parent_dir.parent
                if grandparent_dir.exists() and not any(grandparent_dir.iterdir()):
                    grandparent_dir.rmdir()
                    logger.info(f"Deleted empty directory: {grandparent_dir}")
        except Exception as dir_error:
            # Ignore directory deletion errors (not critical)
            logger.debug(f"Could not delete empty directory: {str(dir_error)}")

    except Exception as delete_error:
        logger.warning(f"Failed to delete attachment file: {saved_path} - {str(delete_error)}")
        result["file_deleted"] = False
```

### 삭제 조건

파일이 **성공적으로 텍스트로 변환된 경우에만** 삭제됩니다:

✅ **삭제되는 경우:**
- 텍스트 변환 성공
- `cleanup_after_query = true`

❌ **삭제되지 않는 경우:**
- 텍스트 변환 실패
- `cleanup_after_query = false`
- 파일 크기 초과로 다운로드 건너뜀
- 변환 불가능한 파일 형식

## 로그 확인

### 성공 로그

```
INFO - Successfully converted attachment to text: report.pdf (4523 chars, ~1130 tokens)
INFO - Deleted attachment file after conversion: /path/to/attachments/kimghw/메일제목_20251013_sender@example.com/report.pdf
INFO - Deleted empty directory: /path/to/attachments/kimghw/메일제목_20251013_sender@example.com
INFO - Deleted empty directory: /path/to/attachments/kimghw
```

### 실패 로그

```
WARNING - Failed to delete attachment file: /path/to/file.pdf - Permission denied
```

## 응답 예시

### cleanup 활성화 시

```json
{
  "attachments": [
    {
      "name": "report.pdf",
      "size": 524288,
      "status": "converted",
      "text_content": "보고서 내용...",
      "token_count": 1130,
      "file_deleted": true
    }
  ]
}
```

### cleanup 비활성화 시

```json
{
  "attachments": [
    {
      "name": "report.pdf",
      "size": 524288,
      "status": "converted",
      "saved_path": "/path/to/attachments/kimghw/.../report.pdf",
      "text_content": "보고서 내용...",
      "token_count": 1130
    }
  ]
}
```

## 사용 예제

### 1. 첨부파일 포함 조회 (자동 정리)

```
사용자: "최근 한달 간 kimghw 계정에 송수신한 메일을 본문과 첨부파일 내용까지 조회해줘"
```

**결과:**
1. 첨부파일 다운로드
2. 텍스트 변환
3. 텍스트 반환
4. **원본 파일 자동 삭제** ✅

### 2. 정리 비활성화

[config.json](modules/mail_query_without_db/config.json)에서:

```json
{
  "file_handling": {
    "cleanup_after_query": false
  }
}
```

**결과:**
1. 첨부파일 다운로드
2. 텍스트 변환
3. 텍스트 반환
4. **원본 파일 보관** (삭제하지 않음)

## 장점

1. **디스크 공간 절약**: 변환된 텍스트만 메모리에 유지
2. **임시 파일 방지**: 첨부파일이 계속 쌓이지 않음
3. **자동 폴더 정리**: 빈 폴더도 자동으로 삭제
4. **안전성**: 변환 성공한 경우에만 삭제

## 주의사항

1. **원본 파일 복구 불가**: 삭제된 파일은 복구할 수 없음
2. **변환 실패 시 보관**: 변환 실패 시 원본 파일은 유지됨
3. **로그 확인**: 삭제 실패 시 로그에서 원인 확인 가능
4. **프로덕션 권장**: 대량의 메일 조회 시 cleanup 활성화 권장

## 환경별 설정 권장

### 로컬 개발

```json
{
  "file_handling": {
    "cleanup_after_query": false
  }
}
```

**이유**: 디버깅 및 테스트를 위해 파일 보관

### 프로덕션 (Render.com)

```json
{
  "file_handling": {
    "cleanup_after_query": true
  }
}
```

**이유**: 디스크 공간 절약 및 임시 파일 관리

## 문제 해결

### 파일이 삭제되지 않음

**원인:**
- 텍스트 변환 실패
- 파일 권한 문제
- `cleanup_after_query = false`

**해결:**
1. 로그 확인: `logs/modules/mcp_server.log`
2. 변환 상태 확인: `status: "converted"` 인지 확인
3. 설정 확인: `config.json`의 `cleanup_after_query` 값 확인

### 폴더가 삭제되지 않음

**원인:**
- 폴더에 다른 파일이 남아있음
- 폴더 권한 문제

**해결:**
- 정상 동작 (의도된 동작)
- 폴더에 다른 첨부파일이 있으면 삭제되지 않음

## 관련 설정

```json
{
  "file_handling": {
    "max_file_size_mb": 50,           // 최대 파일 크기
    "max_preview_length": 3000,       // 미리보기 길이
    "cleanup_after_query": true       // 자동 정리 활성화
  }
}
```

## 참고

- 첨부파일 다운로드: [AttachmentDownloader](modules/mail_query_without_db/core/attachment_downloader.py)
- 텍스트 변환: [FileConverterOrchestrator](modules/mail_query_without_db/core/converters/__init__.py)
- 메일 조회: [EmailQueryTool](modules/mail_query_without_db/mcp_server/tools/email_query.py)
