#server/assistant/ninja_api.py
"""Ninja API routes for assistant module (parallel to DRF endpoints)."""

from typing import Optional
import uuid
from ninja import Router, Schema

from assistant.views import _resolve_assistant_mode, _handle_ephemeral_chat
from assistant.utils.assistant_modes import resolve_legacy_lane
from assistant.processors.conversation_manager import ConversationManager

router = Router(tags=["assistant"])


class ChatIn(Schema):
    message: str
    session_id: Optional[str] = None
    assistant_mode: Optional[str] = "inbox_general"
    assistant_lane: Optional[str] = "inbox"


@router.post("/chat")
def ninja_chat(request, payload: ChatIn):
    assistant_mode = _resolve_assistant_mode({
        'assistant_mode': payload.assistant_mode,
        'assistant_lane': payload.assistant_lane,
    })
    lane = resolve_legacy_lane(assistant_mode)
    session_id = payload.session_id or str(uuid.uuid4())

    if not request.user.is_authenticated:
        result = _handle_ephemeral_chat(message=payload.message, assistant_mode=assistant_mode, lane=lane)
        result['session_id'] = session_id
        return result

    manager = ConversationManager(session_id=session_id, user_id=request.user.id, assistant_mode=assistant_mode)
    reply = manager.process_message(payload.message)
    summary = manager.get_conversation_summary()

    return {
        'reply': reply,
        'session_id': session_id,
        'state': manager.get_current_state(),
        'confidence': summary.get('satisfaction_score', 0.5),
        'metadata': {
            'assistant_mode': assistant_mode,
            'assistant_lane': lane,
            'persistence': 'persistent',
            'conversation_title': manager.session.conversation_title,
            'message_count': summary.get('message_count', 0),
        }
    }
