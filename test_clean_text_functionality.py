"""텍스트 정제 기능 테스트"""
import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from modules.mail_processor._mail_processor_helpers import MailProcessorDataHelper

def test_clean_text():
    """_clean_text 메서드 테스트"""
    
    # 테스트 케이스 1: 사용자가 제공한 실제 메일 content
    test_content = "수신: 한나래호 이진영 3항사님\r\n발신: 한국선급 이은주 선임\r\n\r\n이진영 3항사님께,\r\n\r\n안녕하세요. 한국선급 이은주입니다.\r\n\r\n항상 방선 및 작업에 협조해주셔서 감사합니다.\r\n전문가 자문 관련하여 아래와 같이 요청드립니다.\r\n\r\n---------------   아    래  --------------\r\n\r\n자문비 상세\r\n\r\n  *\r\n방선관련 대면 자문\r\n     *\r\n6월 4일: 홍철현 기관장님(30만원), 이경배 일항사(20만원)\r\n     *\r\n6월 5일: 노희재 일기사(20만원), 김거웅 이항사(20만원)\r\n  *\r\n서면 자문\r\n     *\r\n대면자문외 인원(20만원)\r\n\r\n자문관련 요청자료\r\n\r\n  1.\r\n(서면자문) 선내 데이터 및 ChatGPT를 활용한 질의응답 작성\r\n     *\r\n생성형 AI 사용 시 물어보고 싶은 질문과 간략한 예시 답변 작성\r\n     *\r\n노란색 컬럼은 필수 작성 (하나의 아이디어에 대해 여러 질문 가능)\r\n     *   엑셀 샘플 참고하여 인당 질의응답 10개 작성\r\n     *   PSC 업무 관련 질의내용 추가 요청\r\n  2.\r\n\r\n  3.\r\n (대면자문) 디지털트윈 AR앱 개발을 위한 위치별 주요 작업 내용 및 참고 자료\r\n     *\r\n기관실 및 브릿지에서의 주요 업무 및 작업위치 작성 (대표적인 업무로 작성 부탁드립니다.)\r\n     *\r\n인당 작성 필요 X. 작성 분량은 따로 없으며, 종합적으로 작성된 하나의 파일로 전달\r\n     *\r\n필요 자료 목록 작성 및 예시파일 첨부(공유 가능한 범위 내로 첨부 부탁드립니다.)\r\n        *   예시: 매뉴얼, 인스트럭션북, 정오보고서 양식 등\r\n     *\r\n\r\n  4.\r\n(전체작성)자문비 증빙서류\r\n     *\r\n자문일자 기재 기준\r\n        *\r\n대면자문:  대면자문일자\r\n        *\r\n서면자문: 문서 작성 일자\r\n\r\n-------------------------------------\r\n\r\n자문 요청자료는 6월 27일까지 회신해주시면 감사하겠습니다.\r\n\r\n감사합니다.\r\n이은주 드림.\r\n\r\n\r\n\r\nLEE Eunjoo\r\n\r\n\r\n\r\nDeputy Senior Reasearcher\r\n\r\nAI Convergence Center, R&D Part\r\n\r\nIntelligent Core-Technology Lab.\r\n\r\n\r\n\r\nKOREAN REGISTER\r\n\r\n(06178) 12, Teheran-ro 84-gil, Gangnam-gu, Seoul Republic of Korea\r\n\r\nTel +82 70 8799 7976         Fax +82 70 8799 7989\r\n\r\nMobile +82 10 3364 5646\r\n\r\nEmail ejlee@krs.co.kr<mailto:ejlee@krs.co.kr>        Web www.krs.co.kr<http://www.krs.co.kr/>\r\n"
    
    print("=== 원본 텍스트 ===")
    print(f"길이: {len(test_content)} 문자")
    print(f"\\r\\n 개수: {test_content.count('\\r\\n')}")
    print(f"\\r 개수: {test_content.count('\\r')}")
    print("첫 200자:")
    print(repr(test_content[:200]))
    print()
    
    # 텍스트 정제 실행
    cleaned_content = MailProcessorDataHelper._clean_text(test_content)
    
    print("=== 정제된 텍스트 ===")
    print(f"길이: {len(cleaned_content)} 문자")
    print(f"\\r\\n 개수: {cleaned_content.count('\\r\\n')}")
    print(f"\\r 개수: {cleaned_content.count('\\r')}")
    print(f"\\n 개수: {cleaned_content.count('\\n')}")
    print("첫 200자:")
    print(repr(cleaned_content[:200]))
    print()
    
    print("=== 정제된 텍스트 (실제 출력) ===")
    print(cleaned_content[:500])
    print("...")
    print()
    
    # 테스트 케이스 2: HTML 태그가 포함된 경우
    html_content = "<div>안녕하세요.<br/>이것은 <b>HTML</b> 태그가 포함된 텍스트입니다.</div>\r\n\r\n이메일: test@example.com\r\n웹사이트: https://www.example.com"
    
    print("=== HTML 포함 테스트 ===")
    print("원본:", repr(html_content))
    cleaned_html = MailProcessorDataHelper._clean_text(html_content)
    print("정제:", repr(cleaned_html))
    print("실제:", cleaned_html)
    print()

