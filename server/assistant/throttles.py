from rest_framework.throttling import AnonRateThrottle, UserRateThrottle


class AssistantChatAnonThrottle(AnonRateThrottle):
    scope = 'assistant_chat_anon'


class AssistantChatUserThrottle(UserRateThrottle):
    scope = 'assistant_chat_user'


class DisputeReportAnonThrottle(AnonRateThrottle):
    scope = 'assistant_report_anon'


class DisputeReportUserThrottle(UserRateThrottle):
    scope = 'assistant_report_user'


class DisputeEvidenceUploadUserThrottle(UserRateThrottle):
    scope = 'assistant_evidence_upload_user'
