"""Bounded user-entered service links and digital collection records."""
import re
import uuid
from urllib.parse import urlsplit

BUILTIN_SERVICES = {'netflix', 'prime-video', 'disney-plus', 'youtube', 'spotify', 'apple-tv', 'movies-anywhere'}
DIGITAL_STATUSES = {'purchased', 'redeemed', 'code-included'}


def text(value, limit, label):
    if not isinstance(value, str) or len(value) > limit or any(ord(c) < 32 for c in value):
        raise ValueError(f'Check {label}.')
    return value.strip()


def external_url(value, optional=False):
    value = text(value, 2000, 'the service link')
    if optional and not value:
        return ''
    try:
        url = urlsplit(value)
        if url.scheme not in ('https', 'http') or not url.hostname or url.username or url.password:
            raise ValueError
        _ = url.port
    except ValueError as error:
        raise ValueError('Use a complete HTTP or HTTPS address without embedded credentials.') from error
    return value


def service_preferences(overrides, custom):
    result = []
    for rows, builtin in ((overrides, True), (custom, False)):
        if not isinstance(rows, list) or len(rows) > (len(BUILTIN_SERVICES) if builtin else 30):
            raise ValueError('Keep up to 30 custom services and one override per built-in service.')
        cleaned = []; seen = set()
        for row in rows:
            if not isinstance(row, dict):
                raise ValueError('Check the service details.')
            identifier = row.get('id')
            if not isinstance(identifier, str) or (identifier not in BUILTIN_SERVICES if builtin else not re.fullmatch(r'custom-[a-zA-Z0-9_-]{1,80}', identifier)) or identifier in seen:
                raise ValueError('Choose each service once.')
            name = text(row.get('name', ''), 80, 'the service name')
            if not name:
                raise ValueError('Enter a service name.')
            enabled = row.get('enabled', True)
            if not isinstance(enabled, bool):
                raise ValueError('Choose whether to show the service.')
            cleaned.append({'id': identifier, 'name': name, 'url': external_url(row.get('url', '')), 'enabled': enabled})
            seen.add(identifier)
        result.append(cleaned)
    return tuple(result)


def digital_platforms(rows, item):
    if not isinstance(rows, list) or len(rows) > 30:
        raise ValueError('Keep up to 30 digital platform records per title.')
    physical = {s.get('id') for s in item.get('sources', []) if s.get('type') == 'physical'}
    result = []; seen = set()
    for row in rows:
        if not isinstance(row, dict):
            raise ValueError('Check the digital platform record.')
        identifier = row.get('id') or uuid.uuid4().hex
        if not isinstance(identifier, str) or not re.fullmatch(r'[a-zA-Z0-9_-]{1,80}', identifier) or identifier in seen:
            raise ValueError('Choose each digital platform record once.')
        platform = text(row.get('platform', ''), 120, 'the platform name')
        status = row.get('status')
        source_id = row.get('physicalSourceId', '')
        if not platform or status not in DIGITAL_STATUSES or not isinstance(source_id, str) or source_id and source_id not in physical:
            raise ValueError('Choose a platform, purchase/code status, and an existing physical copy if applicable.')
        result.append({'id': identifier, 'platform': platform, 'status': status,
                       'url': external_url(row.get('url', ''), optional=True),
                       'notes': text(row.get('notes', ''), 1000, 'the digital platform notes'),
                       'physicalSourceId': source_id})
        seen.add(identifier)
    return result
