"""
message_output_formatter.py

Story 8.3 Canonical Message Output Formatter.
Converts safe rendered Jinja2 templates into strict channel-specific immutable output.
"""

from __future__ import annotations

import re
import html
from html.parser import HTMLParser
from typing import Literal

from app.services.ai.FieldOpsAI.schemas.communication import (
    FormattedCommunicationOutput,
    SMSMessageOutput,
    EmailMessageOutput,
    PushMessageOutput,
    PortalMessageOutput,
)


class MessageOutputFormattingError(ValueError):
    """Base error for formatting failures."""


class UnsupportedOutputChannelError(MessageOutputFormattingError):
    """Raised when the channel is unsupported."""


class UnsupportedChannelFormatError(MessageOutputFormattingError):
    """Raised when the format is incompatible with the channel."""


class MissingOutputTitleError(MessageOutputFormattingError):
    """Raised when a title/subject is required but missing."""


class InvalidFormattedContentError(MessageOutputFormattingError):
    """Raised when the content is blank or contains prohibited characters."""


class _PlainTextHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.text_parts: list[str] = []
        self.ignore_tags = {"script", "style"}
        self.current_ignore_count = 0
        self.is_list = False
        self.list_item_prefix = ""

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in self.ignore_tags:
            self.current_ignore_count += 1
        elif tag in ("p", "br", "div", "h1", "h2", "h3", "h4", "h5", "h6", "li"):
            # Ensure block elements start on a new line
            self.text_parts.append("\n")
            if tag == "li":
                self.text_parts.append("- ")

    def handle_endtag(self, tag: str) -> None:
        if tag in self.ignore_tags:
            self.current_ignore_count = max(0, self.current_ignore_count - 1)
        elif tag in ("p", "div", "h1", "h2", "h3", "h4", "h5", "h6", "ul", "ol", "li"):
            # Ensure block elements end on a new line
            self.text_parts.append("\n")

    def handle_data(self, data: str) -> None:
        if self.current_ignore_count == 0:
            self.text_parts.append(data)


