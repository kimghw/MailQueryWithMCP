"""Keyword-based filtering for email messages"""

from typing import List
import re


class KeywordFilter:
    """클라이언트 사이드 키워드 필터링"""

    @staticmethod
    def filter_by_keywords(messages: List, keyword_filter) -> List:
        """
        AND/OR/NOT 키워드 필터링

        Args:
            messages: List of email messages
            keyword_filter: KeywordFilter object with and_keywords, or_keywords, not_keywords

        Returns:
            Filtered list of messages
        """
        if not keyword_filter:
            return messages

        filtered_messages = []

        for mail in messages:
            mail_text = KeywordFilter._get_searchable_text(mail).lower()
            include_mail = True

            # AND condition: all keywords must be present
            if keyword_filter.and_keywords:
                and_keywords = [kw.lower() for kw in keyword_filter.and_keywords]
                if not all(kw in mail_text for kw in and_keywords):
                    include_mail = False

            # OR condition: at least one keyword must be present
            if include_mail and keyword_filter.or_keywords:
                or_keywords = [kw.lower() for kw in keyword_filter.or_keywords]
                if not any(kw in mail_text for kw in or_keywords):
                    include_mail = False

            # NOT condition: none of these keywords should be present
            if include_mail and keyword_filter.not_keywords:
                not_keywords = [kw.lower() for kw in keyword_filter.not_keywords]
                if any(kw in mail_text for kw in not_keywords):
                    include_mail = False

            if include_mail:
                filtered_messages.append(mail)

        return filtered_messages

    @staticmethod
    def _get_searchable_text(mail) -> str:
        """
        Extract all searchable text from an email

        Args:
            mail: Email message object

        Returns:
            Combined text from all searchable fields
        """
        text_parts = []

        # Add subject
        if hasattr(mail, 'subject') and mail.subject:
            text_parts.append(str(mail.subject))

        # Add body preview or body
        if hasattr(mail, 'body_preview') and mail.body_preview:
            text_parts.append(str(mail.body_preview))
        elif hasattr(mail, 'body') and mail.body:
            if isinstance(mail.body, dict):
                content = mail.body.get('content', '')
                if content:
                    # Remove HTML tags if present
                    content = re.sub('<[^<]+?>', '', content)
                    text_parts.append(content[:1000])  # Limit to first 1000 chars
            else:
                text_parts.append(str(mail.body)[:1000])

        # Add sender information
        if hasattr(mail, 'from_address') and mail.from_address:
            if isinstance(mail.from_address, dict):
                email_addr = mail.from_address.get('emailAddress', {})
                if isinstance(email_addr, dict):
                    sender_email = email_addr.get('address', '')
                    sender_name = email_addr.get('name', '')
                    text_parts.append(sender_email)
                    text_parts.append(sender_name)

        # Add recipient information (for sent emails)
        if hasattr(mail, 'to_recipients') and mail.to_recipients:
            for recipient in mail.to_recipients:
                if isinstance(recipient, dict):
                    email_addr = recipient.get('emailAddress', {})
                    if isinstance(email_addr, dict):
                        text_parts.append(email_addr.get('address', ''))
                        text_parts.append(email_addr.get('name', ''))

        # Add attachment names
        if hasattr(mail, 'attachments') and mail.attachments:
            for attachment in mail.attachments:
                if isinstance(attachment, dict):
                    text_parts.append(attachment.get('name', ''))

        return ' '.join(text_parts)
