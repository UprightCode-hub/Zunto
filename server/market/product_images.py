from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from io import BytesIO
from typing import Iterable
from urllib.parse import urljoin, urlparse

import requests
from django.conf import settings
from django.core.files.base import ContentFile
from django.utils.text import slugify
from PIL import Image, ImageDraw, ImageFont, ImageOps, UnidentifiedImageError

from core.storage_backends import PublicMediaStorage

logger = logging.getLogger(__name__)

IRRELEVANT_QUERY_WORDS = {
    'affordable',
    'best',
    'buy',
    'cheap',
    'deal',
    'discount',
    'for',
    'free',
    'hot',
    'latest',
    'new',
    'offer',
    'official',
    'online',
    'original',
    'promo',
    'sale',
    'seller',
    'shipping',
    'shop',
    'store',
    'top',
    'wholesale',
}

WIKIMEDIA_API_URL = 'https://commons.wikimedia.org/w/api.php'
ALLOWED_IMAGE_TYPES = {'image/jpeg', 'image/png', 'image/webp'}
MAX_DOWNLOAD_BYTES = 5 * 1024 * 1024
PRODUCT_IMAGE_DIR = 'product_locked_images'


@dataclass(frozen=True)
class ImageCandidate:
    url: str
    source: str
    title: str = ''
    description: str = ''
    mime_type: str = ''


def build_product_image_query(product, min_tokens: int = 3, max_tokens: int = 6) -> str:
    tokens = _meaningful_tokens(getattr(product, 'title', '') or '')

    for value in (
        getattr(product, 'brand', '') or '',
        getattr(getattr(product, 'product_family', None), 'name', '') or '',
        getattr(getattr(product, 'category', None), 'name', '') or '',
    ):
        if len(tokens) >= min_tokens:
            break
        for token in _meaningful_tokens(value):
            if token not in tokens:
                tokens.append(token)
            if len(tokens) >= min_tokens:
                break

    if not tokens:
        tokens = ['product']

    return ' '.join(tokens[:max_tokens])


def ensure_product_image_locked(product) -> str:
    if product.image_url_locked:
        return product.image_url_locked
    if getattr(settings, 'TESTING', False):
        return ''

    query = build_product_image_query(product)
    candidates = fetch_image_candidates(query, limit=5)
    selected = select_best_candidate(query, candidates)

    if selected is not None:
        try:
            stored_url = store_candidate_image(product, selected)
            source = _source_label(selected, query)
            _lock_product_image(product, stored_url, source)
            return stored_url
        except Exception:
            logger.exception(
                "Failed to store selected product image for product_id=%s",
                product.pk,
            )

    stored_url = store_placeholder_image(product, query)
    _lock_product_image(product, stored_url, f'generated_placeholder:{query}'[:255])
    return stored_url


def fetch_image_candidates(query: str, limit: int = 5) -> list[ImageCandidate]:
    try:
        response = requests.get(
            WIKIMEDIA_API_URL,
            params={
                'action': 'query',
                'format': 'json',
                'generator': 'search',
                'gsrnamespace': 6,
                'gsrsearch': query,
                'gsrlimit': max(1, min(limit, 5)),
                'prop': 'imageinfo',
                'iiprop': 'url|mime|extmetadata',
                'iiurlwidth': 1200,
            },
            headers={'User-Agent': 'ZuntoProductImageLocker/1.0'},
            timeout=(5, 10),
        )
        response.raise_for_status()
    except requests.RequestException:
        logger.exception("Product image candidate search failed for query=%r", query)
        return []

    pages = (response.json().get('query') or {}).get('pages') or {}
    candidates = []
    for page in sorted(pages.values(), key=lambda item: item.get('index', 0)):
        image_info = (page.get('imageinfo') or [{}])[0]
        mime_type = image_info.get('mime') or ''
        image_url = image_info.get('thumburl') or image_info.get('url') or ''
        if not image_url or mime_type not in ALLOWED_IMAGE_TYPES:
            continue
        metadata = image_info.get('extmetadata') or {}
        candidates.append(
            ImageCandidate(
                url=image_url,
                source='wikimedia_commons',
                title=str(page.get('title') or ''),
                description=_metadata_value(metadata, 'ImageDescription'),
                mime_type=mime_type,
            )
        )
    return candidates[:limit]


def select_best_candidate(query: str, candidates: Iterable[ImageCandidate]) -> ImageCandidate | None:
    query_tokens = set(_meaningful_tokens(query))
    ranked = []
    for index, candidate in enumerate(candidates):
        text_tokens = set(_meaningful_tokens(f'{candidate.title} {candidate.description}'))
        overlap_score = len(query_tokens & text_tokens)
        ranked.append((overlap_score, -index, candidate))
    if not ranked:
        return None
    ranked.sort(reverse=True)
    return ranked[0][2]


