"""Conversation manager for multi-turn query interactions"""

import logging
from typing import Dict, Any, Optional, List
from datetime import datetime
import json

logger = logging.getLogger(__name__)


class ConversationManager:
    """Manages multi-turn conversations for parameter collection"""
    
    def __init__(self):
        self.conversations = {}  # session_id -> conversation_state
        
    def create_session(self, session_id: str) -> None:
        """Create a new conversation session"""
        self.conversations[session_id] = {
            "created_at": datetime.now(),
            "last_activity": datetime.now(),
            "context": {},
            "history": [],
            "pending_template": None,
            "collected_params": {}
        }
        
    def get_session(self, session_id: str) -> Optional[Dict[str, Any]]:
        """Get conversation session"""
        return self.conversations.get(session_id)
    
    def update_session(
        self, 
        session_id: str,
        template_id: Optional[str] = None,
        collected_params: Optional[Dict[str, Any]] = None,
        query: Optional[str] = None
    ) -> None:
        """Update conversation session"""
        if session_id not in self.conversations:
            self.create_session(session_id)
            
        session = self.conversations[session_id]
        session["last_activity"] = datetime.now()
        
        if template_id:
            session["pending_template"] = template_id
            
        if collected_params:
            session["collected_params"].update(collected_params)
            
        if query:
            session["history"].append({
                "timestamp": datetime.now(),
                "query": query,
                "template": template_id,
                "params": collected_params
            })
    
    def clear_session(self, session_id: str) -> None:
        """Clear conversation session"""
        if session_id in self.conversations:
            del self.conversations[session_id]
    
    def cleanup_old_sessions(self, max_age_minutes: int = 30) -> int:
        """Clean up old sessions"""
        now = datetime.now()
        old_sessions = []
        
        for session_id, session in self.conversations.items():
            age = (now - session["last_activity"]).total_seconds() / 60
            if age > max_age_minutes:
                old_sessions.append(session_id)
        
        for session_id in old_sessions:
            del self.conversations[session_id]
            
        return len(old_sessions)
    
    def format_conversation_context(self, session_id: str) -> str:
        """Format conversation context for display"""
        session = self.get_session(session_id)
        if not session:
            return "새로운 대화를 시작합니다."
        
        context = []
        if session["pending_template"]:
            context.append(f"현재 진행 중인 쿼리: {session['pending_template']}")
            
        if session["collected_params"]:
            context.append("수집된 파라미터:")
            for key, value in session["collected_params"].items():
                context.append(f"  - {key}: {value}")
                
        if session["history"]:
            context.append(f"\n최근 {len(session['history'])}개의 쿼리를 수행했습니다.")
            
        return "\n".join(context) if context else "대화 컨텍스트가 비어있습니다."