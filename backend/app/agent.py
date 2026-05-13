from datetime import datetime
from uuid import uuid4

from .agents.constants import OPERATIONS_SYSTEM_PROMPT
from .agents.domain import DomainToolsMixin
from .agents.drafts import DraftGenerationMixin
from .agents.resolver import RequestResolverMixin
from .agents.responses import ResponseGenerationMixin
from .agents.tasks import TaskPlanningMixin, dedupe_tasks
from .agents.text import get_channel_display_name, summarize_order_items
from .gemini_client import gemini_client
from .models import (
    AgentAction,
    AgentResult,
    AssistantInterpretation,
    ChatMessage,
    OperationsState,
)


class OperationsAgent(
    DomainToolsMixin,
    RequestResolverMixin,
    DraftGenerationMixin,
    ResponseGenerationMixin,
    TaskPlanningMixin,
):
    def generate_customer_reply(
        self, message: str, state: OperationsState
    ) -> AgentResult:
        interpretation = self.interpret_message(message, state)
        context = self._resolve_request(message, state, interpretation=interpretation)
        actions = [*interpretation.actions]

        if context.get("intent") == "customer_update_draft":
            draft = self._build_contact_draft(message, context, state, interpretation)
            if draft:
                actions.append(
                    AgentAction(
                        id=str(uuid4()),
                        label=f"Created customer update draft for {draft.customerName}",
                        type="create_customer_update_draft",
                        payload={
                            "customerId": draft.customerId,
                            "orderId": draft.entities.orderId or "",
                            "channel": draft.recommendedChannel,
                        },
                    )
                )
                return AgentResult(
                    response=self._contact_draft_ready_reply(message, draft),
                    actions=actions,
                    contactDraft=draft,
                )

            return AgentResult(
                response=self._contact_draft_blocked_reply(message, context, state),
                actions=actions,
            )

        prompt = self._build_grounded_reply_prompt(message, context, state)
        response_text = gemini_client.generate_text(
            prompt,
            system_instruction=OPERATIONS_SYSTEM_PROMPT,
        )

        if response_text:
            return AgentResult(response=response_text, actions=actions)

        return AgentResult(
            response=self._fallback_reply(message, context, state),
            actions=actions,
        )

    def interpret_message(
        self,
        message: str,
        state: OperationsState,
        customer_email: str | None = None,
        customer_name: str | None = None,
    ) -> AssistantInterpretation:
        return self._interpret_message(
            message,
            state,
            customer_email=customer_email,
            customer_name=customer_name,
        )

    def generate_customer_email_draft(
        self,
        message: str,
        state: OperationsState,
        customer_email: str,
        customer_name: str,
        subject: str,
    ) -> tuple[str, str, AssistantInterpretation]:
        interpretation = self.interpret_message(
            message,
            state,
            customer_email=customer_email,
            customer_name=customer_name,
        )
        context = self._resolve_request(
            message,
            state,
            customer_email=customer_email,
            customer_name=customer_name,
            interpretation=interpretation,
        )
        prompt = self._build_customer_email_draft_prompt(
            message,
            subject,
            context,
            state,
            interpretation,
        )
        response_text = gemini_client.generate_text(
            prompt,
            system_instruction=OPERATIONS_SYSTEM_PROMPT,
        )
        body = (
            response_text.strip()
            if response_text
            else self._fallback_reply(message, context, state)
        )

        return self._reply_subject(subject), body, interpretation


def create_chat_message(text: str, role: str) -> ChatMessage:
    return ChatMessage(
        id=str(uuid4()),
        role=role,  # type: ignore[arg-type]
        text=text,
        timestamp=datetime.now().strftime("%H:%M"),
    )


agent = OperationsAgent()
