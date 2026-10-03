"""Opt-in OIDC authorization code flow, PKCE, and RS256 ID-token validation.

Only explicitly linked issuer/subject identities can open an existing owner
profile. No email matching, auto-provisioning, token persistence, or redirects
on outbound requests. The local password and recovery key remain independent.
"""
import base64
import hashlib
import hmac
import ipaddress
import json
import math
import os
from pathlib import Path
import secrets
import threading
import time
import urllib.parse
import urllib.request

MAX_RESPONSE = 256 * 1024


def b64(value):
    return base64.urlsafe_b64encode(value).rstrip(b'=').decode('ascii')


def unb64(value):
    if not isinstance(value, str) or len(value) > 24000 or any(c not in 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789-_' for c in value):
        raise ValueError('Invalid identity token encoding.')
    return base64.b64decode(value + '=' * (-len(value) % 4), altchars=b'-_', validate=True)


def endpoint(value):
    if not isinstance(value, str) or len(value) > 2000:
        raise ValueError('Enter a complete OIDC endpoint address.')
    url = urllib.parse.urlsplit(value)
    try:
        loopback = url.hostname == 'localhost' or ipaddress.ip_address(url.hostname or '').is_loopback
    except ValueError:
        loopback = False
    if not url.hostname or url.username or url.password or url.fragment or url.scheme != 'https' and not (url.scheme == 'http' and loopback):
        raise ValueError('OIDC requires HTTPS; HTTP is allowed only for loopback development.')
    _ = url.port
    return value


def configuration(value):
    if value in (None, ''):
        return None
    if isinstance(value, str):
        value = json.loads(value)
    if not isinstance(value, dict) or set(value) - {'issuer', 'clientId', 'redirectUri', 'clientSecretFile', 'name'}:
        raise ValueError('Check the OIDC configuration fields.')
    issuer = endpoint(value.get('issuer'))
    if urllib.parse.urlsplit(issuer).query:
        raise ValueError('The OIDC issuer cannot contain a query.')
    redirect = endpoint(value.get('redirectUri'))
    uri = urllib.parse.urlsplit(redirect)
    if uri.path != '/api/oidc/callback' or uri.query:
        raise ValueError('Use /api/oidc/callback as the exact registered redirect path.')
    client = value.get('clientId'); name = value.get('name', 'Identity provider')
    if not isinstance(client, str) or not 1 <= len(client) <= 200 or not isinstance(name, str) or not 1 <= len(name) <= 80:
        raise ValueError('Enter the OIDC client ID and provider name.')
    secret = value.get('clientSecretFile')
    if secret is not None and (not isinstance(secret, str) or not Path(secret).is_absolute()):
        raise ValueError('Use an absolute path for the private OIDC client-secret file.')
    return {'issuer': issuer, 'clientId': client, 'redirectUri': redirect, 'name': name, 'clientSecretFile': secret}


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request_json(url, body=None, headers=None):
    endpoint(url)
    request = urllib.request.Request(url, data=body, headers={'Accept': 'application/json', **(headers or {})})
    try:
        with urllib.request.build_opener(NoRedirect).open(request, timeout=10) as response:
            data = response.read(MAX_RESPONSE + 1)
        if len(data) > MAX_RESPONSE:
            raise ValueError('OIDC response is too large.')
        result = json.loads(data)
        if not isinstance(result, dict):
            raise ValueError('Invalid OIDC response.')
        return result
    except (OSError, ValueError) as error:
        raise ValueError('The identity provider could not complete this request. Local sign-in remains available.') from error


def validate_id_token(token, keys, config, nonce, access_token=None, clock=None):
    if not isinstance(token, str) or len(token) > 24000 or token.count('.') != 2:
        raise ValueError('Invalid identity token.')
    head, payload, signature = token.split('.')
    header = json.loads(unb64(head)); claims = json.loads(unb64(payload))
    if not isinstance(header, dict) or not isinstance(claims, dict) or header.get('alg') != 'RS256' or header.get('crit') or 'jku' in header or 'x5u' in header:
        raise ValueError('Only signed RS256 identity tokens are supported.')
    matching = [key for key in keys if isinstance(key, dict) and key.get('kty') == 'RSA' and key.get('kid') == header.get('kid')
                and key.get('use', 'sig') == 'sig' and key.get('alg', 'RS256') == 'RS256' and ('key_ops' not in key or 'verify' in key['key_ops'])]
    if len(matching) != 1:
        raise ValueError('The identity signing key was not found or is ambiguous.')
    key = matching[0]
    n = int.from_bytes(unb64(key.get('n')), 'big'); e = int.from_bytes(unb64(key.get('e')), 'big')
    if not 2048 <= n.bit_length() <= 8192 or not 3 <= e <= 2**32 - 1 or e % 2 == 0:
        raise ValueError('Unsupported identity signing key.')
    signed = unb64(signature); length = (n.bit_length() + 7) // 8
    if len(signed) != length or int.from_bytes(signed, 'big') >= n:
        raise ValueError('Invalid identity signature.')
    digest_info = bytes.fromhex('3031300d060960864801650304020105000420') + hashlib.sha256((head + '.' + payload).encode('ascii')).digest()
    expected = b'\x00\x01' + b'\xff' * (length - len(digest_info) - 3) + b'\x00' + digest_info
    decoded = pow(int.from_bytes(signed, 'big'), e, n).to_bytes(length, 'big')
    if not hmac.compare_digest(decoded, expected):
        raise ValueError('Identity signature verification failed.')
    current = time.time() if clock is None else clock
    audience = claims.get('aud'); audience = [audience] if isinstance(audience, str) else audience
    if claims.get('iss') != config['issuer'] or not isinstance(audience, list) or config['clientId'] not in audience or any(not isinstance(a, str) for a in audience):
        raise ValueError('The identity token belongs to another issuer or application.')
    if (len(audience) > 1 or 'azp' in claims) and claims.get('azp') != config['clientId']:
        raise ValueError('The identity token has a different authorized party.')
    for field in ('exp', 'iat'):
        value = claims.get(field)
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError('Invalid identity token lifetime.')
    if claims['exp'] <= current or claims['iat'] > current + 60 or claims['iat'] < current - 3600:
        raise ValueError('The identity token is expired or not current.')
    if 'nbf' in claims and (isinstance(claims['nbf'], bool) or not isinstance(claims['nbf'], (int, float)) or not math.isfinite(claims['nbf']) or claims['nbf'] > current + 60):
        raise ValueError('The identity token is not valid yet.')
    if not isinstance(claims.get('nonce'), str) or not hmac.compare_digest(claims['nonce'], nonce):
        raise ValueError('The identity token does not match this sign-in request.')
    subject = claims.get('sub')
    if not isinstance(subject, str) or not 1 <= len(subject) <= 255:
        raise ValueError('Invalid identity subject.')
    if 'at_hash' in claims:
        if not isinstance(access_token, str) or claims['at_hash'] != b64(hashlib.sha256(access_token.encode('ascii')).digest()[:16]):
            raise ValueError('The access token does not match the identity token.')
    return subject


class OIDC:
    def __init__(self, config):
        self.config = configuration(config)
        self.pending = {}; self.lock = threading.RLock(); self.generation = 0; self.cached = None; self.cached_at = 0

    def metadata(self, refresh=False):
        if not refresh and self.cached and time.time() - self.cached_at < 300:
            return self.cached
        config = self.config
        discovered = request_json(config['issuer'].rstrip('/') + '/.well-known/openid-configuration')
        if discovered.get('issuer') != config['issuer']:
            raise ValueError('OIDC discovery returned a different issuer.')
        for field in ('authorization_endpoint', 'token_endpoint', 'jwks_uri'):
            endpoint(discovered.get(field))
        if 'RS256' not in discovered.get('id_token_signing_alg_values_supported', ['RS256']):
            raise ValueError('This provider does not support RS256 identity tokens.')
        if 'S256' not in discovered.get('code_challenge_methods_supported', ['S256']):
            raise ValueError('This provider does not support PKCE S256.')
        keys = request_json(discovered['jwks_uri']).get('keys')
        if not isinstance(keys, list) or len(keys) > 100:
            raise ValueError('Invalid identity signing-key list.')
        self.cached = (discovered, keys); self.cached_at = time.time()
        return self.cached

    def begin(self, purpose, profile_id=None, remember=False):
        if purpose not in ('login', 'link') or purpose == 'link' and not profile_id:
            raise ValueError('Choose a valid identity action.')
        discovered, _ = self.metadata()
        state = secrets.token_urlsafe(32); binding = secrets.token_urlsafe(32)
        nonce = secrets.token_urlsafe(32); verifier = secrets.token_urlsafe(48)
        with self.lock:
            self.pending = {k: v for k, v in self.pending.items() if v['expires'] > time.time()}
            if len(self.pending) >= 100:
                raise ValueError('Too many identity sign-in attempts. Try again later.')
            self.pending[state] = {'binding': hashlib.sha256(binding.encode()).digest(), 'nonce': nonce, 'verifier': verifier,
                                   'purpose': purpose, 'profileId': profile_id, 'remember': remember, 'generation': self.generation, 'expires': time.time() + 300}
        query = urllib.parse.urlencode({'response_type': 'code', 'client_id': self.config['clientId'], 'redirect_uri': self.config['redirectUri'],
                                      'scope': 'openid', 'state': state, 'nonce': nonce, 'code_challenge_method': 'S256',
                                      'code_challenge': b64(hashlib.sha256(verifier.encode('ascii')).digest())})
        url = discovered['authorization_endpoint'] + ('&' if '?' in discovered['authorization_endpoint'] else '?') + query
        return url, binding

    def complete(self, state, binding, code):
        if not all(isinstance(v, str) and 1 <= len(v) <= limit for v, limit in ((state, 128), (binding, 128), (code, 4096))):
            raise ValueError('Invalid identity callback.')
        with self.lock:
            pending = self.pending.get(state)
            if not pending or pending['expires'] <= time.time() or not hmac.compare_digest(pending['binding'], hashlib.sha256(binding.encode()).digest()):
                raise ValueError('This identity sign-in request has expired or belongs to another browser.')
            del self.pending[state]
        discovered, keys = self.metadata()
        values = {'grant_type': 'authorization_code', 'code': code, 'redirect_uri': self.config['redirectUri'], 'client_id': self.config['clientId'], 'code_verifier': pending['verifier']}
        headers = {'Content-Type': 'application/x-www-form-urlencoded'}
        secret_path = self.config['clientSecretFile']
        if secret_path:
            path = Path(secret_path)
            if any(p.is_symlink() for p in (path, *path.parents)) or not path.is_file() or path.stat().st_size > 4096 or os.name != 'nt' and path.stat().st_mode & 0o077:
                raise ValueError('Protect the private OIDC client-secret file before enabling sign-in.')
            secret = path.read_text().strip()
            if not secret:
                raise ValueError('The OIDC client-secret file is empty.')
            basic = urllib.parse.quote(self.config['clientId'], safe='') + ':' + urllib.parse.quote(secret, safe='')
            headers['Authorization'] = 'Basic ' + base64.b64encode(basic.encode()).decode()
        response = request_json(discovered['token_endpoint'], urllib.parse.urlencode(values).encode(), headers)
        try:
            subject = validate_id_token(response.get('id_token'), keys, self.config, pending['nonce'], response.get('access_token'))
        except ValueError:
            _, keys = self.metadata(refresh=True)
            subject = validate_id_token(response.get('id_token'), keys, self.config, pending['nonce'], response.get('access_token'))
        return pending, subject
