import hashlib
import imaplib
import os
import smtplib
from dataclasses import dataclass
from datetime import datetime
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from email.utils import parseaddr
from uuid import uuid4

from fastapi import HTTPException

from .agent import agent
from .commerce import get_commerce_connector
from .models import (
    AgentAction,
    AssistantDraft,
    ConnectorHealth,
    CustomerMessage,
    CustomerThread,
    DraftApprovalRequest,
    DraftApprovalResponse,
    InboxSyncResponse,
    OperationsState,
)


@dataclass
class InboundEmail:
    provider_message_id: str
    from_name: str
    from_email: str
    to_email: str
    subject: str
    body: str
    received_at: str


_threads: dict[str, CustomerThread] = {}
_drafts: dict[str, AssistantDraft] = {}
_seen_provider_message_ids: set[str] = set()
_last_imap_error: str | None = None
_last_smtp_error: str | None = None


def sync_inbox(state: OperationsState) -> InboxSyncResponse:
    messages = _fetch_imap_messages() if _imap_configured() else _demo_messages()
    synced = 0

    for message in messages:
        if ingest_inbound_email(message, state):
            synced += 1

    return InboxSyncResponse(
        syncedMessages=synced,
        threads=list_threads(),
        connectorHealth=[*email_connector_health(), get_commerce_connector().health()],
    )


def ingest_inbound_email(
    message: InboundEmail,
    state: OperationsState,
) -> CustomerThread | None:
    if message.provider_message_id in _seen_provider_message_ids:
        return None

    _seen_provider_message_ids.add(message.provider_message_id)
    customer = agent.lookup_customer(
        state,
        email=message.from_email,
        name=message.from_name,
    )
    customer_name = customer.name if customer else message.from_name or message.from_email
    thread_id = _thread_id(message.from_email, message.subject)

    thread = _threads.get(thread_id)
    if thread is None:
        thread = CustomerThread(
            id=thread_id,
            subject=_clean_subject(message.subject),
            customerId=customer.id if customer else None,
            customerName=customer_name,
            customerEmail=message.from_email,
            status="open",
            unread=True,
            lastMessageAt=message.received_at,
        )
        _threads[thread_id] = thread

    reply_subject, draft_body, interpretation = agent.generate_customer_email_draft(
        message.body,
        state,
        customer_email=message.from_email,
        customer_name=customer_name,
        subject=message.subject,
    )
    inbound = CustomerMessage(
        id=str(uuid4()),
        threadId=thread.id,
        providerMessageId=message.provider_message_id,
        direction="inbound",
        fromName=customer_name,
        fromEmail=message.from_email,
        toEmail=message.to_email,
        subject=message.subject,
        body=message.body,
        receivedAt=message.received_at,
        unread=True,
        intent=interpretation.intent,
        entities=interpretation.entities,
    )
    draft = AssistantDraft(
        id=str(uuid4()),
        threadId=thread.id,
        messageId=inbound.id,
        subject=reply_subject,
        body=draft_body,
        toEmail=message.from_email,
        status="pending_review",
        intent=interpretation.intent,
        entities=interpretation.entities,
        confidence=interpretation.confidence,
        requiredReviewReason=(
            interpretation.requiredReviewReason
            or "Human approval is required before any customer email is sent."
        ),
        createdAt=_now(),
    )

    thread.customerId = customer.id if customer else thread.customerId
    thread.customerName = customer_name
    thread.customerEmail = message.from_email
    thread.unread = True
    thread.status = "drafted"
    thread.lastMessageAt = message.received_at
    thread.messages.append(inbound)
    thread.drafts.append(draft)
    _drafts[draft.id] = draft

    return thread


def list_threads() -> list[CustomerThread]:
    return sorted(
        _threads.values(),
        key=lambda thread: thread.lastMessageAt,
        reverse=True,
    )


def get_thread(thread_id: str) -> CustomerThread:
    thread = _threads.get(thread_id)
    if thread is None:
        raise HTTPException(status_code=404, detail="Thread not found")
    return thread


