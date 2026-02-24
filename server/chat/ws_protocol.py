import json
from datetime import datetime, timezone
from uuid import uuid4

PROTOCOL_VERSION = '1.0'
MAX_WS_PAYLOAD_BYTES = 64 * 1024

ALLOWED_EVENT_TYPES = {
    'chat.message.send',
    'chat.message.ack',
    'chat.message.created',
    'chat.message.updated',
    'chat.message.deleted',
    'chat.history.synced',
    'chat.error',
    'chat.warning',
    'chat.ping',
    'chat.pong',
    'chat.replay.request',
    'chat.replay.chunk',
    'chat.replay.complete',
    'chat.join',
    'chat.leave',
    'chat.typing.start',
    'chat.typing.stop',
    'chat.presence.online',
    'chat.presence.offline',
    'chat.presence.snapshot',
    'chat.read.updated',
    'chat.read.snapshot',
}

LEGACY_EVENT_TYPE_MAP = {
    'join': 'chat.join',
    'leave': 'chat.leave',
    'ping': 'chat.ping',
    'pong': 'chat.pong',
    'heartbeat': 'chat.ping',
    'chat_message': 'chat.message.created',
    'message': 'chat.message.created',
    'message_deleted': 'chat.message.deleted',
    'error': 'chat.error',
    'ack': 'chat.message.ack',
    'typing': 'chat.typing.start',
    'user_status': 'chat.presence.online',
    'read_receipt': 'chat.read.updated',
}


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _string_or_none(value):
    if value is None:
        return None
    return str(value)


def build_envelope(
    *,
    event_type,
    conversation_id,
    payload,
    actor_id=None,
    correlation_id=None,
    idempotency_key=None,
    event_id=None,
    seq=None,
    occurred_at=None,
    meta=None,
    protocol_version=PROTOCOL_VERSION,
):
    envelope = {
        'v': str(protocol_version),
        'type': event_type,
        'event_id': _string_or_none(event_id) or str(uuid4()),
        'conversation_id': _string_or_none(conversation_id),
        'actor_id': _string_or_none(actor_id),
        'occurred_at': occurred_at or now_iso(),
        'seq': seq,
        'correlation_id': _string_or_none(correlation_id),
        'idempotency_key': _string_or_none(idempotency_key),
        'payload': payload if isinstance(payload, dict) else {},
    }
    if meta:
        envelope['meta'] = meta
    return envelope


def parse_ws_message(raw_text):
    if raw_text is None:
        return None, 'empty_payload'

    if len(raw_text.encode('utf-8')) > MAX_WS_PAYLOAD_BYTES:
        return None, 'payload_too_large'

    try:
        data = json.loads(raw_text)
    except json.JSONDecodeError:
        return None, 'invalid_json'

    if not isinstance(data, dict):
        return None, 'payload_not_object'

    normalized, normalization_meta = normalize_legacy_event(data)
    valid, reason = validate_envelope(normalized)
    if not valid:
        return None, reason

    if normalized['type'] not in ALLOWED_EVENT_TYPES:
        return None, f"unknown_event_type:{normalized['type']}"

    if normalized['v'] != PROTOCOL_VERSION:
        return None, f"unsupported_protocol_version:{normalized['v']}"

    if normalization_meta:
        normalized.setdefault('meta', {})
        normalized['meta']['normalized_from'] = normalization_meta

    return normalized, None


def normalize_legacy_event(data):
    if {'v', 'type', 'event_id', 'conversation_id', 'payload'}.issubset(set(data.keys())):
        return data, None

    legacy_type = data.get('type')
    mapped_type = LEGACY_EVENT_TYPE_MAP.get(legacy_type)
    if not mapped_type:
        return data, None

    payload = data.get('payload') if isinstance(data.get('payload'), dict) else {}

    if mapped_type in {'chat.join', 'chat.leave'}:
        payload = {'conversation_id': data.get('conversation_id')}
    elif mapped_type == 'chat.ping':
        payload = {'timestamp': data.get('timestamp')}
    elif mapped_type == 'chat.typing.start':
        payload = {'state': 'start' if data.get('is_typing', True) else 'stop'}
        if payload['state'] == 'stop':
            mapped_type = 'chat.typing.stop'
    elif mapped_type == 'chat.presence.online':
        status = data.get('status')
        actor_id = data.get('user_id') or data.get('actor_id')
        payload = {'actor_id': actor_id, 'status': status or 'online'}
        if status == 'offline':
            mapped_type = 'chat.presence.offline'
    elif mapped_type == 'chat.read.updated':
        payload = {
            'actor_id': data.get('read_by') or data.get('actor_id') or data.get('user_id'),
            'last_read_message_id': data.get('last_read_message_id'),
            'message_ids': data.get('message_ids') if isinstance(data.get('message_ids'), list) else None,
            'read_at': data.get('read_at'),
        }

    normalized = build_envelope(
        event_type=mapped_type,
        conversation_id=data.get('conversation_id'),
        payload=payload,
        actor_id=data.get('actor_id') or data.get('user_id'),
        correlation_id=data.get('correlation_id'),
        idempotency_key=data.get('idempotency_key'),
        event_id=data.get('event_id'),
        meta={'legacy_type': legacy_type},
        protocol_version=data.get('v') or data.get('protocol_version') or PROTOCOL_VERSION,
    )
    return normalized, legacy_type


def validate_envelope(data):
    required = ('v', 'type', 'event_id', 'conversation_id', 'payload')
    for key in required:
        if key not in data:
            return False, f'missing_{key}'

    if not isinstance(data.get('v'), str):
        return False, 'invalid_v'
    if not isinstance(data.get('type'), str):
        return False, 'invalid_type'
    if not isinstance(data.get('event_id'), str):
        return False, 'invalid_event_id'
    if not isinstance(data.get('conversation_id'), str):
        return False, 'invalid_conversation_id'
    if not isinstance(data.get('payload'), dict):
        return False, 'invalid_payload'

    if data.get('actor_id') is not None and not isinstance(data.get('actor_id'), str):
        return False, 'invalid_actor_id'
    if data.get('correlation_id') is not None and not isinstance(data.get('correlation_id'), str):
        return False, 'invalid_correlation_id'
    if data.get('idempotency_key') is not None and not isinstance(data.get('idempotency_key'), str):
        return False, 'invalid_idempotency_key'

    return True, None
