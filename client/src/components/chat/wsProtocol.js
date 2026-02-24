const PROTOCOL_VERSION = '1.0';

const ALLOWED_EVENT_TYPES = new Set([
  'chat.message.ack',
  'chat.message.created',
  'chat.message.updated',
  'chat.message.deleted',
  'chat.history.synced',
  'chat.error',
  'chat.warning',
  'chat.ping',
  'chat.pong',
  'chat.typing.start',
  'chat.typing.stop',
  'chat.presence.online',
  'chat.presence.offline',
  'chat.presence.snapshot',
  'chat.read.updated',
  'chat.read.snapshot',
]);

const LEGACY_TYPE_MAP = {
  message: 'chat.message.created',
  chat_message: 'chat.message.created',
  message_deleted: 'chat.message.deleted',
  error: 'chat.error',
  ack: 'chat.message.ack',
  ping: 'chat.ping',
  pong: 'chat.pong',
  typing: 'chat.typing.start',
  user_status: 'chat.presence.online',
  read_receipt: 'chat.read.updated',
};

const isObject = (value) => value && typeof value === 'object' && !Array.isArray(value);

const buildEnvelopeFromLegacy = (raw) => {
  const mappedType = LEGACY_TYPE_MAP[raw?.type];
  if (!mappedType) {
    return null;
  }

  let payload = isObject(raw.payload) ? { ...raw.payload } : {};
  if (mappedType === 'chat.message.created') {
    payload.message = raw.message || payload.message || null;
  }
  if (mappedType === 'chat.message.deleted') {
    payload.message_id = raw.message_id || payload.message_id || null;
  }
  if (mappedType === 'chat.error') {
    payload.message = raw.message || payload.message || 'Unknown websocket error';
  }
  if (mappedType === 'chat.read.updated') {
    payload.actor_id = raw.read_by || raw.actor_id || raw.user_id || payload.actor_id || null;
    payload.message_ids = Array.isArray(raw.message_ids) ? raw.message_ids : (Array.isArray(payload.message_ids) ? payload.message_ids : null);
    payload.last_read_message_id = raw.last_read_message_id || payload.last_read_message_id || (Array.isArray(payload.message_ids) ? payload.message_ids[payload.message_ids.length - 1] : null);
    payload.read_at = raw.read_at || payload.read_at || new Date().toISOString();
  }

  return {
    v: raw.v || raw.protocol_version || PROTOCOL_VERSION,
    type: mappedType,
    event_id: raw.event_id || `${Date.now()}-${Math.random().toString(16).slice(2)}`,
    conversation_id: String(raw.conversation_id || payload?.message?.conversation || ''),
    actor_id: raw.actor_id || raw.user_id || null,
    occurred_at: raw.occurred_at || new Date().toISOString(),
    seq: Number.isFinite(raw.seq) ? raw.seq : null,
    correlation_id: raw.correlation_id || null,
    idempotency_key: raw.idempotency_key || null,
    payload,
    meta: {
      normalized_from: raw.type,
    },
  };
};

const validateEnvelope = (event) => {
  if (!isObject(event)) return { valid: false, reason: 'payload_not_object' };
  const required = ['v', 'type', 'event_id', 'conversation_id', 'payload'];
  for (const key of required) {
    if (!(key in event)) return { valid: false, reason: `missing_${key}` };
  }

  if (typeof event.v !== 'string') return { valid: false, reason: 'invalid_v' };
  if (event.v !== PROTOCOL_VERSION) return { valid: false, reason: `unsupported_v_${event.v}` };
  if (typeof event.type !== 'string') return { valid: false, reason: 'invalid_type' };
  if (!ALLOWED_EVENT_TYPES.has(event.type)) return { valid: false, reason: `unknown_type_${event.type}` };
  if (typeof event.event_id !== 'string' || event.event_id.length === 0) return { valid: false, reason: 'invalid_event_id' };
  if (typeof event.conversation_id !== 'string' || event.conversation_id.length === 0) return { valid: false, reason: 'invalid_conversation_id' };
  if (!isObject(event.payload)) return { valid: false, reason: 'invalid_payload' };

  return { valid: true, reason: null };
};

export const parseAndNormalizeWsEvent = (rawText) => {
  let parsed;
  try {
    parsed = JSON.parse(rawText);
  } catch {
    return { ok: false, reason: 'invalid_json' };
  }

  const candidate = buildEnvelopeFromLegacy(parsed) || parsed;
  const validation = validateEnvelope(candidate);
  if (!validation.valid) {
    return { ok: false, reason: validation.reason, event: candidate };
  }

  return { ok: true, event: candidate };
};

export const dispatchInboxWsEvent = ({ event, handlers, onUnhandled }) => {
  const handler = handlers[event.type];
  if (!handler) {
    onUnhandled?.(event, `missing_handler_${event.type}`);
    return;
  }
  handler(event);
};

export const getWsProtocolVersion = () => PROTOCOL_VERSION;


export const buildClientWsEnvelope = ({ type, conversationId, actorId, payload = {}, correlationId = null, idempotencyKey = null }) => ({
  v: PROTOCOL_VERSION,
  type,
  event_id: `client-${Date.now()}-${Math.random().toString(16).slice(2)}`,
  conversation_id: String(conversationId),
  actor_id: actorId ? String(actorId) : null,
  occurred_at: new Date().toISOString(),
  seq: null,
  correlation_id: correlationId,
  idempotency_key: idempotencyKey,
  payload,
});