def test_extract_mail_content():
    """extract_mail_content 메서드 테스트"""
    
    # 테스트용 메일 데이터
    test_mail = {
        "id": "test_mail_001",
        "subject": "테스트 메일",
        "body": {
            "contentType": "text",
            "content": "수신: 한나래호 이진영 3항사님\r\n발신: 한국선급 이은주 선임\r\n\r\n안녕하세요. 한국선급 이은주입니다.\r\n\r\n항상 방선 및 작업에 협조해주셔서 감사합니다."
        },
        "bodyPreview": "수신: 한나래호 이진영 3항사님\r\n발신: 한국선급 이은주 선임\r\n안녕하세요..."
    }
    
    print("=== extract_mail_content 테스트 ===")
    extracted_content = MailProcessorDataHelper.extract_mail_content(test_mail)
    
    print(f"추출된 content 길이: {len(extracted_content)} 문자")
    print(f"\\r\\n 개수: {extracted_content.count('\\r\\n')}")
    print(f"\\r 개수: {extracted_content.count('\\r')}")
    print("추출된 content:")
    print(extracted_content)
    print()

def test_bodypreview_cleaning():
    """bodyPreview 정제 테스트"""
    
    # bodyPreview만 있는 메일 데이터
    test_mail_preview_only = {
        "id": "test_mail_002",
        "subject": "테스트 메일 2",
        "bodyPreview": "수신: 한나래호 이진영 3항사님\r\n발신: 한국선급 이은주 선임\r\n\r\n안녕하세요. 한국선급 이은주입니다.\r\n\r\n항상 방선 및 작업에 협조해주셔서 감사합니다.\r\n전문가 자문 관련하여 아래와 같이 요청드립니다."
    }
    
    print("=== bodyPreview 정제 테스트 ===")
    print("원본 bodyPreview:")
    print(repr(test_mail_preview_only["bodyPreview"]))
    print()
    
    # bodyPreview 직접 정제
    cleaned_preview = MailProcessorDataHelper._clean_text(test_mail_preview_only["bodyPreview"])
    print("정제된 bodyPreview:")
    print(repr(cleaned_preview))
    print()
    print("실제 출력:")
    print(cleaned_preview)
    print()
    
    # extract_mail_content로 bodyPreview 추출 (body.content가 없는 경우)
    extracted_from_preview = MailProcessorDataHelper.extract_mail_content(test_mail_preview_only)
    print("extract_mail_content로 추출된 내용:")
    print(extracted_from_preview)
    print()

def test_body_preview_cleaning():
    """body_preview 필드 정제 테스트 (사용자 피드백 케이스)"""
    
    # 사용자가 제공한 실제 케이스
    test_mail_body_preview = {
        "id": "test_mail_003",
        "subject": "Claude Pro Subscription Canceled",
        "body_preview": "Hello Geohwa,\r\n\r\nYour subscription to Claude Pro has been successfully canceled.\r\n\r\nYour access to Claude Pro will expire on Jul 12, 2025.\r\n\r\nWe're sorry to see you go! You can re-subscribe at any time by visiting the Claude billing settings page.\r\n\r\nWarm"
    }
    
    print("=== body_preview 정제 테스트 (사용자 피드백 케이스) ===")
    print("원본 body_preview:")
    print(repr(test_mail_body_preview["body_preview"]))
    print()
    
    # body_preview 직접 정제
    cleaned_body_preview = MailProcessorDataHelper._clean_text(test_mail_body_preview["body_preview"])
    print("정제된 body_preview:")
    print(repr(cleaned_body_preview))
    print()
    print("실제 출력:")
    print(cleaned_body_preview)
    print()

if __name__ == "__main__":
    print("텍스트 정제 기능 테스트 시작\n")
    
    test_clean_text()
    test_extract_mail_content()
    test_bodypreview_cleaning()
    test_body_preview_cleaning()
    
    print("테스트 완료!")
