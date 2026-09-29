"""Exact local ISBN/GTIN equivalence, never fuzzy product identification."""
import re


def clean_barcode(value):
    if not isinstance(value, str) or not 1 <= len(value.strip()) <= 80:
        raise ValueError('Enter a barcode of up to 80 characters.')
    code = re.sub(r'[\s-]', '', value.upper())
    if not re.fullmatch(r'[A-Z0-9]{1,80}', code):
        raise ValueError('Use the letters and numbers printed below the barcode.')
    return code


def check_digit(body):
    return str((10 - sum(int(digit) * (3 if index % 2 == 0 else 1) for index, digit in enumerate(reversed(body))) % 10) % 10)


def valid_barcode(code):
    if re.fullmatch(r'\d{9}[\dX]', code):
        return sum((10 if digit == 'X' else int(digit)) * (10 - index) for index, digit in enumerate(code)) % 11 == 0
    base = code[:12] if len(code) in (14, 17) else code[:13] if len(code) in (15, 18) else code
    return code.isdigit() and len(base) in (8, 12, 13) and check_digit(base[:-1]) == base[-1]


def barcode_keys(value):
    code = clean_barcode(value)
    keys = [code]
    if valid_barcode(code):
        if len(code) == 12:
            keys.append('0' + code)
        if len(code) in (14, 17):
            keys.append('0' + code)
        if len(code) == 13 and code.startswith('0'):
            keys.append(code[1:])
        if len(code) in (15, 18) and code.startswith('0'):
            keys.append(code[1:])
        if len(code) == 10:
            body = '978' + code[:9]
            keys.append(body + check_digit(body))
        if len(code) == 13 and code.startswith('978'):
            body = code[3:12]
            digit = (11 - sum(int(digit) * (10 - index) for index, digit in enumerate(body)) % 11) % 11
            keys.append(body + ('X' if digit == 10 else str(digit)))
    return list(dict.fromkeys(keys))
