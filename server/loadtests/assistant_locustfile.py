"""Locust load test profile for assistant/chat APIs (10K readiness baseline)."""

from locust import HttpUser, task, between
import uuid


class AssistantUser(HttpUser):
    wait_time = between(0.2, 1.5)

    def on_start(self):
        self.session_id = str(uuid.uuid4())

    @task(8)
    def assistant_chat(self):
        self.client.post(
            "/assistant/api/chat/",
            json={
                "message": "Show me products under 100 dollars",
                "session_id": self.session_id,
                "assistant_lane": "inbox",
            },
        )

    @task(2)
    def dispute_report(self):
        self.client.post(
            "/assistant/api/report/",
            json={
                "report_type": "dispute",
                "description": "Load test dispute creation",
            },
        )


class ChatBurstUser(HttpUser):
    wait_time = between(0.05, 0.5)

    @task
    def message_burst(self):
        # Requires existing conversation id for realistic runs
        self.client.post(
            "/chat/messages/",
            json={
                "conversation_id": "00000000-0000-0000-0000-000000000000",
                "content": "load-test message",
            },
        )
