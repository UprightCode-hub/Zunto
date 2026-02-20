#server/chat/security.py
import re
from urllib.parse import urlparse

URL_PATTERN = re.compile(r"https?://[^\s<>'\"]+", re.IGNORECASE)
SUSPICIOUS_LINK_TERMS = (
    'pay outside',
    'payment link',
    'verify wallet',
    'reset your password',
    'crypto giveaway',
    'urgent payment',
)


def extract_urls(text):
    if not text:
        return []
    return [match.rstrip('.,;:!?)') for match in URL_PATTERN.findall(text)]


def find_blocked_url(urls, blocked_domains):
    blocked = {domain.lower().strip() for domain in blocked_domains if domain}
    for url in urls:
        host = (urlparse(url).hostname or '').lower()
        if not host:
            continue
        for domain in blocked:
            if host == domain or host.endswith(f'.{domain}'):
                return url
    return None


def has_suspicious_link_phrase(text):
    normalized = (text or '').lower()
    return any(term in normalized for term in SUSPICIOUS_LINK_TERMS)
