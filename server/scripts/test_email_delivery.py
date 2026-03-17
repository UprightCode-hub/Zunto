#!/usr/bin/env python3
"""CLI helper to test outbound email delivery from the backend."""
import argparse
import os
import sys


def main():
    parser = argparse.ArgumentParser(description='Send a backend test verification email.')
    parser.add_argument('--to', required=True, help='Recipient email address')
    parser.add_argument('--name', default='Test User', help='Recipient display name')
    parser.add_argument('--code', default='123456', help='Verification code to include')
    parser.add_argument('--settings', default='ZuntoProject.settings', help='Django settings module')
    args = parser.parse_args()

    os.environ.setdefault('DJANGO_SETTINGS_MODULE', args.settings)

    try:
        import django
        django.setup()
    except Exception as exc:
        print(f'Failed to initialize Django: {exc}')
        return 1

    from notifications.email_service import EmailService

    sent = EmailService.send_verification_email_to_recipient(
        recipient_email=args.to,
        recipient_name=args.name,
        code=args.code,
    )

    if sent:
        print(f'Email sent successfully to {args.to}')
        return 0

    print(f'Email failed for {args.to}')
    return 2


if __name__ == '__main__':
    sys.exit(main())