def approve_draft(
    draft_id: str,
    request: DraftApprovalRequest,
) -> DraftApprovalResponse:
    draft = _drafts.get(draft_id)
    if draft is None:
        raise HTTPException(status_code=404, detail="Draft not found")
    if draft.status != "pending_review":
        raise HTTPException(status_code=409, detail="Draft already processed")

    thread = get_thread(draft.threadId)
    now = _now()

    if request.subject:
        draft.subject = request.subject
    if request.body:
        draft.body = request.body

    draft.status = "approved"
    draft.approvedAt = now
    send_reference = _send_smtp(draft)
    draft.status = "sent" if send_reference else "failed"
    draft.sentAt = _now() if send_reference else None
    draft.sendRecorded = bool(send_reference)
    thread.status = "sent" if send_reference else "drafted"
    thread.unread = False if send_reference else thread.unread

    if send_reference:
        thread.messages.append(
            CustomerMessage(
                id=str(uuid4()),
                threadId=thread.id,
                providerMessageId=send_reference,
                direction="outbound",
                fromName="çırak Ops",
                fromEmail=_smtp_from_email(),
                toEmail=draft.toEmail,
                subject=draft.subject,
                body=draft.body,
                receivedAt=draft.sentAt or _now(),
                unread=False,
                intent=draft.intent,
                entities=draft.entities,
            )
        )
        thread.lastMessageAt = draft.sentAt or now

    action = AgentAction(
        id=str(uuid4()),
        label=(
            f"Approved and recorded email send to {draft.toEmail}"
            if send_reference
            else f"Draft approval failed for {draft.toEmail}"
        ),
        type="send_email" if send_reference else "approve_draft",
        payload={
            "draftId": draft.id,
            "threadId": thread.id,
            "toEmail": draft.toEmail,
            "sent": bool(send_reference),
        },
    )

    return DraftApprovalResponse(thread=thread, draft=draft, action=action)


def email_connector_health() -> list[ConnectorHealth]:
    return [
        ConnectorHealth(
            name="IMAP inbox",
            type="email_inbound",
            status="ok" if _imap_configured() and not _last_imap_error else (
                "error" if _last_imap_error else "disabled"
            ),
            lastChecked=_now(),
            capabilities=["inbox_sync"] if _imap_configured() else [],
            message=_last_imap_error
            or (
                "Set IMAP_HOST, IMAP_USERNAME, and IMAP_PASSWORD to sync real email."
                if not _imap_configured()
                else None
            ),
        ),
        ConnectorHealth(
            name="SMTP outbound",
            type="email_outbound",
            status="ok" if _smtp_configured() and not _last_smtp_error else (
                "error" if _last_smtp_error else "disabled"
            ),
            lastChecked=_now(),
            capabilities=["send_on_approval"] if _smtp_configured() else ["dry_run_record"],
            message=_last_smtp_error
            or (
                "Set SMTP_HOST and SMTP_FROM_EMAIL to send real approved drafts."
                if not _smtp_configured()
                else None
            ),
        ),
    ]


def reset_inbox_state() -> None:
    global _last_imap_error, _last_smtp_error
    _threads.clear()
    _drafts.clear()
    _seen_provider_message_ids.clear()
    _last_imap_error = None
    _last_smtp_error = None


def _fetch_imap_messages() -> list[InboundEmail]:
    global _last_imap_error
    host = os.getenv("IMAP_HOST", "")
    port = int(os.getenv("IMAP_PORT", "993"))
    username = os.getenv("IMAP_USERNAME", "")
    password = os.getenv("IMAP_PASSWORD", "")
    mailbox = os.getenv("IMAP_MAILBOX", "INBOX")
    use_ssl = os.getenv("IMAP_USE_SSL", "true").lower() != "false"
    limit = int(os.getenv("EMAIL_SYNC_LIMIT", "25"))

    try:
        client = imaplib.IMAP4_SSL(host, port) if use_ssl else imaplib.IMAP4(host, port)
        client.login(username, password)
        client.select(mailbox)
        _, data = client.search(None, "ALL")
        message_ids = (data[0] or b"").split()[-limit:]
        messages: list[InboundEmail] = []

        for message_id in message_ids:
            _, fetched = client.fetch(message_id, "(RFC822)")
            raw = fetched[0][1] if fetched and isinstance(fetched[0], tuple) else None
            if raw:
                messages.append(_parse_email(raw, fallback_id=message_id.decode("utf-8")))

        client.logout()
        _last_imap_error = None
        return messages
    except Exception as exc:
        _last_imap_error = str(exc)
        return []


