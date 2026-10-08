"""Purchased orders awaiting delivery, separate from received library copies."""
from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
import hashlib
import json
import re

from collecting import clean_target, remove_target


TEXT_LIMITS = {'label': 120, 'vendor': 250, 'trackingNumber': 250, 'orderNumber': 120,
               'digitalPlatform': 120, 'digitalFormat': 120, 'notes': 4000, 'platform': 120, 'region': 80, 'barcode': 80}
DATE_FIELDS = ('dateOrdered', 'releaseDate', 'expectedDeliveryDate')
IDENTITY_FIELDS = ('title', 'kind', 'year', 'format', 'edition', 'season', 'platform', 'region', 'barcode', 'releaseType', 'digitalPlatform', 'digitalFormat')
ACTIVE_STATUSES = ('ordered', 'shipped', 'part-received')


def request_key(value):
    if not isinstance(value, str) or not re.fullmatch(r'[A-Za-z0-9-]{16,80}', value):
        raise ValueError('Reopen this form before saving.')
    return hashlib.sha256(value.encode()).hexdigest()[:32]


def positive_quantity(value, maximum=999):
    if isinstance(value, bool) or not isinstance(value, int) or not 1 <= value <= maximum:
        raise ValueError(f'Enter a quantity from 1 to {maximum}.')
    return value


def clean_preorder(data):
    if not isinstance(data.get('title'), str):
        raise ValueError('Enter a title up to 250 characters.')
    year = data.get('year')
    if year is not None and (isinstance(year, bool) or not isinstance(year, int)):
        raise ValueError('Enter a whole release year or leave it empty.')
    release_type = data.get('releaseType', 'physical')
    if release_type not in ('physical', 'digital'):
        raise ValueError('Choose a physical or digital release.')
    result = clean_target(data)
    result['releaseType'] = release_type
    from collector_features import external_url
    result['digitalUrl'] = external_url(data.get('digitalUrl', ''), optional=True)
    result['quantity'] = positive_quantity(data.get('quantity'))
    for field, maximum in TEXT_LIMITS.items():
        value = data.get(field, '')
        if not isinstance(value, str) or len(value) > maximum:
            raise ValueError(f'Enter {field} up to {maximum} characters.')
        result[field] = value.strip()
    for field in DATE_FIELDS:
        value = data.get(field, '')
        if not isinstance(value, str) or value and not re.fullmatch(r'\d{4}-\d{2}-\d{2}', value):
            raise ValueError('Enter dates as YYYY-MM-DD or leave them empty.')
        if value:
            try:
                parsed = date.fromisoformat(value)
                if not 1800 <= parsed.year <= 2200:
                    raise ValueError()
            except ValueError as error:
                raise ValueError('Enter a valid order, release, or delivery date.') from error
        result[field] = value
    price = data.get('price', '')
    if not isinstance(price, str) or price and not re.fullmatch(r'\d{1,9}(?:\.\d{1,2})?', price):
        raise ValueError('Enter a nonnegative unit price with up to two decimal places.')
    try:
        result['price'] = str(Decimal(price).quantize(Decimal('0.01'))) if price else ''
    except InvalidOperation as error:
        raise ValueError('Enter a valid unit price.') from error
    currency = data.get('currency', 'USD')
    if not isinstance(currency, str) or not re.fullmatch(r'[A-Za-z]{3}', currency):
        raise ValueError('Enter a three-letter currency code.')
    result['currency'] = currency.upper()
    status = data.get('deliveryStatus', 'ordered')
    if status not in ('ordered', 'shipped', 'cancelled'):
        raise ValueError('Choose Ordered, Shipped, or Cancelled.')
    result['deliveryStatus'] = status
    return result


def order_status(order):
    if order['receivedQuantity'] == order['quantity']:
        return 'received'
    if order['deliveryStatus'] == 'cancelled':
        return 'cancelled'
    return 'part-received' if order['receivedQuantity'] else order['deliveryStatus']


def get_preorder(db, identifier):
    if not isinstance(identifier, str) or not re.fullmatch(r'preorder-[0-9a-f]{32}', identifier):
        raise ValueError('Choose a preorder.')
    row = db.execute('SELECT data FROM preorders WHERE id=?', (identifier,)).fetchone()
    if not row:
        raise ValueError('This preorder is no longer available.')
    return json.loads(row[0])


def check_revision(order, data):
    revision = data.get('revision')
    if isinstance(revision, bool) or not isinstance(revision, int) or revision != order['revision']:
        raise ValueError('This preorder changed on another screen. Reload it before saving.')


def store_preorder(db, order):
    order['status'] = order_status(order)
    db.execute('INSERT INTO preorders(id,data) VALUES(?,?) ON CONFLICT(id) DO UPDATE SET data=excluded.data',
               (order['id'], json.dumps(order)))


