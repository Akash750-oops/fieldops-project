import pytest
from app.services.ai.FieldOpsAI.schemas.communication import (
    CommunicationDecision,
    SMSMessageOutput,
    EmailMessageOutput,
    PushMessageOutput,
    PortalMessageOutput,
    output_text_for_validation,
)
from app.services.ai.FieldOpsAI.services.message_output_formatter import MessageOutputFormatter

def test_message_output_formatter_text_normalization():
    # Test SMS (text normalization)
    out = MessageOutputFormatter.format(
        channel="SMS",
        rendered_title=None,
        rendered_body="  Hello \n \n World  ",
        template_format="text"
    )
    assert isinstance(out, SMSMessageOutput)
    assert out.text == "Hello World"

    # Test EMAIL HTML plain-text pairing
    out_email = MessageOutputFormatter.format(
        channel="EMAIL",
        rendered_title="Subject",
        rendered_body="<p>Hello <b>World</b></p>",
        template_format="html"
    )
    assert isinstance(out_email, EmailMessageOutput)
    assert out_email.subject == "Subject"
    assert out_email.html_body == "<p>Hello <b>World</b></p>"
    assert out_email.text_body == "Hello World"

def test_message_output_formatter_portal_title_fallback():
    # Test PORTAL title fallback
    out = MessageOutputFormatter.format(
        channel="PORTAL",
        rendered_title=None,
        rendered_body="Some body",
        template_format="text"
    )
    assert isinstance(out, PortalMessageOutput)
    assert out.title == "FieldOps Update"
    assert out.body == "Some body"

def test_communication_decision_compatibility():
    # Test that CommunicationDecision still provides legacy properties
    dec = CommunicationDecision(
        channel="EMAIL",
        output=EmailMessageOutput(subject="Subj", text_body="text", html_body="html"),
        tone="PROFESSIONAL",
        confidence=1.0
    )
    assert dec.subject == "Subj"
    assert dec.message == "html"
    assert dec.title is None

    dec_sms = CommunicationDecision(
        channel="SMS",
        output=SMSMessageOutput(text="hello"),
        tone="PROFESSIONAL",
        confidence=1.0
    )
    assert dec_sms.message == "hello"
    assert dec_sms.title is None
    assert dec_sms.subject is None

def test_output_text_for_validation():
    # Test SMS
    assert output_text_for_validation(SMSMessageOutput(text="msg")) == "msg"
    # Test EMAIL
    assert output_text_for_validation(EmailMessageOutput(subject="subj", text_body="txt")) == "subj\ntxt"
    # Test PUSH
    assert output_text_for_validation(PushMessageOutput(title="tit", body="bdy")) == "tit\nbdy"
    # Test PORTAL
    assert output_text_for_validation(PortalMessageOutput(title="tit", body="bdy")) == "tit\nbdy"
