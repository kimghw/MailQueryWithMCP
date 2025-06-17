#!/bin/bash

# 데이터베이스 초기화
echo "데이터베이스를 초기화합니다..."
uv run python script/ignore/mail_query_processor.py --clear-data

# 메인 테스트 스크립트 실행
echo "메인 테스트를 실행합니다..."
uv run python modules/mail_process/scripts/test.py