def store_candidate_image(product, candidate: ImageCandidate) -> str:
    response = requests.get(
        candidate.url,
        headers={'User-Agent': 'ZuntoProductImageLocker/1.0'},
        stream=True,
        timeout=(5, 15),
    )
    response.raise_for_status()

    content_type = (response.headers.get('content-type') or '').split(';', 1)[0].lower()
    if content_type not in ALLOWED_IMAGE_TYPES:
        raise ValueError(f'Unsupported image content type: {content_type}')

    content = BytesIO()
    total = 0
    for chunk in response.iter_content(chunk_size=64 * 1024):
        if not chunk:
            continue
        total += len(chunk)
        if total > MAX_DOWNLOAD_BYTES:
            raise ValueError('Product image exceeds maximum download size')
        content.write(chunk)

    encoded_image = _encode_image_as_jpeg(content.getvalue())
    filename = _storage_filename(product, 'jpg')
    return _save_public_file(filename, encoded_image)


def store_placeholder_image(product, query: str) -> str:
    image = Image.new('RGB', (900, 900), '#f4f6f8')
    draw = ImageDraw.Draw(image)
    draw.rectangle((0, 0, 899, 899), outline='#c8d1dc', width=6)
    draw.rectangle((80, 300, 820, 600), fill='#ffffff', outline='#d8dee8', width=3)

    title = ' '.join((query or 'product').split()[:6]).title()
    font = ImageFont.load_default()
    lines = _wrap_text(title, max_chars=24)[:3]
    line_height = 34
    y = 430 - ((len(lines) - 1) * line_height // 2)
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        x = (900 - (bbox[2] - bbox[0])) // 2
        draw.text((x, y), line, fill='#1f2937', font=font)
        y += line_height

    output = BytesIO()
    image.save(output, format='JPEG', quality=88, optimize=True)
    filename = _storage_filename(product, 'jpg')
    return _save_public_file(filename, output.getvalue())


def _meaningful_tokens(value: str) -> list[str]:
    tokens = []
    seen = set()
    for token in re.findall(r'[a-zA-Z0-9][a-zA-Z0-9._+-]*', value.lower()):
        token = token.strip('._+-')
        if not token or token in IRRELEVANT_QUERY_WORDS or token in seen:
            continue
        seen.add(token)
        tokens.append(token)
    return tokens


def _metadata_value(metadata: dict, key: str) -> str:
    value = metadata.get(key) or {}
    text = value.get('value') if isinstance(value, dict) else value
    return re.sub(r'<[^>]+>', ' ', str(text or '')).strip()


def _encode_image_as_jpeg(raw_content: bytes) -> bytes:
    try:
        image = Image.open(BytesIO(raw_content))
        image.verify()
        image = Image.open(BytesIO(raw_content))
    except UnidentifiedImageError as exc:
        raise ValueError('Downloaded file is not a valid image') from exc

    image = ImageOps.exif_transpose(image)
    if image.mode not in ('RGB', 'L'):
        image = image.convert('RGB')
    if image.mode == 'L':
        image = image.convert('RGB')
    image.thumbnail((1200, 1200), Image.Resampling.LANCZOS)

    output = BytesIO()
    image.save(output, format='JPEG', quality=88, optimize=True)
    return output.getvalue()


def _save_public_file(filename: str, content: bytes) -> str:
    storage = PublicMediaStorage()
    stored_name = storage.save(filename, ContentFile(content))
    return _absolute_media_url(storage.url(stored_name))


def _storage_filename(product, extension: str) -> str:
    slug = slugify(getattr(product, 'title', '') or 'product')[:60] or 'product'
    return f'{PRODUCT_IMAGE_DIR}/{product.pk}-{slug}.{extension}'


def _lock_product_image(product, image_url: str, source: str) -> None:
    type(product).objects.filter(pk=product.pk, image_url_locked='').update(
        image_url_locked=image_url,
        image_source=source[:255],
    )
    product.image_url_locked = image_url
    product.image_source = source[:255]


def _source_label(candidate: ImageCandidate, query: str) -> str:
    title = slugify(candidate.title or '')[:80]
    return f'{candidate.source}:{query}:{title}'[:255]


def _absolute_media_url(image_url: str) -> str:
    if urlparse(image_url).scheme in {'http', 'https'}:
        return image_url

    base_url = (
        getattr(settings, 'PUBLIC_MEDIA_BASE_URL', '')
        or os.environ.get('PUBLIC_MEDIA_BASE_URL', '')
        or os.environ.get('RENDER_EXTERNAL_URL', '')
        or os.environ.get('SITE_URL', '')
        or 'http://localhost:8000'
    )
    return urljoin(f'{base_url.rstrip("/")}/', image_url.lstrip('/'))


def _wrap_text(text: str, max_chars: int) -> list[str]:
    words = text.split()
    lines = []
    current = ''
    for word in words:
        if not current:
            current = word
            continue
        if len(f'{current} {word}') > max_chars:
            lines.append(current)
            current = word
        else:
            current = f'{current} {word}'
    if current:
        lines.append(current)
    return lines or ['Product']
