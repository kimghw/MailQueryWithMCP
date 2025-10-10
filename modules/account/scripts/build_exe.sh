#!/bin/bash
# Windows용 실행 파일 빌드 스크립트

cd /home/kimghw/IACSGRAPH

# PyInstaller 설치 확인
pip install pyinstaller

# 실행 파일 생성
pyinstaller \
  --onefile \
  --name enroll_account \
  --add-data "infra/migrations/initial_schema.sql:infra/migrations" \
  --add-data "enrollment:enrollment" \
  --hidden-import=pydantic \
  --hidden-import=yaml \
  --hidden-import=cryptography \
  --hidden-import=sqlite3 \
  --clean \
  modules/account/scripts/enroll_account.py

echo "빌드 완료: dist/enroll_account 또는 dist/enroll_account.exe"
