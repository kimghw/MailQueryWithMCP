"""Conversation-based filtering for email messages"""

from typing import List


class ConversationFilter:
    """대화 필터링 (양방향 메일)"""

    @staticmethod
    def filter_conversation(messages: List, user_id: str, conversation_with: List[str]) -> List:
        """
        특정 사용자와 주고받은 모든 메일 필터링

        Args:
            messages: List of email messages
            user_id: User ID
            conversation_with: List of email addresses to filter conversation with

        Returns:
            Filtered list of messages
        """
        if not conversation_with:
            return messages

        conversation_emails = [email.lower() for email in conversation_with]
        filtered_messages = []

        for mail in messages:
            include_mail = False

            # Get sender email
            sender_email = ConversationFilter._get_sender_email(mail)

            # Check if sender is in conversation_with
            if sender_email in conversation_emails:
                include_mail = True

            # Check if this is a sent mail (from the user)
            elif sender_email and f"{user_id}@" in sender_email:
                # This is a sent mail, check recipients
                if ConversationFilter._has_recipient_in_list(mail, conversation_emails):
                    include_mail = True

            if include_mail:
                filtered_messages.append(mail)

        return filtered_messages

    @staticmethod
    def _get_sender_email(mail) -> str:
        """
        발신자 이메일 추출

        Args:
            mail: Email message object

        Returns:
            Sender email address (lowercase)
        """
        if mail.from_address and isinstance(mail.from_address, dict):
            email_addr = mail.from_address.get("emailAddress", {})
            return email_addr.get("address", "").lower()
        return ""

    @staticmethod
    def _has_recipient_in_list(mail, email_list: List[str]) -> bool:
        """
        수신자 목록에 특정 이메일이 있는지 확인

        Args:
            mail: Email message object
            email_list: List of email addresses to check (lowercase)

        Returns:
            True if any recipient is in the email_list
        """
        if hasattr(mail, "to_recipients") and mail.to_recipients:
            for recipient in mail.to_recipients:
                if isinstance(recipient, dict):
                    recip_addr = recipient.get("emailAddress", {})
                    if isinstance(recip_addr, dict):
                        recip_email = recip_addr.get("address", "").lower()
                        if recip_email in email_list:
                            return True
        return False
