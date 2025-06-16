#!/usr/bin/env python3
"""발신자 추출 테스트"""
import json
import sys
import os

# 프로젝트 루트 경로 추가
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from modules.mail_processor._mail_processor_helpers import MailProcessorDataHelper


def test_sender_extraction():
    """실제 메일 샘플로 발신자 추출 테스트"""
    print("=== 발신자 추출 테스트 ===\n")
    
    # 실제 메일 샘플 로드
    sample_file = "data/mail_samples/mail_AAMkADU2MGM5YzRjLTE4NmItNDE4NC_20250616_155821_61320.json"
    
    try:
        with open(sample_file, 'r', encoding='utf-8') as f:
            sample_data = json.load(f)
        
        mail_data = sample_data['mail_data']
        
        print(f"📧 메일 제목: {mail_data.get('subject', 'N/A')[:100]}...")
        print(f"📧 메일 ID: {mail_data.get('id', 'N/A')}")
        
        # 발신자 필드들 확인
        print(f"\n📋 발신자 필드 구조:")
        print(f"  - from: {mail_data.get('from')}")
        print(f"  - sender: {mail_data.get('sender')}")
        print(f"  - from_address: {mail_data.get('from_address')}")
        
        # 발신자 주소 추출 테스트
        sender_address = MailProcessorDataHelper._extract_sender_address(mail_data)
        print(f"\n✅ 추출된 발신자 주소: '{sender_address}'")
        
        if sender_address:
            print("✅ 발신자 추출 성공!")
        else:
            print("❌ 발신자 추출 실패!")
            
        # ProcessedMailData 생성 테스트
        from modules.mail_processor.mail_processor_schema import ProcessingStatus
        
        processed_mail = MailProcessorDataHelper.create_processed_mail_data(
            mail_data, 
            "test_account", 
            ["테스트", "키워드"], 
            ProcessingStatus.SUCCESS
        )
        
        print(f"\n📊 ProcessedMailData 결과:")
        print(f"  - 발신자: '{processed_mail.sender_address}'")
        print(f"  - 제목: '{processed_mail.subject[:50]}...'")
        print(f"  - 메일 ID: '{processed_mail.mail_id}'")
        print(f"  - 키워드: {processed_mail.keywords}")
        
    except Exception as e:
        print(f"❌ 테스트 실패: {str(e)}")
        import traceback
        traceback.print_exc()


def test_various_mail_formats():
    """다양한 메일 형식 테스트"""
    print("\n=== 다양한 메일 형식 테스트 ===\n")
    
    test_cases = [
        {
            "name": "정상적인 from 필드",
            "mail": {
                "id": "test1",
                "subject": "테스트 메일 1",
                "from": {
                    "emailAddress": {
                        "name": "테스트 사용자",
                        "address": "test@example.com"
                    }
                }
            }
        },
        {
            "name": "sender 필드만 있는 경우",
            "mail": {
                "id": "test2",
                "subject": "테스트 메일 2",
                "sender": {
                    "emailAddress": {
                        "name": "발신자",
                        "address": "sender@example.com"
                    }
                }
            }
        },
        {
            "name": "from_address 필드 (GraphMailItem)",
            "mail": {
                "id": "test3",
                "subject": "테스트 메일 3",
                "from_address": {
                    "emailAddress": {
                        "name": "GraphMail 사용자",
                        "address": "graphmail@example.com"
                    }
                }
            }
        },
        {
            "name": "발신자 정보 없음",
            "mail": {
                "id": "test4",
                "subject": "테스트 메일 4"
            }
        },
        {
            "name": "초안 메일",
            "mail": {
                "id": "test5",
                "subject": "초안 메일",
                "isDraft": True
            }
        }
    ]
    
    for test_case in test_cases:
        print(f"📝 {test_case['name']}:")
        sender = MailProcessorDataHelper._extract_sender_address(test_case['mail'])
        print(f"   결과: '{sender}'")
        print()


if __name__ == "__main__":
    test_sender_extraction()
    test_various_mail_formats()
