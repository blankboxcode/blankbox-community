"""Private artwork attached to a title or one of its physical editions."""
import uuid
from datetime import datetime, timezone
from artwork import artwork_hash, jpeg_size

MAX_TITLE_IMAGES = 48
MAX_EDITION_IMAGES = 12
ROLES = {'front', 'back', 'spine', 'disc', 'other'}


class ArtworkGallery:
    def gallery_artwork(self, item_id):
        with self.db() as db:
            return [{'id': r['id'], 'releaseId': r['release_id'], 'label': r['label'], 'role': r['role'],
                     'url': f"/api/artwork/gallery/{item_id}/{r['id']}/{r['sha256'][:16]}",
                     'primary': bool(r['is_primary'])}
                    for r in db.execute('SELECT id,release_id,label,role,sha256,is_primary FROM artwork_gallery WHERE item_id=? ORDER BY created_at,id', (item_id,))]

    def save_gallery_artwork(self, item_id, image, release_id=None, label='', role='front'):
        width, height = jpeg_size(image)
        item = self.get_item(item_id)
        releases = {s.get('physicalReleaseId') for s in item.get('sources', []) if s.get('type') == 'physical'}
        if release_id not in (None, '') and release_id not in releases:
            raise ValueError('Choose an existing physical edition for this image.')
        if role not in ROLES or not isinstance(label, str) or len(label) > 120:
            raise ValueError('Choose an image role and a label up to 120 characters.')
        identifier = uuid.uuid4().hex; release_id = release_id or None
        with self.db() as db:
            db.execute('BEGIN IMMEDIATE')
            total = db.execute('SELECT COUNT(*) FROM artwork_gallery WHERE item_id=?', (item_id,)).fetchone()[0]
            scoped = db.execute('SELECT COUNT(*) FROM artwork_gallery WHERE item_id=? AND release_id IS ?', (item_id, release_id)).fetchone()[0]
            if total >= MAX_TITLE_IMAGES or scoped >= MAX_EDITION_IMAGES:
                raise ValueError('Keep up to 12 images per edition and 48 per title.')
            db.execute('INSERT INTO artwork_gallery(id,item_id,release_id,label,role,sha256,width,height,image,created_at,is_primary) VALUES(?,?,?,?,?,?,?,?,?,?,0)',
                       (identifier, item_id, release_id, label.strip() or role.title(), role, artwork_hash(image), width, height, image, datetime.now(timezone.utc).isoformat()))
            first = db.execute('SELECT 1 FROM item_artwork WHERE item_id=?', (item_id,)).fetchone() is None
        if first:
            self.save_owner_artwork(item_id, image, gallery_id=identifier)
        return {'ok': True, 'item': self.public_item(self.get_item(item_id))}

    def select_gallery_artwork(self, item_id, identifier):
        with self.db() as db:
            row = db.execute('SELECT image FROM artwork_gallery WHERE item_id=? AND id=?', (item_id, identifier)).fetchone()
        if not row:
            raise ValueError('That saved image was not found.')
        return self.save_owner_artwork(item_id, row['image'], gallery_id=identifier)

    def remove_gallery_artwork(self, item_id, identifier):
        with self.db() as db:
            row = db.execute('SELECT is_primary FROM artwork_gallery WHERE item_id=? AND id=?', (item_id, identifier)).fetchone()
        if not row:
            raise ValueError('That saved image was not found.')
        if row['is_primary']:
            self.remove_owner_artwork(item_id)
        with self.db() as db:
            db.execute('DELETE FROM artwork_gallery WHERE item_id=? AND id=?', (item_id, identifier))
        return {'ok': True, 'item': self.public_item(self.get_item(item_id))}
