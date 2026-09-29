export function cleanBarcode(value: string) { return value.toUpperCase().replace(/[\s-]/g, ''); }
function checkDigit(body: string) { return String((10 - [...body].reverse().reduce((total, digit, index) => total + Number(digit) * (index % 2 ? 1 : 3), 0) % 10) % 10); }
export function validBarcode(value: string) {
  const code = cleanBarcode(value);
  if (/^\d{9}[\dX]$/.test(code)) return [...code].reduce((total, digit, index) => total + (digit === 'X' ? 10 : Number(digit)) * (10 - index), 0) % 11 === 0;
  const base = [14, 17].includes(code.length) ? code.slice(0, 12) : [15, 18].includes(code.length) ? code.slice(0, 13) : code;
  return /^\d+$/.test(code) && [8, 12, 13].includes(base.length) && checkDigit(base.slice(0, -1)) === base.at(-1);
}
export function barcodeKeys(value: string) {
  const code = cleanBarcode(value);
  const keys = new Set([code]);
  if (validBarcode(code)) {
    if (code.length === 12) keys.add(`0${code}`);
    if ([14, 17].includes(code.length)) keys.add(`0${code}`);
    if (code.length === 13 && code.startsWith('0')) keys.add(code.slice(1));
    if ([15, 18].includes(code.length) && code.startsWith('0')) keys.add(code.slice(1));
    if (code.length === 10) { const body = `978${code.slice(0, 9)}`; keys.add(body + checkDigit(body)); }
    if (code.length === 13 && code.startsWith('978')) { const body = code.slice(3, 12); const digit = (11 - [...body].reduce((total, value, index) => total + Number(value) * (10 - index), 0) % 11) % 11; keys.add(body + (digit === 10 ? 'X' : digit)); }
  }
  return [...keys].filter(Boolean);
}
export function barcodeEquivalent(left: string, right: string) { const keys = new Set(barcodeKeys(left)); return barcodeKeys(right).some(key => keys.has(key)); }
export type BarcodeBounds = { left: number; top: number; width: number; height: number };
export function barcodeBounds(points: { x: number; y: number }[], width: number, height: number): BarcodeBounds | undefined {
  if (!points.length || !width || !height) return;
  const xs = points.map(point => point.x).filter(Number.isFinite), ys = points.map(point => point.y).filter(Number.isFinite);
  if (!xs.length || !ys.length) return;
  // One-dimensional decoders return points on a scan line rather than corners.
  // Highlight a surrounding region, not a purported exact segmentation mask.
  const paddingY = Math.max(35, (Math.max(...xs) - Math.min(...xs)) / 4);
  const left = Math.max(0, Math.min(width, Math.min(...xs) - 20)), top = Math.max(0, Math.min(height, Math.min(...ys) - paddingY));
  const right = Math.max(left, Math.min(width, Math.max(...xs) + 20)), bottom = Math.max(top, Math.min(height, Math.max(...ys) + paddingY));
  return { left: left / width * 100, top: top / height * 100, width: (right - left) / width * 100, height: (bottom - top) / height * 100 };
}
