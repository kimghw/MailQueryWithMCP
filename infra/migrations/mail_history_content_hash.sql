-- Mail History 테이블에 content_hash 컬럼 추가
-- 중복 메일 검사를 위한 내용 해시 저장

-- content_hash 컬럼 추가
ALTER TABLE mail_history ADD COLUMN content_hash TEXT;

-- content_hash 인덱스 생성 (중복 검사 성능 향상)
CREATE INDEX idx_mail_history_content_hash ON mail_history (content_hash);

-- 기존 데이터에 대한 content_hash 업데이트는 필요시 별도 스크립트로 처리
