#!/bin/bash

echo "🧪 리팩토링 전체 테스트 실행"
echo ""

PYTHONPATH=/home/kimghw/IACSGRAPH/modules
VENV=/home/kimghw/IACSGRAPH/.venv/bin/python3

# Phase 1
echo "============================================================"
echo "Phase 1: Utils 통합 테스트"
echo "============================================================"
PYTHONPATH=$PYTHONPATH $VENV test_phase1_utils.py
PHASE1=$?
echo ""

# Phase 2
echo "============================================================"
echo "Phase 2: Filters 모듈 테스트"
echo "============================================================"
PYTHONPATH=$PYTHONPATH $VENV test_phase2_filters.py
PHASE2=$?
echo ""

# Phase 3
echo "============================================================"
echo "Phase 3: Import 경로 테스트"
echo "============================================================"
PYTHONPATH=$PYTHONPATH $VENV test_phase3_imports.py
PHASE3=$?
echo ""

# Integration
echo "============================================================"
echo "통합 테스트"
echo "============================================================"
PYTHONPATH=$PYTHONPATH $VENV test_integration.py
INTEGRATION=$?
echo ""

# Summary
echo "============================================================"
echo "📊 테스트 결과 요약"
echo "============================================================"

if [ $PHASE1 -eq 0 ]; then
    echo "✅ Phase 1: Utils 통합 테스트 PASSED"
else
    echo "❌ Phase 1: Utils 통합 테스트 FAILED"
fi

if [ $PHASE2 -eq 0 ]; then
    echo "✅ Phase 2: Filters 모듈 테스트 PASSED"
else
    echo "❌ Phase 2: Filters 모듈 테스트 FAILED"
fi

if [ $PHASE3 -eq 0 ]; then
    echo "✅ Phase 3: Import 경로 테스트 PASSED"
else
    echo "❌ Phase 3: Import 경로 테스트 FAILED"
fi

if [ $INTEGRATION -eq 0 ]; then
    echo "✅ 통합 테스트 PASSED"
else
    echo "❌ 통합 테스트 FAILED"
fi

echo ""
echo "============================================================"

# Check if all tests passed
if [ $PHASE1 -eq 0 ] && [ $PHASE2 -eq 0 ] && [ $PHASE3 -eq 0 ] && [ $INTEGRATION -eq 0 ]; then
    echo "🎉 All tests PASSED!"
    echo ""
    echo "리팩토링이 성공적으로 완료되었습니다."
    echo ""
    echo "다음 단계:"
    echo "1. MCP 서버 실행: ./entrypoints/local/run_http.sh"
    echo "2. 실제 메일 조회 테스트"
    exit 0
else
    echo "⚠️  Some tests FAILED!"
    echo ""
    echo "위의 실패한 테스트를 확인하세요."
    exit 1
fi
