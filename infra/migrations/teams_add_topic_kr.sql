-- Teams 채팅 테이블에 한글 이름 컬럼 추가
-- topic_kr: 한글로 번역된 채팅방 이름 (1:1 채팅의 경우 상대방 한글 이름)

ALTER TABLE teams_chats ADD COLUMN topic_kr TEXT;

-- 인덱스 추가 (한글 이름 검색용)
CREATE INDEX IF NOT EXISTS idx_teams_chats_topic_kr_lower
    ON teams_chats (user_id, is_active, LOWER(topic_kr));
