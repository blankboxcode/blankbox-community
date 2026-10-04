"""Confined reads and verified, non-replacing file copies."""
from pathlib import Path
import hashlib
import os
import stat
import uuid

CHUNK = 1024 * 1024

def reject_links(path):
    """Reject symlinks and Windows reparse points in every existing component."""
    path = Path(os.path.abspath(Path(path).expanduser()))
    for part in (*reversed(path.parents), path):
        try:
            details = part.lstat()
        except FileNotFoundError:
            continue
        if stat.S_ISLNK(details.st_mode) or getattr(details, 'st_file_attributes', 0) & 0x400:
            raise ValueError('Linked paths and Windows reparse points are not allowed here.')
    return path

def inside(path:Path,root:Path):
    try: path.relative_to(root); return True
    except ValueError: return False

def digest(path):
    h=hashlib.sha256()
    with open(path,'rb') as f:
        for part in iter(lambda:f.read(CHUNK),b''): h.update(part)
    return h.hexdigest()

def safe_file(root,relative):
    root=reject_links(root)
    rel=Path(relative)
    if rel.is_absolute() or rel.drive or '..' in rel.parts: raise ValueError('Source path is outside the configured folder.')
    current=root
    for part in rel.parts:
        current=current/part
        if current.is_symlink(): raise ValueError('Symbolic links are not imported.')
    resolved=current.resolve(strict=True)
    if not inside(resolved,root) or not resolved.is_file(): raise ValueError('Source is not a regular file.')
    return resolved

def open_linked_file(root,relative,expected_root=None):
    """Open a configured source without following symlink components on Linux."""
    root=reject_links(root)
    rel=Path(relative)
    if not relative or rel.is_absolute() or rel.drive or '..' in rel.parts or '.' in rel.parts:
        raise ValueError('Linked file is outside the configured folder.')
    if os.name=='posix' and hasattr(os,'O_NOFOLLOW') and hasattr(os,'O_DIRECTORY'):
        directory=os.open(root,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW)
        try:
            root_details=os.fstat(directory)
            if expected_root and f'{root_details.st_dev}:{root_details.st_ino}'!=expected_root:
                raise ValueError('The linked drive changed. Index it again.')
            for part in rel.parts[:-1]:
                next_directory=os.open(part,os.O_RDONLY|os.O_DIRECTORY|os.O_NOFOLLOW,dir_fd=directory)
                os.close(directory);directory=next_directory
            descriptor=os.open(rel.parts[-1],os.O_RDONLY|os.O_NOFOLLOW|os.O_NONBLOCK,dir_fd=directory)
            try:
                if not stat.S_ISREG(os.fstat(descriptor).st_mode):raise ValueError('Linked source is not a regular file.')
                return os.fdopen(descriptor,'rb')
            except Exception:
                os.close(descriptor);raise
        finally:os.close(directory)
    # Windows does not support dir_fd. Recheck the confined resolved path and
    # handle identity after opening, and never accept a browser-supplied path.
    path=safe_file(root,relative)
    reject_links(path)
    before=path.stat()
    stream=open(path,'rb')
    try:
        details=root.stat()
        if expected_root and f'{details.st_dev}:{details.st_ino}'!=expected_root:
            raise ValueError('The linked drive changed. Index it again.')
        if fingerprint(before)!=fingerprint(os.fstat(stream.fileno())) or path.resolve()!=safe_file(root,relative):
            raise ValueError('Linked source changed while opening it.')
        return stream
    except Exception:
        stream.close();raise

def safe_destination(root,relative):
    root=reject_links(root)
    rel=Path(relative)
    if rel.is_absolute() or rel.drive or '..' in rel.parts or root.is_symlink():raise ValueError('Destination is outside the configured folder.')
    current=root
    for part in rel.parts:
        current=current/part
        if current.is_symlink():raise ValueError('A destination directory or file is a symbolic link.')
    if not inside(current.resolve(),root.resolve()):raise ValueError('Destination is outside the configured folder.')
    return current

def fingerprint(st): return (st.st_dev,st.st_ino,st.st_size,st.st_mtime_ns)