def save_preorder(db, data, timestamp):
    """The caller owns the transaction, including an optional wishlist transfer."""
    prepared = clean_preorder(data)
    if not isinstance(data.get('moveIntention', False), bool):
        raise ValueError('Choose whether to move the saved intention.')
    if data.get('id'):
        current = get_preorder(db, data['id'])
        check_revision(current, data)
        if current['receivedQuantity'] and any(prepared[field] != current.get(field, 'physical' if field == 'releaseType' else '') for field in (*IDENTITY_FIELDS, 'quantity')):
            raise ValueError('Received copies keep their title, edition, and ordered quantity. Create another preorder for a different release.')
        if current['status'] == 'received' and prepared['deliveryStatus'] == 'cancelled':
            raise ValueError('This order has already been received. Its delivery cannot be cancelled.')
        order = {**current, **prepared, 'revision': current['revision'] + 1, 'updatedAt': timestamp}
        if any(prepared[field] != current.get(field, 'physical' if field == 'releaseType' else '') for field in IDENTITY_FIELDS):
            order.pop('intentionReference', None)
    else:
        identifier = 'preorder-' + request_key(data.get('requestId'))
        signature = hashlib.sha256(json.dumps({**prepared, 'intentionId': data.get('intentionId'), 'moveIntention': data.get('moveIntention', False)}, sort_keys=True).encode()).hexdigest()
        row = db.execute('SELECT data FROM preorders WHERE id=?', (identifier,)).fetchone()
        if row:
            existing = json.loads(row[0])
            if existing['createDigest'] != signature:
                raise ValueError('This save was already used for a different preorder. Reopen the form.')
            return existing
        order = {**prepared, 'id': identifier, 'receivedQuantity': 0, 'revision': 1,
                 'createdAt': timestamp, 'updatedAt': timestamp, 'createDigest': signature}
        if data.get('intentionId') or data.get('moveIntention'):
            identifier = data.get('intentionId')
            if not isinstance(identifier, str) or not re.fullmatch(r'intent-[0-9a-f]{32}', identifier):
                raise ValueError('Choose a saved intention.')
            intention = db.execute('SELECT title,kind,year,desired_format,edition,season,work_id,release_id FROM collecting_targets WHERE id=?', (identifier,)).fetchone()
            matches = intention and tuple(intention)[:6] == tuple(prepared[field] for field in ('title', 'kind', 'year', 'format', 'edition', 'season'))
            if data.get('moveIntention') and not matches:
                raise ValueError('The intention changed. Reopen it before moving it to Preorders.')
            if matches:
                order['intentionId'] = identifier
                order['intentionReference'] = {'workId': intention['work_id'], 'releaseId': intention['release_id']}
                if intention['release_id']:
                    row = db.execute("SELECT namespace,value FROM metadata_identifiers WHERE entity_id=? AND namespace IN ('isbn','upc-ean') ORDER BY namespace,value LIMIT 1", (intention['release_id'],)).fetchone()
                    if row:
                        order['intentionReference']['identifier'] = dict(row)
                if data.get('moveIntention'):
                    remove_target(db, identifier)
    store_preorder(db, order)
    return order


def public_preorder(order):
    return {key: value for key, value in order.items() if key != 'createDigest'}


def preorder_page(db, *, query='', status='active', offset=0, limit=25):
    if not isinstance(query, str) or len(query) > 250 or status not in ('active', 'all', 'ordered', 'shipped', 'part-received', 'received', 'cancelled'):
        raise ValueError('Choose a valid preorder search and status.')
    if not 0 <= offset <= 1000000 or not 1 <= limit <= 50:
        raise ValueError('Choose a valid preorder page.')
    where, values = [], []
    if status == 'active':
        where.append("json_extract(data,'$.status') IN ('ordered','shipped','part-received')")
    elif status != 'all':
        where.append("json_extract(data,'$.status')=?")
        values.append(status)
    if query.strip():
        where.append("instr(lower(json_extract(data,'$.title')||' '||json_extract(data,'$.vendor')||' '||json_extract(data,'$.label')||' '||json_extract(data,'$.orderNumber')),lower(?))>0")
        values.append(query.strip())
    clause = ' WHERE ' + ' AND '.join(where) if where else ''
    total = db.execute('SELECT COUNT(*) FROM preorders' + clause, values).fetchone()[0]
    rows = db.execute("SELECT data FROM preorders" + clause + " ORDER BY json_extract(data,'$.createdAt') DESC,id LIMIT ? OFFSET ?", (*values, limit, offset)).fetchall()
    counts = dict(db.execute("SELECT json_extract(data,'$.status'),COUNT(*) FROM preorders GROUP BY json_extract(data,'$.status')"))
    return {'preorders': [public_preorder(json.loads(row[0])) for row in rows], 'total': total, 'offset': offset, 'limit': limit,
            'counts': {'active': sum(counts.get(key, 0) for key in ACTIVE_STATUSES), 'received': counts.get('received', 0), 'cancelled': counts.get('cancelled', 0)}}


def preorder_detail(db, identifier):
    order = public_preorder(get_preorder(db, identifier))
    receipts = []
    for row in db.execute('SELECT data FROM preorder_receipts WHERE preorder_id=? ORDER BY rowid DESC LIMIT 999', (identifier,)):
        receipt = json.loads(row[0])
        receipt.pop('inputDigest', None)
        item_id = receipt['itemId']
        if not db.execute('SELECT 1 FROM items WHERE id=?', (item_id,)).fetchone():
            alias = db.execute('SELECT item_id FROM catalog_item_aliases WHERE alias_id=?', (item_id,)).fetchone()
            item_id = alias[0] if alias else None
        receipts.append({**receipt, 'currentItemId': item_id})
    return {'preorder': order, 'receipts': receipts}
