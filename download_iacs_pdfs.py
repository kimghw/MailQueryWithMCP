import os
import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
import re
import time

# IACS UR-Z 페이지 URL
base_url = "https://iacs.org.uk/resolutions/unified-requirements/ur-z"

# PDF 저장 폴더
save_folder = "UR-Z_PDFs"
os.makedirs(save_folder, exist_ok=True)

# 세션 생성 (쿠키 유지를 위해)
session = requests.Session()
session.headers.update({
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
})

# 웹페이지 요청
print(f"웹페이지 요청 중: {base_url}")
response = session.get(base_url)
print(f"응답 상태 코드: {response.status_code}")
soup = BeautifulSoup(response.text, "html.parser")

# 다운로드 링크 추출
download_links = []
print("\n다운로드 링크 검색 중...")

# "DOWNLOAD FILE" 버튼을 찾아서 링크 추출
for a_tag in soup.find_all("a", href=True):
    href = a_tag.get("href", "")
    text = a_tag.get_text(strip=True)
    
    # 다운로드 링크 패턴 확인
    if "download" in href.lower() or "DOWNLOAD FILE" in text:
        full_url = urljoin(base_url, href)
        # 중복 제거
        if full_url not in [link[0] for link in download_links]:
            # 문서 제목 찾기
            parent = a_tag.parent
            while parent and parent.name not in ['div', 'section', 'article']:
                parent = parent.parent
            
            title = "Unknown"
            if parent:
                # h2, h3, h4 태그에서 제목 찾기
                title_elem = parent.find(['h2', 'h3', 'h4'])
                if title_elem:
                    title = title_elem.get_text(strip=True)
            
            download_links.append((full_url, title))
            print(f"다운로드 링크 발견: {title}")

print(f"\n총 {len(download_links)}개의 다운로드 링크를 발견했습니다.")

# 파일 다운로드
if download_links:
    for i, (url, title) in enumerate(download_links, 1):
        print(f"\n[{i}/{len(download_links)}] {title} 다운로드 중...")
        
        try:
            # 파일 다운로드
            response = session.get(url, stream=True, allow_redirects=True)
            response.raise_for_status()
            
            # 파일명 추출
            filename = None
            
            # Content-Disposition 헤더에서 파일명 추출
            if 'content-disposition' in response.headers:
                cd = response.headers['content-disposition']
                filename_match = re.search(r'filename[^;=\n]*=(([\'"]).*?\2|[^;\n]*)', cd)
                if filename_match:
                    filename = filename_match.group(1).strip('"\'')
            
            # URL에서 파일명 추출
            if not filename:
                parsed_url = urlparse(response.url)
                filename = os.path.basename(parsed_url.path)
            
            # 파일명이 없거나 .pdf가 아닌 경우
            if not filename or not filename.endswith('.pdf'):
                # 제목을 기반으로 파일명 생성
                safe_title = re.sub(r'[^\w\s-]', '', title)
                safe_title = re.sub(r'[-\s]+', '-', safe_title)
                filename = f"{safe_title}.pdf"
            
            filepath = os.path.join(save_folder, filename)
            
            # 파일 저장
            with open(filepath, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)
            
            print(f"✅ {filename} 다운로드 완료")
            
            # 서버 부하 방지를 위한 짧은 대기
            time.sleep(1)
            
        except Exception as e:
            print(f"❌ {title} 다운로드 실패: {e}")
    
    print("\n✅ 모든 파일 다운로드 작업 완료.")
else:
    print("\n❌ 다운로드 링크를 찾을 수 없습니다.")
    
    # API 엔드포인트 확인
    print("\nAPI 엔드포인트 확인 중...")
    
    # IACS API URL 패턴 시도
    api_urls = [
        "https://iacs.org.uk/api/resolutions/ur-z",
        "https://iacs.org.uk/api/documents/ur-z",
        "https://iacs.org.uk/download/ur-z"
    ]
    
    for api_url in api_urls:
        try:
            print(f"시도 중: {api_url}")
            response = session.get(api_url)
            if response.status_code == 200:
                print(f"✅ API 응답 성공: {api_url}")
                # JSON 응답 처리
                if response.headers.get('content-type', '').startswith('application/json'):
                    data = response.json()
                    print(f"JSON 데이터: {data}")
                break
        except Exception as e:
            print(f"❌ API 요청 실패: {e}")
