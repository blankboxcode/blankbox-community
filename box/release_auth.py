"""Verify publisher RSA-PSS/SHA-256 signatures (RFC 8017, 32-byte salt)."""
import base64
import hashlib
import hmac
import json
from pathlib import Path


def verify_signature(message, signature, trust=None):
    """Strict verification with the locally installed trust anchor; no network."""
    trust = Path(trust) if trust else Path(__file__).with_name('release-trust.json')
    keys = json.loads(trust.read_text(encoding='ascii'))
    if keys.get('format') != 1 or signature.get('algorithm') != 'RSA-PSS-SHA256':
        raise ValueError('Unsupported publisher signature.')
    key = keys.get('keys', {}).get(signature.get('keyId'))
    if not isinstance(key, dict):
        raise ValueError('This publisher key is not trusted by this installation.')
    modulus = int(key['n'], 16)
    exponent = key['e']
    if not 3072 <= modulus.bit_length() <= 4096 or exponent != 65537:
        raise ValueError('Unsupported publisher key.')
    try:
        raw = base64.b64decode(signature['value'], validate=True)
    except (ValueError, TypeError) as error:
        raise ValueError('Invalid publisher signature encoding.') from error
    width = (modulus.bit_length() + 7) // 8
    value = int.from_bytes(raw, 'big')
    if len(raw) != width or value >= modulus:
        raise ValueError('Invalid publisher signature size.')
    bits = modulus.bit_length() - 1
    length = (bits + 7) // 8
    decoded = pow(value, exponent, modulus)
    if decoded >= 1 << (length * 8):
        raise ValueError('Invalid publisher signature.')
    encoded = decoded.to_bytes(length, 'big')
    if encoded[-1] != 0xbc:
        raise ValueError('Invalid publisher signature padding.')
    masked, digest = encoded[:-33], encoded[-33:-1]
    unused = 8 * length - bits
    if masked[0] & (0xff << (8 - unused) & 0xff):
        raise ValueError('Invalid publisher signature padding.')
    mask = b''.join(hashlib.sha256(digest + counter.to_bytes(4, 'big')).digest()
                    for counter in range((len(masked) + 31) // 32))[:len(masked)]
    plain = bytearray(a ^ b for a, b in zip(masked, mask))
    plain[0] &= 0xff >> unused
    if plain[:-33] != b'\0' * (len(plain) - 33) or plain[-33] != 1:
        raise ValueError('Invalid publisher signature padding.')
    expected = hashlib.sha256(b'\0' * 8 + hashlib.sha256(message).digest() + plain[-32:]).digest()
    if not hmac.compare_digest(expected, digest):
        raise ValueError('Publisher signature verification failed.')


def manifest_bytes(value):
    return json.dumps({k: v for k, v in value.items() if k != 'publisherSignature'},
                      sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode('utf-8')
