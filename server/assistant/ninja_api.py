"""Ninja API routes for assistant module (parallel to DRF endpoints)."""

from typing import Optional
import uuid
from ninja import Router, Schema

from assistant.views import _resolve_assistant_lane, _handle_ephemeral_chat
from assistant.processors.conversation_manager import ConversationManager

router = Router(tags=["assistant"])


class ChatIn(Schema):
    message: str
    session_id: Optional[str] = None
    assistant_lane: Optional[str] = "inbox"


@router.post("/chat")
def ninja_chat(request, payload: ChatIn):
    lane = _resolve_assistant_lane({'assistant_lane': payload.assistant_lane})
    session_id = payload.session_id or str(uuid.uuid4())

    if not request.user.is_authenticated:
        result = _handle_ephemeral_chat(message=payload.message, lane=lane)
        result['session_id'] = session_id
        return result

    manager = ConversationManager(session_id=session_id, user_id=request.user.id, assistant_lane=lane)
    reply = manager.process_message(payload.message)
    summary = manager.get_conversation_summary()

    return {
        'reply': reply,
        'session_id': session_id,
        'state': manager.get_current_state(),
        'confidence': summary.get('satisfaction_score', 0.5),
        'metadata': {
            'assistant_lane': lane,
            'persistence': 'persistent',
            'conversation_title': manager.session.conversation_title,
            'message_count': summary.get('message_count', 0),
        }
    }
