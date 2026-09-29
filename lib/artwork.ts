const MAX_INPUT = 12 * 1024 * 1024;
const MAX_SAVED = 512 * 1024;

async function withoutJpegMetadata(image: Blob): Promise<Blob> {
  const bytes = new Uint8Array(await image.arrayBuffer());
  if (bytes[0] !== 0xff || bytes[1] !== 0xd8) throw new Error('The browser could not encode this cover.');
  const sections: BlobPart[] = [bytes.slice(0, 2)];
  let offset = 2;
  while (offset < bytes.length - 2) {
    const start = offset;
    if (bytes[offset++] !== 0xff) throw new Error('The browser produced a damaged JPEG.');
    while (bytes[offset] === 0xff) offset++;
    const marker = bytes[offset++];
    if (marker === 0xda) {
      sections.push(bytes.slice(start));
      return new Blob(sections, { type: 'image/jpeg' });
    }
    if (offset + 2 > bytes.length) break;
    const length = (bytes[offset] << 8) | bytes[offset + 1];
    if (length < 2 || offset + length > bytes.length) break;
    offset += length;
    if (!(marker >= 0xe1 && marker <= 0xef) && marker !== 0xfe) sections.push(bytes.slice(start, offset));
  }
  throw new Error('The browser produced a damaged JPEG.');
}

export async function prepareCover(input: Blob): Promise<Blob> {
  if (!['image/jpeg', 'image/png', 'image/webp'].includes(input.type) || !input.size || input.size > MAX_INPUT) {
    throw new Error('Choose a JPG, PNG, or WebP image smaller than 12 MB.');
  }
  const url = URL.createObjectURL(input);
  try {
    const image = new Image();
    image.src = url;
    await image.decode();
    if (!image.naturalWidth || !image.naturalHeight || image.naturalWidth * image.naturalHeight > 40_000_000) {
      throw new Error('This image is too large to prepare as a cover.');
    }
    let scale = Math.min(1, 1200 / image.naturalWidth, 1800 / image.naturalHeight);
    for (let attempt = 0; attempt < 8; attempt++) {
      const canvas = document.createElement('canvas');
      canvas.width = Math.max(1, Math.round(image.naturalWidth * scale));
      canvas.height = Math.max(1, Math.round(image.naturalHeight * scale));
      const context = canvas.getContext('2d');
      if (!context) throw new Error('This browser cannot prepare cover artwork.');
      context.fillStyle = '#f7f7f7';
      context.fillRect(0, 0, canvas.width, canvas.height);
      context.drawImage(image, 0, 0, canvas.width, canvas.height);
      const quality = Math.max(0.5, 0.86 - attempt * 0.06);
      const blob = await new Promise<Blob | null>(resolve => canvas.toBlob(resolve, 'image/jpeg', quality));
      if (blob?.type === 'image/jpeg') {
        const clean = await withoutJpegMetadata(blob);
        if (clean.size <= MAX_SAVED) return clean;
      }
      scale *= 0.8;
    }
    throw new Error('This image could not fit the 512 KB cover limit. Choose a smaller image.');
  } finally {
    URL.revokeObjectURL(url);
  }
}
