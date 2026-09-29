"""Evidence-backed edition gaps. Reference coverage is never assumed exhaustive."""
from collecting import format_key


def edition_status(record, physical, owned, digital):
    if record['id'] in owned:
        return 'owned'
    if record['id'] in digital:
        return 'digital'
    format_name = record.get('format')
    if not format_name:
        return 'unknown'
    possible = []
    for source in physical:
        # Legacy Book records don't establish a binding; generic reference Book
        # records likewise cannot rule out a hardcover or paperback copy.
        same_format = format_key(source.get('label')) == format_key(format_name)
        generic_book = format_name in ('Book', 'Hardcover', 'Paperback') and source.get('label') in ('Book', 'Hardcover', 'Paperback') and 'Book' in (format_name, source.get('label'))
        if not same_format and not generic_book:
            continue
        season = record.get('season')
        if season and source.get('season') not in (None, 'complete-series', season):
            continue
        if generic_book or not record.get('edition') or not source.get('edition') or source['edition'].casefold() == record['edition'].casefold():
            possible.append(source)
    return 'review' if possible else 'missing'


def reference_summary(editions):
    refs = [row for row in editions if row['origin'] not in ('household-copy', 'household-file')]
    counts = {state: sum(row['status'] == state for row in refs) for state in ('owned', 'digital', 'missing', 'review', 'unknown')}
    return {**counts, 'known': len(refs), 'coverage': 'known-references-only',
            'status': 'unknown' if not refs else 'review' if counts['review'] or counts['unknown'] else 'gaps' if counts['missing'] or counts['digital'] else 'all-known-owned'}