def _directory_handle(path, create=False, for_fsync=False):
    path = Path(os.path.abspath(path))
    descriptor = os.open(path.anchor, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW)
    try:
        parts=path.parts[1:]
        for index,part in enumerate(parts):
            if create:
                try:
                    os.mkdir(part, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            # Linux O_PATH needs search permission rather than read permission
            # on each ancestor. The final destination still needs a readable
            # directory handle for fsync after the exclusive link is created.
            directory_flags=(os.O_RDONLY if for_fsync and index==len(parts)-1 else getattr(os,'O_PATH',os.O_RDONLY)) | os.O_DIRECTORY | os.O_NOFOLLOW
            child = os.open(part, directory_flags, dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def checked_copy(src, dst, expected=None):
    """Copy through checked handles and commit exclusively, preserving originals."""
    src, dst = reject_links(src), reject_links(dst)
    temporary = '.blank-box-' + uuid.uuid4().hex + '.partial'
    source_dir = destination_dir = None
    temporary_created = False
    anchored = os.name == 'posix' and hasattr(os, 'O_NOFOLLOW') and hasattr(os, 'O_DIRECTORY')
    pending = dst.parent / temporary
    try:
        if anchored:
            source_dir = _directory_handle(src.parent)
            destination_dir = _directory_handle(dst.parent, create=True, for_fsync=True)
            source_args = {'dir_fd': source_dir}
            destination_args = {'dir_fd': destination_dir}
            source_name, destination_name, temporary_name = src.name, dst.name, temporary
        else:
            dst.parent.mkdir(parents=True, exist_ok=True)
            reject_links(dst)
            source_args = destination_args = {}
            source_name, destination_name, temporary_name = src, dst, pending
        flags = os.O_RDONLY | getattr(os, 'O_NOFOLLOW', 0) | getattr(os, 'O_NONBLOCK', 0)
        try:
            existing = os.open(destination_name, flags, **destination_args)
        except FileNotFoundError:
            pass
        else:
            with os.fdopen(existing, 'rb') as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ValueError('The destination is not a regular file.')
                value = hashlib.sha256()
                for part in iter(lambda: stream.read(CHUNK), b''):
                    value.update(part)
                if expected and value.hexdigest() == expected:
                    return expected
            raise ValueError('An existing destination has different content; it was not overwritten.')
        fd = os.open(source_name, flags, **source_args)
        with os.fdopen(fd, 'rb') as incoming:
            before = os.fstat(incoming.fileno())
            if not stat.S_ISREG(before.st_mode):
                raise ValueError('Only regular files can be copied.')
            output_fd = os.open(temporary_name, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600, **destination_args)
            temporary_created = True
            with os.fdopen(output_fd, 'wb') as outgoing:
                value = hashlib.sha256()
                for part in iter(lambda: incoming.read(CHUNK), b''):
                    value.update(part)
                    outgoing.write(part)
                outgoing.flush()
                os.fsync(outgoing.fileno())
            if fingerprint(before) != fingerprint(os.fstat(incoming.fileno())):
                raise ValueError('Source changed during the copy. Scan it again.')
        actual = value.hexdigest()
        if expected and actual != expected:
            raise ValueError('Source changed since the scan. Scan it again.')
        fd = os.open(temporary_name, flags, **destination_args)
        with os.fdopen(fd, 'rb') as copied:
            value = hashlib.sha256()
            for part in iter(lambda: copied.read(CHUNK), b''):
                value.update(part)
        if value.hexdigest() != actual:
            raise ValueError('The destination checksum did not match.')
        if anchored:
            os.link(temporary_name, destination_name, src_dir_fd=destination_dir, dst_dir_fd=destination_dir, follow_symlinks=False)
            os.fsync(destination_dir)
        else:
            reject_links(dst)
            os.link(pending, dst)
        return actual
    finally:
        try:
            if temporary_created and destination_dir is not None:
                os.unlink(temporary, dir_fd=destination_dir)
            elif temporary_created:
                pending.unlink(missing_ok=True)
        except FileNotFoundError:
            pass
        finally:
            for descriptor in (source_dir, destination_dir):
                if descriptor is not None:
                    os.close(descriptor)
