#server/test_cart_task.py
import os
import django

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'ZuntoProject.settings')
django.setup()

from cart.tasks import detect_abandoned_carts, send_abandonment_reminders


def test_abandonment_detection():
    print("\n=== Testing Abandonment Detection ===")
    result = detect_abandoned_carts()
    print(f"Result: {result}")


def test_reminder_sending():
    print("\n=== Testing Reminder Sending ===")
    result = send_abandonment_reminders()
    print(f"Result: {result}")


if __name__ == "__main__":
    test_abandonment_detection()
    test_reminder_sending()
    print("\n=== All Tests Completed ===\n")