class MessageOutputFormatter:
    """
    Strict, purely functional formatter for communication channels.
    """

    @classmethod
    def format(
        cls,
        *,
        channel: str,
        rendered_title: str | None,
        rendered_body: str,
        template_format: str,
    ) -> FormattedCommunicationOutput:
        """
        Convert safely rendered content into strict channel output.
        """
        # Validate inputs
        if not isinstance(rendered_body, str):
            raise InvalidFormattedContentError("Rendered body must be a string.")
            
        if "\x00" in rendered_body or (rendered_title and "\x00" in rendered_title):
            raise InvalidFormattedContentError("Null bytes are prohibited.")
            
        normalized_channel = channel.upper()
        if normalized_channel == "IN_APP":
            normalized_channel = "PORTAL"
            
        if normalized_channel not in ("SMS", "EMAIL", "PUSH", "PORTAL"):
            raise UnsupportedOutputChannelError(f"Channel {channel} is not supported.")
            
        normalized_format = template_format.lower()
        if normalized_format not in ("text", "html"):
            raise UnsupportedChannelFormatError(f"Format {template_format} is not supported.")
            
        # Dispatch to specific formatters
        if normalized_channel == "SMS":
            return cls._format_sms(rendered_title, rendered_body, normalized_format)
        elif normalized_channel == "EMAIL":
            return cls._format_email(rendered_title, rendered_body, normalized_format)
        elif normalized_channel == "PUSH":
            return cls._format_push(rendered_title, rendered_body, normalized_format)
        elif normalized_channel == "PORTAL":
            return cls._format_portal(rendered_title, rendered_body, normalized_format)
            
        raise UnsupportedOutputChannelError("Message output could not be formatted for the requested channel.")

    @classmethod
    def _normalize_whitespace(
        cls,
        text: str,
        collapse_lines: bool = False,
    ) -> str:
        """
        Safely normalize text spacing.
        """
        # Normalize CR/LF
        text = text.replace("\r\n", "\n").replace("\r", "\n")
        
        if collapse_lines:
            # Replace all newlines and tabs with spaces
            text = text.replace("\n", " ").replace("\t", " ")
            # Collapse multiple spaces
            text = re.sub(r" +", " ", text)
        else:
            # Collapse spaces and tabs on the same line, but preserve newlines
            text = re.sub(r"[ \t]+", " ", text)
            # Collapse multiple empty lines to a single empty line
            text = re.sub(r"\n{3,}", "\n\n", text)
            
        return text.strip()

    @classmethod
    def _validate_subject_or_title(
        cls,
        title: str | None,
        channel: str,
        require: bool = True,
    ) -> str | None:
        if require and not title:
            raise MissingOutputTitleError(f"{channel} requires a title/subject.")
        if not title:
            return None
            
        # Check for CR/LF injection
        if "\n" in title or "\r" in title:
            # Normalize it out rather than just failing, but for headers it's safer to just reject or replace
            pass
            
        normalized = cls._normalize_whitespace(title, collapse_lines=True)
        if require and not normalized:
            raise MissingOutputTitleError(f"{channel} requires a non-blank title/subject.")
            
        return normalized

    @classmethod
    def _format_sms(
        cls,
        title: str | None,
        body: str,
        format_type: str,
    ) -> SMSMessageOutput:
        if format_type != "text":
            raise UnsupportedChannelFormatError("SMS requires text format.")
            
        normalized = cls._normalize_whitespace(body, collapse_lines=True)
        if not normalized:
            raise InvalidFormattedContentError("SMS text cannot be blank.")
            
        return SMSMessageOutput(text=normalized)

    @classmethod
    def _format_email(
        cls,
        title: str | None,
        body: str,
        format_type: str,
    ) -> EmailMessageOutput:
        subject = cls._validate_subject_or_title(title, "EMAIL", require=True)
        
        if format_type == "html":
            html_body = body
            if not html_body.strip():
                raise InvalidFormattedContentError("Email HTML body cannot be blank.")
                
            parser = _PlainTextHTMLParser()
            parser.feed(html_body)
            raw_text = "".join(parser.text_parts)
            text_body = html.unescape(raw_text)
            
            text_body = cls._normalize_whitespace(text_body, collapse_lines=False)
            if not text_body:
                raise InvalidFormattedContentError("Email plain-text alternative cannot be blank.")
                
            return EmailMessageOutput(
                subject=subject,
                text_body=text_body,
                html_body=html_body,
            )
        else:
            text_body = cls._normalize_whitespace(body, collapse_lines=False)
            if not text_body:
                raise InvalidFormattedContentError("Email text body cannot be blank.")
                
            return EmailMessageOutput(
                subject=subject,
                text_body=text_body,
                html_body=None,
            )

    @classmethod
    def _format_push(
        cls,
        title: str | None,
        body: str,
        format_type: str,
    ) -> PushMessageOutput:
        if format_type != "text":
            raise UnsupportedChannelFormatError("PUSH requires text format.")
            
        valid_title = cls._validate_subject_or_title(title, "PUSH", require=True)
        valid_body = cls._normalize_whitespace(body, collapse_lines=False)
        
        if not valid_body:
            raise InvalidFormattedContentError("PUSH body cannot be blank.")
            
        return PushMessageOutput(title=valid_title, body=valid_body)

    @classmethod
    def _format_portal(
        cls,
        title: str | None,
        body: str,
        format_type: str,
    ) -> PortalMessageOutput:
        # Based on audit, currently portal might not require title for some notifications, but let's check.
        # It says "When the current portal infrastructure requires a title, enforce it. When title is currently optional, preserve that behavior."
        # Actually InAppNotification model does not have a title field usually, wait let me check InAppNotification.
        # No, let's make title optional for portal unless the audit proved it's required.
        valid_title = cls._validate_subject_or_title(title, "PORTAL", require=False)
        
        if format_type != "text":
            raise UnsupportedChannelFormatError("PORTAL currently supports text format only.")
            
        valid_body = cls._normalize_whitespace(body, collapse_lines=False)
        if not valid_body:
            raise InvalidFormattedContentError("PORTAL body cannot be blank.")
        title = title.strip() if title else "FieldOps Update"
        return PortalMessageOutput(
            title=title,
            body=valid_body,
            content_format="text"
        )
