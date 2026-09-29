"""Periodic metadata-only discovery. No automatic media or identity writes."""
import json
import os
import stat
import time
import uuid
from pathlib import Path
from local_clues import path_clues


def monitor_source(box, source_id):
    from server import Problem, inferred_title, inventory_title_key, kind_for, now, inside, fingerprint
    root=box.source_roots.get(source_id)
    if not root or not root.is_dir():raise Problem('The monitored source is unavailable. Its catalog links remain intact.',409)
    details=root.stat();identity=f'{details.st_dev}:{details.st_ino}'
    with box.db() as db:
        previous=db.execute('SELECT * FROM inventory_batches WHERE source_id=? ORDER BY started_at DESC,rowid DESC LIMIT 1',(source_id,)).fetchone()
    if previous and previous['root_identity']!=identity:
        raise Problem('The monitored drive identity changed. Review the drive and run Index source before monitoring resumes.',409)
    batch_id=previous['id'] if previous else uuid.uuid4().hex
    copy_discovery=box.get_settings().get('autoFolderCopy',False)

    def worker(job):
        added=changed=waiting=seen=0;errors=[];observed_at=time.time()
        with box.db() as db:
            if not previous:db.execute('INSERT INTO inventory_batches(id,source_id,source_path,root_identity,status,started_at) VALUES(?,?,?,?,?,?)',(batch_id,source_id,str(root),identity,'complete',now()))
            db.execute('CREATE TEMP TABLE observed_paths(path TEXT PRIMARY KEY)')
            pending=[]
            def flush():
                nonlocal added,changed,waiting
                # Each chunk commits while the previous visible inventory stays
                # usable. Deletions require a complete, error-free traversal.
                for relative,details in pending:
                    db.execute('INSERT INTO observed_paths VALUES(?)',(relative,))
                    kind=kind_for(relative)
                    if copy_discovery and kind in ('photo','home-video','file') and Path(relative).suffix.casefold() not in ('.nfo','.srt','.ass','.ssa','.sub','.idx','.sfv','.md5','.sha256'):
                        observed=json.dumps(fingerprint(details))
                        candidate=db.execute('SELECT fingerprint,status FROM auto_copy_candidates WHERE source_id=? AND relative_path=?',(source_id,relative)).fetchone()
                        status=('pending' if candidate and candidate['fingerprint']==observed and candidate['status']=='waiting' else candidate['status'] if candidate and candidate['fingerprint']==observed and candidate['status'] in ('pending','handled') else 'waiting')
                        db.execute('INSERT INTO auto_copy_candidates VALUES(?,?,?,?,?,?,?) ON CONFLICT(source_id,relative_path) DO UPDATE SET fingerprint=excluded.fingerprint,bytes=excluded.bytes,kind=excluded.kind,status=excluded.status,discovered_at=excluded.discovered_at',(source_id,relative,observed,details.st_size,kind,status,now()))
                    old=db.execute('SELECT bytes,mtime_ns FROM inventory_files WHERE batch_id=? AND relative_path=?',(batch_id,relative)).fetchone()
                    if old and (old['bytes'],old['mtime_ns'])==(details.st_size,details.st_mtime_ns):
                        db.execute('DELETE FROM monitored_files WHERE source_id=? AND path=?',(source_id,relative));continue
                    observation=db.execute('SELECT * FROM monitored_files WHERE source_id=? AND path=?',(source_id,relative)).fetchone()
                    stable=observation and observation['root_identity']==identity and observation['bytes']==details.st_size and observation['mtime_ns']==details.st_mtime_ns and observed_at-observation['seen_at']>=60
                    if not stable:
                        if not observation or (observation['root_identity'],observation['bytes'],observation['mtime_ns'])!=(identity,details.st_size,details.st_mtime_ns):
                            db.execute('INSERT INTO monitored_files VALUES(?,?,?,?,?,?) ON CONFLICT(source_id,path) DO UPDATE SET root_identity=excluded.root_identity,bytes=excluded.bytes,mtime_ns=excluded.mtime_ns,seen_at=excluded.seen_at',(source_id,relative,identity,details.st_size,details.st_mtime_ns,observed_at))
                        waiting+=1;continue
                    title,year=inferred_title(Path(relative).name);clues=path_clues(relative,kind,title,year)
                    values=(batch_id,relative,kind,clues['title'],inventory_title_key(clues['title']),clues['year'],details.st_size,details.st_mtime_ns,json.dumps(clues),clues['groupKey'])
                    db.execute('INSERT INTO inventory_files(batch_id,relative_path,kind,title,title_key,year,bytes,mtime_ns,clues,group_key) VALUES(?,?,?,?,?,?,?,?,?,?) ON CONFLICT(batch_id,relative_path) DO UPDATE SET kind=excluded.kind,title=excluded.title,title_key=excluded.title_key,year=excluded.year,bytes=excluded.bytes,mtime_ns=excluded.mtime_ns,clues=excluded.clues,group_key=excluded.group_key',values)
                    db.execute('DELETE FROM monitored_files WHERE source_id=? AND path=?',(source_id,relative))
                    if old:changed+=1
                    else:added+=1
                db.commit();pending.clear()
                job.update(done=seen,added=added,changed=changed,waiting=waiting,message=f'{seen} file entries checked · {added} new · {changed} changed · {waiting} waiting for stability')
                box.save_job(job)
            def walk_error(error):
                if len(errors)<20:errors.append(str(error))
            try:
                for folder,dirs,files in os.walk(root,followlinks=False,onerror=walk_error):
                    if not inside(Path(folder).resolve(),root):dirs.clear();continue
                    dirs[:]=[name for name in dirs if not name.startswith('.') and not (Path(folder)/name).is_symlink()]
                    for name in files:
                        if name.startswith('.'):continue
                        path=Path(folder)/name
                        try:
                            details=path.stat(follow_symlinks=False)
                            if not stat.S_ISREG(details.st_mode):continue
                            pending.append((path.relative_to(root).as_posix(),details));seen+=1
                            if seen>1000000:raise Problem('This source exceeds 1,000,000 entries. Configure smaller folders.')
                            if len(pending)>=250:flush()
                        except OSError as error:walk_error(error)
                flush()
                final=root.stat()
                if not root.is_dir() or f'{final.st_dev}:{final.st_ino}'!=identity:raise Problem('The drive disconnected or changed during monitoring. Previous catalog links remain intact.',409)
                removed=0
                if not errors:
                    removed=db.execute('DELETE FROM inventory_files WHERE batch_id=? AND relative_path NOT IN (SELECT path FROM observed_paths)',(batch_id,)).rowcount
                    db.execute('DELETE FROM monitored_files WHERE source_id=? AND path NOT IN (SELECT path FROM observed_paths)',(source_id,))
                    if copy_discovery:db.execute("UPDATE auto_copy_candidates SET status='missing' WHERE source_id=? AND status NOT IN ('handled','missing') AND relative_path NOT IN (SELECT path FROM observed_paths)",(source_id,))
                totals=db.execute('SELECT COUNT(*),COALESCE(SUM(bytes),0) FROM inventory_files WHERE batch_id=?',(batch_id,)).fetchone()
                db.execute('UPDATE inventory_batches SET status=?,finished_at=?,scanned=?,total_bytes=?,errors=? WHERE id=?',('partial' if errors else 'complete',now(),*totals,json.dumps(errors),batch_id))
                db.commit()
                job.update(removed=removed,errors=errors,message=f'{added} new and {changed} changed files ready for review · {waiting} waiting for stability · {removed} missing entries; catalog links retained')
            except Exception:
                db.rollback()
                raise
    return {**box.start_job('source-monitor',worker),'batchId':batch_id}
