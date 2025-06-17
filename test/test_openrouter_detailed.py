#!/usr/bin/env python3
"""OpenRouter API 상세 디버깅 테스트"""
import asyncio
import sys
import os
import aiohttp
import json

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from infra.core.config import get_config


async def test_direct_openrouter_call():
    """OpenRouter API 직접 호출 테스트"""
    print("=== OpenRouter API 직접 호출 상세 테스트 ===\n")
    
    config = get_config()
    
    if not config.openrouter_api_key:
        print("❌ OpenRouter API 키가 설정되지 않았습니다!")
        return
    
    print(f"✅ API Key: {config.openrouter_api_key[:10]}...")
    print(f"✅ Model: {config.openrouter_model}")
    
    url = "https://openrouter.ai/api/v1/chat/completions"
    headers = {
        "Authorization": f"Bearer {config.openrouter_api_key}",
        "Content-Type": "application/json",
        "HTTP-Referer": "https://iacsgraph.local",
        "X-Title": "IACSGRAPH Mail Processor"
    }
    
    payload = {
        "model": "openai/gpt-3.5-turbo",  # 더 안정적인 모델로 변경
        "messages": [
            {
                "role": "user", 
                "content": "다음 이메일에서 키워드 5개를 추출해주세요: [EA004] 프로젝트 진행 상황 보고서"
            }
        ],
        "max_tokens": 200,  # 토큰 수 증가
        "temperature": 0.3
    }
    
    print(f"\n📤 요청 URL: {url}")
    print(f"📤 요청 헤더: {json.dumps(headers, indent=2, ensure_ascii=False)}")
    print(f"📤 요청 페이로드: {json.dumps(payload, indent=2, ensure_ascii=False)}")
    
    try:
        async with aiohttp.ClientSession() as session:
            print("\n🔄 API 호출 중...")
            
            async with session.post(url, headers=headers, json=payload, timeout=aiohttp.ClientTimeout(total=30)) as response:
                print(f"\n📥 응답 상태: {response.status}")
                print(f"📥 응답 헤더: {dict(response.headers)}")
                
                # 응답 텍스트 전체 읽기
                response_text = await response.text()
                print(f"📥 응답 텍스트 (원본): {response_text}")
                
                if response.status == 200:
                    try:
                        data = json.loads(response_text)
                        print(f"📥 파싱된 JSON: {json.dumps(data, indent=2, ensure_ascii=False)}")
                        
                        if 'choices' in data and data['choices']:
                            if 'message' in data['choices'][0]:
                                content = data['choices'][0]['message'].get('content', '')
                                print(f"✅ 추출된 내용: '{content}'")
                                
                                if content.strip():
                                    keywords = [kw.strip() for kw in content.split(',')]
                                    print(f"✅ 파싱된 키워드: {keywords}")
                                else:
                                    print("⚠️ 내용이 비어있습니다")
                            else:
                                print("❌ choices[0]에 message가 없습니다")
                        else:
                            print("❌ 응답에 choices가 없습니다")
                            
                    except json.JSONDecodeError as e:
                        print(f"❌ JSON 파싱 오류: {e}")
                        
                else:
                    print(f"❌ API 호출 실패: {response.status}")
                    print(f"❌ 오류 내용: {response_text}")
                    
    except Exception as e:
        print(f"❌ 예외 발생: {str(e)}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_direct_openrouter_call())