def _parse_email(raw: bytes, fallback_id: str) -> InboundEmail:
    parsed = BytesParser(policy=policy.default).parsebytes(raw)
    from_name, from_email = parseaddr(parsed.get("From", ""))
    _, to_email = parseaddr(parsed.get("To", ""))
    provider_id = parsed.get("Message-ID") or fallback_id

    return InboundEmail(
        provider_message_id=provider_id.strip(),
        from_name=from_name,
        from_email=from_email,
        to_email=to_email or _smtp_from_email(),
        subject=parsed.get("Subject", "(no subject)"),
        body=_extract_body(parsed),
        received_at=_now(),
    )


def _extract_body(message: EmailMessage) -> str:
    if message.is_multipart():
        for part in message.walk():
            if part.get_content_type() == "text/plain":
                return (part.get_content() or "").strip()
        return ""

    return (message.get_content() or "").strip()


def _send_smtp(draft: AssistantDraft) -> str | None:
    global _last_smtp_error

    if not _smtp_configured():
        _last_smtp_error = None
        return f"dry-run:{draft.id}"

    email_message = EmailMessage()
    email_message["Subject"] = draft.subject
    email_message["From"] = _smtp_from_email()
    email_message["To"] = draft.toEmail
    email_message.set_content(draft.body)

    host = os.getenv("SMTP_HOST", "")
    port = int(os.getenv("SMTP_PORT", "587"))
    username = os.getenv("SMTP_USERNAME")
    password = os.getenv("SMTP_PASSWORD")
    use_tls = os.getenv("SMTP_USE_TLS", "true").lower() != "false"

    try:
        with smtplib.SMTP(host, port, timeout=10) as client:
            if use_tls:
                client.starttls()
            if username and password:
                client.login(username, password)
            client.send_message(email_message)
        _last_smtp_error = None
        return f"smtp:{uuid4()}"
    except Exception as exc:
        _last_smtp_error = str(exc)
        return None


def _demo_messages() -> list[InboundEmail]:
    return [
        InboundEmail(
            provider_message_id="demo-email-128",
            from_name="Mina Yılmaz",
            from_email="mina.yilmaz@example.com",
            to_email=_smtp_from_email(),
            subject="Sipariş 128 teslimat",
            body="Merhaba, sipariş 128 ne zaman teslim edilir?",
            received_at="2026-05-12T09:21:00+03:00",
        ),
        InboundEmail(
            provider_message_id="demo-email-stock-dara",
            from_name="Dara Boutique",
            from_email="hello@daraboutique.example",
            to_email=_smtp_from_email(),
            subject="Cotton towel stock",
            body="Hi, do you have enough cotton towels in stock for a reorder this week?",
            received_at="2026-05-12T09:37:00+03:00",
        ),
        InboundEmail(
            provider_message_id="demo-email-vague-order",
            from_name="Arda Market",
            from_email="orders@ardamarket.example",
            to_email=_smtp_from_email(),
            subject="Order status",
            body="Where is my order? We need an update before the afternoon delivery window.",
            received_at="2026-05-12T09:46:00+03:00",
        ),
    ]


def _thread_id(from_email: str, subject: str) -> str:
    key = f"{from_email.lower()}:{_clean_subject(subject).lower()}"
    return f"thread-{hashlib.sha1(key.encode('utf-8')).hexdigest()[:12]}"


def _clean_subject(subject: str) -> str:
    cleaned = subject.strip()
    while cleaned.lower().startswith("re:"):
        cleaned = cleaned[3:].strip()
    return cleaned or "(no subject)"


def _imap_configured() -> bool:
    return all(
        [
            os.getenv("IMAP_HOST"),
            os.getenv("IMAP_USERNAME"),
            os.getenv("IMAP_PASSWORD"),
        ]
    )


def _smtp_configured() -> bool:
    return bool(os.getenv("SMTP_HOST") and os.getenv("SMTP_FROM_EMAIL"))


def _smtp_from_email() -> str:
    return os.getenv("SMTP_FROM_EMAIL", "support@cirak.local")


def _now() -> str:
    return datetime.now().isoformat(timespec="seconds")
