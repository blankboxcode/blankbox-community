"""On-demand retailer connector boundary; this module makes search links, not offer claims."""
from __future__ import annotations

from dataclasses import dataclass
import json
from pathlib import Path
from typing import Protocol
from urllib.parse import quote, urlparse
import re

from collecting import KINDS, clean_target


class RetailerConnector(Protocol):
    id: str
    name: str
    version: str
    capabilities: frozenset[str]

    def search_link(self, query: str) -> str: ...
    def search_offers(self, query: dict) -> list[dict]: ...


@dataclass(frozen=True)
class SearchLinkConnector:
    id: str
    name: str
    version: str
    prefix: str
    registry_source_id: str
    media_kinds: frozenset[str]
    suffix: str = ''
    link_kind: str = 'search'
    capabilities: frozenset[str] = frozenset({'SEARCH_LINK'})

    def search_link(self, query: str) -> str:
        return self.prefix if self.link_kind == 'store-home' else self.prefix + quote(query, safe='') + self.suffix

    def search_offers(self, query: dict) -> list[dict]:
        # A deep link is not an offer. No price, stock, or checked-at value is invented.
        return []


ALLOWED_HOSTS = {
    'amazon': ('www.amazon.com', 'amazon'),
    'gruv': ('gruv.com', 'gruv'),
    'barnes-noble': ('www.barnesandnoble.com', 'barnes_noble'),
    'hamilton-book': ('www.hamiltonbook.com', 'hamiltonbook'),
    'ebay': ('www.ebay.com', 'ebay'),
    'mycomicshop': ('www.mycomicshop.com', 'mycomicshop'),
    'walmart': ('www.walmart.com', 'walmart'),
    'target': ('www.target.com', 'target'),
    'criterion': ('www.criterion.com', 'criterion'),
    'arrow-video': ('www.arrowfilms.com', 'arrow_video'),
    'kino-lorber': ('kinolorber.com', 'kino_lorber'),
    'shout-studios': ('shoutfactory.com', 'shout_studios'),
    'vinegar-syndrome': ('vinegarsyndrome.com', 'vinegar_syndrome'),
    'diabolikdvd': ('diabolikdvd.com', 'diabolikdvd'),
    'orbit-dvd': ('www.orbitdvd.com', 'orbit_dvd'),
    'deepdiscount': ('www.deepdiscount.com', 'deepdiscount'),
    'rarewaves': ('www.rarewaves.com', 'rarewaves'),
    'zavvi-us': ('us.zavvi.com', 'zavvi_us'),
    'amoeba-music': ('www.amoeba.com', 'amoeba_music'),
    'bandcamp': ('bandcamp.com', 'bandcamp'),
    'abebooks': ('www.abebooks.com', 'abebooks'),
    'alibris': ('www.alibris.com', 'alibris'),
    'booksamillion': ('www.booksamillion.com', 'booksamillion'),
    'bookshop': ('bookshop.org', 'bookshop_org'),
    'thriftbooks': ('www.thriftbooks.com', 'thriftbooks'),

}

DEFAULT_STORE_IDS = ('amazon', 'gruv', 'barnes-noble', 'hamilton-book', 'ebay', 'mycomicshop', 'walmart', 'target', 'criterion')


def enabled_kinds(connector, preferences):
    # A saved household selection remains exact when new choices are added.
    return preferences.get(connector.id, sorted(connector.media_kinds) if not preferences and connector.id in DEFAULT_STORE_IDS else [])


