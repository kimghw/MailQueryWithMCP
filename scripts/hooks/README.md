# Pre-commit Hooks

이 디렉토리는 Git pre-commit hooks를 포함합니다.

## 설치

```bash
# 1. pre-commit 설치
pip install pre-commit

# 2. hook 활성화
pre-commit install
```

## Hooks

### 1. `check_datetime_usage.py`
- **목적:** `datetime.now()` 사용 방지
- **권장:** `utc_now()` from `infra.utils.datetime_utils`
- **문서:** [docs/DATETIME_USAGE_GUIDE.md](../../docs/DATETIME_USAGE_GUIDE.md)

### 2. `check_branch.py`
- **목적:** main/master 브랜치 직접 커밋 방지
- **권장:** feature branch 생성 후 PR

## 수동 실행

```bash
# 모든 파일 검사
pre-commit run --all-files

# 특정 hook만 실행
pre-commit run check-naive-datetime --all-files

# Hook 건너뛰기 (비권장)
git commit --no-verify
```

## 테스트

```bash
# datetime 검사 테스트
python3 scripts/hooks/check_datetime_usage.py path/to/file.py

# branch 검사 테스트
python3 scripts/hooks/check_branch.py
```
