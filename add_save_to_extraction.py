#!/usr/bin/env python3
import re

filepath = '/home/kimghw/IACSGRAPH/modules/keyword_extractor/services/extraction_service.py'
with open(filepath, 'r') as f:
    content = f.read()

# Path import 추가
if 'from pathlib import Path' not in content:
    import_pos = content.find('from datetime import datetime')
    if import_pos > 0:
        end_of_line = content.find('\n', import_pos)
        content = content[:end_of_line+1] + 'from pathlib import Path\n' + content[end_of_line+1:]

# 저장 메서드 추가
save_method = '''
    def _save_structured_response(self, text: str, subject: str, sent_time: Optional[datetime], result: Dict[str, Any]) -> None:
        """구조화된 응답을 파일로 저장"""
        try:
            # 저장 디렉토리 설정
            base_dir = Path("/home/kimghw/IACSGRAPH/data/mail_analysis_results")
            base_dir.mkdir(parents=True, exist_ok=True)
            
            # 파일명 생성 (날짜 기반)
            date_str = datetime.now().strftime("%Y%m%d")
            filename = f"mail_analysis_results_{date_str}.jsonl"
            filepath = base_dir / filename
            
            # 저장할 데이터 구성
            analysis_data = {
                "timestamp": datetime.now().isoformat(),
                "subject": subject,
                "sent_time": sent_time.isoformat() if sent_time and hasattr(sent_time, 'isoformat') else str(sent_time),
                "body_content": text[:2000],  # 처음 2000자만
                "model": self.model,
                "analysis_result": result
            }
            
            # JSONL 파일에 추가 모드로 저장
            with open(filepath, 'a', encoding='utf-8') as f:
                json.dump(analysis_data, f, ensure_ascii=False)
                f.write('\\n')
            
            self.logger.debug(f"구조화된 응답 저장: {filepath}")
            
        except Exception as e:
            self.logger.error(f"구조화된 응답 저장 실패: {str(e)}")
'''

# _call_openrouter_structured_api 메서드에서 결과 저장 호출 추가
# result를 반환하기 전에 저장
structured_pattern = r'(if "usage" in data:\s+result\[\'token_usage\'\] = data\["usage"\]\s+)(return result)'
match = re.search(structured_pattern, content, re.MULTILINE)
if match:
    save_call = '''
                            # 구조화된 응답 저장
                            if result and 'mail_type' in result:
                                self._save_structured_response(limited_content, subject, sent_time, result)
                            
                            '''
    content = content[:match.end(1)] + save_call + content[match.end(1):]

# 클래스 끝부분에 저장 메서드 추가
class_end = content.rfind('    async def close(self):')
if class_end > 0:
    content = content[:class_end] + save_method + '\n\n' + content[class_end:]

# 파일 저장
with open(filepath, 'w') as f:
    f.write(content)

print("extraction_service.py에 저장 기능이 추가되었습니다.")