def clean_store_preferences(packaged, custom):
    available = {connector.id: connector.media_kinds for connector in connectors()}
    if not isinstance(packaged, list) or len(packaged) != len(available) or any(not isinstance(row, dict) or row.get('id') not in available for row in packaged):
        raise ValueError('Choose stores from the available search sources.')
    enabled = {}
    for row in packaged:
        identifier, kinds = row['id'], row.get('enabledKinds')
        if identifier in enabled or not isinstance(kinds, list) or len(kinds) > len(available[identifier]) or any(not isinstance(kind, str) or kind not in available[identifier] for kind in kinds) or len(set(kinds)) != len(kinds):
            raise ValueError('Choose supported media types for each store.')
        enabled[identifier] = kinds
    if not isinstance(custom, list) or len(custom) > 20:
        raise ValueError('Add up to 20 custom store searches.')
    cleaned = []
    seen = set()
    for store in custom:
        if not isinstance(store, dict):
            raise ValueError('Review each custom store search.')
        identifier = store.get('id')
        name = store.get('name')
        template = store.get('urlTemplate')
        kinds = store.get('mediaKinds')
        if not isinstance(identifier, str) or not re.fullmatch(r'custom-[a-f0-9]{32}', identifier) or identifier in seen:
            raise ValueError('Each custom store needs a unique identifier.')
        if not isinstance(name, str) or not 1 <= len(name.strip()) <= 80 or any(ord(character) < 32 for character in name):
            raise ValueError('Enter a custom store name up to 80 characters.')
        if not isinstance(template, str) or len(template) > 1000 or template.count('{query}') != 1:
            raise ValueError('Use one {query} placeholder in the HTTPS store search URL.')
        parsed = urlparse(template)
        if parsed.scheme != 'https' or not parsed.hostname or parsed.username or parsed.password or '{query}' in parsed.netloc or parsed.fragment or any(character in template for character in '\r\n\\<>'):
            raise ValueError('Use an HTTPS store search URL without credentials or a fragment.')
        if not isinstance(kinds, list) or not kinds or len(kinds) > len(KINDS) or any(not isinstance(kind, str) or kind not in KINDS for kind in kinds) or len(set(kinds)) != len(kinds):
            raise ValueError('Choose media types that this custom store sells.')
        seen.add(identifier)
        cleaned.append({'id': identifier, 'name': name.strip(), 'urlTemplate': template, 'mediaKinds': kinds})
    return enabled, cleaned


def connectors():
    """Load packaged, declarative search links; a store config can be updated alone."""
    result = []
    directory = Path(__file__).with_name('retail_connectors')
    for retailer_id, (host, registry_source_id) in ALLOWED_HOSTS.items():
        path = directory / (retailer_id + '.json')
        try:
            config = json.loads(path.read_text(encoding='utf-8'))
            prefix = config['prefix']
            if config['id'] != retailer_id or config.get('registrySourceId') != registry_source_id or not isinstance(prefix, str) or not prefix.startswith('https://' + host + '/'):
                continue
            media_kinds = config.get('mediaKinds')
            if not isinstance(media_kinds, list) or not media_kinds or any(not isinstance(kind, str) or kind not in KINDS for kind in media_kinds):
                continue
            link_kind = config.get('linkKind', 'search')
            if link_kind not in ('search', 'store-home'):
                continue
            result.append(SearchLinkConnector(retailer_id, str(config['name']), str(config['version']), prefix,
                                              registry_source_id, frozenset(media_kinds), link_kind=link_kind))
        except (OSError, ValueError, KeyError, TypeError):
            continue
    return result


def store_sources(settings):
    enabled = settings.get('retailStoreKinds') or {}
    return [{'id': connector.id, 'name': connector.name, 'linkKind': connector.link_kind, 'mediaKinds': sorted(connector.media_kinds),
             'enabledKinds': enabled_kinds(connector, enabled)}
            for connector in connectors()]


def store_links(data, settings=None):
    target = clean_target(data)
    settings = settings or {}
    enabled = settings.get('retailStoreKinds') or {}
    custom = settings.get('customRetailStores', [])
    format_term = '' if target['format'] in ('Any', 'Book', 'Comic', 'Game', 'Other') else target['format']
    season_term = 'Complete series' if target['season'] == 'complete-series' else 'Specials' if target['season'] == 'specials' else 'Season ' + target['season'] if target['season'] else ''
    query = ' '.join(str(part) for part in (target['title'], target['year'] or '', season_term, format_term) if part)
    links = [{'retailerId': connector.id, 'sourceRegistryId': connector.registry_source_id,
             'name': connector.name, 'version': connector.version,
             'capabilities': sorted(connector.capabilities), 'url': connector.search_link(query),
             'linkKind': connector.link_kind, 'query': query,
             'offerStatus': 'not-checked'} for connector in connectors() if target['kind'] in enabled_kinds(connector, enabled) and target['kind'] in connector.media_kinds]
    for store in custom:
        if target['kind'] in store['mediaKinds']:
            links.append({'retailerId': store['id'], 'sourceRegistryId': store['id'], 'name': store['name'], 'version': 'owner',
                          'capabilities': ['SEARCH_LINK'], 'url': store['urlTemplate'].replace('{query}', quote(query, safe='')),
                          'linkKind': 'search', 'query': query, 'offerStatus': 'not-checked'})
    return links
