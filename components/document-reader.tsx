'use client';
/* eslint-disable @next/next/no-img-element -- Comic and EPUB images are private authenticated media. */

import { useEffect, useRef, useState } from 'react';
import { BookOpen, ChevronLeft, ChevronRight, Maximize2, Minimize2, Moon, Sun } from 'lucide-react';
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import type { MediaItem, MediaSource, ReaderFormat } from '@/lib/media';
type ReaderManifest = { format: 'epub' | 'cbz'; total: number; chapters: { title: string }[] };
type ReaderBlock = { kind: string; text?: string; asset?: number; alt?: string };
type ReaderChapter = { title: string; blocks: ReaderBlock[] };

export function DocumentReader({ item, source, url, format, onClose, onProgress }: {
  item: MediaItem; source: MediaSource; url: string; format: ReaderFormat;
  onClose: () => void; onProgress: (progress: number) => void;
}) {
  const [manifest, setManifest] = useState<ReaderManifest | null>(null);
  const [chapter, setChapter] = useState<ReaderChapter | null>(null);
  const [error, setError] = useState('');
  const [index, setIndex] = useState(0);
  const [page, setPage] = useState(0);
  const [pageCount, setPageCount] = useState(1);
  const [fontSize, setFontSize] = useState(18);
  const [light, setLight] = useState(false);
  const [fitWidth, setFitWidth] = useState(true);
  const [finished, setFinished] = useState((item.progress || 0) >= 1);
  const bodyRef = useRef<HTMLDivElement>(null);
  const articleRef = useRef<HTMLElement>(null);
  const pageRef = useRef(0);
  const resumeFractionRef = useRef<number | null>(null);
  const previousChapterEndRef = useRef(false);
  const base = `/api/reader/${encodeURIComponent(item.id)}/${encodeURIComponent(source.id || '')}`;

  useEffect(() => {
    if (format === 'pdf') return;
    const controller = new AbortController();
    fetch(base, { cache: 'no-store', signal: controller.signal })
      .then(async response => {
        const value = await response.json() as ReaderManifest & { error?: string };
        if (!response.ok) throw new Error(value.error || 'This file could not be opened.');
        return value as ReaderManifest;
      })
      .then(value => {
        if (!value.total || value.format !== format) throw new Error('This file has no readable pages.');
        setManifest(value);
        const position = Math.max(0, Math.min(value.total, (item.progress || 0) * value.total));
        const chapterIndex = Math.min(value.total - 1, Math.floor(position));
        resumeFractionRef.current = format === 'epub' ? position - chapterIndex : null;
        setIndex(chapterIndex);
      })
      .catch(reason => { if (reason.name !== 'AbortError') setError(reason.message); });
    return () => controller.abort();
  }, [base, format, item.progress]);

  useEffect(() => {
    if (format !== 'epub' || !manifest) return;
    const controller = new AbortController();
    fetch(`${base}/chapter/${index}`, { cache: 'no-store', signal: controller.signal })
      .then(async response => {
        const value = await response.json() as ReaderChapter & { error?: string };
        if (!response.ok) throw new Error(value.error || 'This chapter could not be opened.');
        return value as ReaderChapter;
      })
      .then(value => { setChapter(value); setError(''); setPage(0); setPageCount(1); pageRef.current = 0; bodyRef.current?.scrollTo(0, 0); })
      .catch(reason => { if (reason.name !== 'AbortError') setError(reason.message); });
    return () => controller.abort();
  }, [base, format, index, manifest]);

  useEffect(() => {
    if (format !== 'epub' || !chapter) return;
    const body = bodyRef.current, article = articleRef.current;
    if (!body || !article) return;
    const measure = () => {
      const width = body.clientWidth;
      if (!width) return;
      const count = Math.max(1, Math.ceil((Math.max(body.scrollWidth, article.scrollWidth) - 1) / width));
      let next = Math.min(pageRef.current, count - 1);
      const landedAtPreviousChapterEnd = previousChapterEndRef.current;
      if (landedAtPreviousChapterEnd) { next = count - 1; previousChapterEndRef.current = false; }
      else if (resumeFractionRef.current !== null) { next = Math.min(count - 1, Math.floor(resumeFractionRef.current * count)); resumeFractionRef.current = null; }
      pageRef.current = next;
      setPage(next);
      setPageCount(count);
      body.scrollLeft = next * width;
      if (landedAtPreviousChapterEnd && manifest) onProgress((index + next / count) / manifest.total);
    };
    const frame = requestAnimationFrame(measure);
    const observer = new ResizeObserver(measure);
    observer.observe(body);
    observer.observe(article);
    const images = [...article.querySelectorAll('img')];
    images.forEach(image => image.addEventListener('load', measure));
    return () => { cancelAnimationFrame(frame); observer.disconnect(); images.forEach(image => image.removeEventListener('load', measure)); };
  }, [chapter, fontSize, format, index, manifest, onProgress]);

  const showPage = (next: number) => {
    if (!manifest) return;
    const clamped = Math.max(0, Math.min(next, pageCount - 1));
    pageRef.current = clamped;
    setPage(clamped);
    bodyRef.current?.scrollTo({ left: clamped * (bodyRef.current?.clientWidth || 0), top: 0 });
    setFinished(false);
    onProgress((index + clamped / pageCount) / manifest.total);
  };
  const jumpChapter = (next: number, fromPrevious = false) => {
    if (!manifest || next < 0 || next >= manifest.total) return;
    previousChapterEndRef.current = fromPrevious;
    resumeFractionRef.current = null;
    setChapter(null);
    setPage(0);
    setPageCount(1);
    pageRef.current = 0;
    setIndex(next);
    setFinished(false);
    onProgress(next / manifest.total);
    bodyRef.current?.scrollTo(0, 0);
  };
  const turn = (direction: -1 | 1) => {
    if (!manifest) return;
    if (format === 'epub') {
      if (direction < 0 && page > 0) showPage(page - 1);
      else if (direction > 0 && page < pageCount - 1) showPage(page + 1);
      else jumpChapter(index + direction, direction < 0);
    } else {
      const next = index + direction;
      if (next >= 0 && next < manifest.total) { setIndex(next); setFinished(false); onProgress(next / manifest.total); }
    }
  };
  const atStart = !manifest || index === 0 && (format !== 'epub' || page === 0);
  const atEnd = !manifest || index === manifest.total - 1 && (format !== 'epub' || page === pageCount - 1);

  return <Dialog open onOpenChange={open => { if (!open) onClose(); }}><DialogContent className={`document-reader-dialog ${light ? 'reader-light' : ''}`}>
    <DialogHeader><DialogTitle>{item.title}</DialogTitle><DialogDescription>{format === 'pdf' ? 'PDF reader. Use your browser controls to search, zoom, or print.' : format === 'cbz' ? 'Comic reader' : 'Book reader'}</DialogDescription></DialogHeader>
    {format === 'pdf' ? <iframe className="document-reader-pdf" src={url} title={`Read ${item.title}`} /> : <>
      <div className="document-reader-toolbar">
        <div className="document-reader-pages"><button className="subtle-button icon-only" aria-label="Previous page" disabled={atStart} onClick={() => turn(-1)}><ChevronLeft size={18} /></button>
          {format === 'epub' && manifest ? <><select aria-label="Chapter" value={index} onChange={event => jumpChapter(Number(event.target.value))}>{manifest.chapters.map((entry, chapterIndex) => <option key={chapterIndex} value={chapterIndex}>{entry.title}</option>)}</select><span>Page {page + 1} of {pageCount}</span></> : <span>{manifest ? `Page ${index + 1} of ${manifest.total}` : 'Opening…'}</span>}
          <button className="subtle-button icon-only" aria-label="Next page" disabled={atEnd} onClick={() => turn(1)}><ChevronRight size={18} /></button></div>
        {format === 'epub' ? <div className="document-reader-controls"><button className="subtle-button" onClick={() => setFontSize(size => Math.max(14, size - 2))} aria-label="Decrease text size">A−</button><button className="subtle-button" onClick={() => setFontSize(size => Math.min(28, size + 2))} aria-label="Increase text size">A+</button><button className="subtle-button icon-only" onClick={() => setLight(value => !value)} aria-label={light ? 'Use dark pages' : 'Use light pages'}>{light ? <Moon size={16} /> : <Sun size={16} />}</button></div> : <button className="subtle-button icon-only" onClick={() => setFitWidth(value => !value)} aria-label={fitWidth ? 'Show comic at natural size' : 'Fit comic to width'}>{fitWidth ? <Maximize2 size={17} /> : <Minimize2 size={17} />}</button>}
      </div>
      <div className={`document-reader-body ${format === 'epub' ? 'epub-paged' : ''}`} ref={bodyRef} tabIndex={0} aria-label={format === 'cbz' ? 'Comic pages. Use left and right arrow keys to turn pages.' : 'Book text. Use left and right arrow keys to turn pages.'} onKeyDown={event => { if (event.key === 'ArrowLeft') { event.preventDefault(); turn(-1); } else if (event.key === 'ArrowRight') { event.preventDefault(); turn(1); } }}>
        {error ? <div className="document-reader-message"><BookOpen size={26} /><p>{error}</p><a className="text-button" href={url} target="_blank" rel="noopener noreferrer">Open original file</a></div> : !manifest ? <div className="document-reader-message">Opening your file…</div> : format === 'cbz' ? <img className={`document-reader-comic ${fitWidth ? 'fit-width' : ''}`} src={`${base}/asset/${index}`} alt={`Page ${index + 1} of ${manifest.total}`} onError={() => setError('This comic page could not be displayed.')} /> : chapter ? <article className="document-reader-chapter" ref={articleRef} style={{ fontSize }}><h2>{chapter.title}</h2>{chapter.blocks.map((block, position) => block.kind === 'image' && block.asset !== undefined ? <img key={position} src={`${base}/asset/${block.asset}`} alt={block.alt || ''} /> : /^h[1-6]$/.test(block.kind) ? <h3 key={position}>{block.text}</h3> : block.kind === 'blockquote' ? <blockquote key={position}>{block.text}</blockquote> : block.kind === 'pre' ? <pre key={position}>{block.text}</pre> : block.kind === 'li' ? <p className="document-reader-list" key={position}>• {block.text}</p> : <p key={position}>{block.text}</p>)}</article> : <div className="document-reader-message">Opening chapter…</div>}
      </div>
      <div className="document-reader-footer"><span>{manifest ? format === 'epub' ? `Chapter ${index + 1} of ${manifest.total} · Page ${page + 1} of ${pageCount}` : `${index + 1} / ${manifest.total}` : ''}</span><div>{manifest && atEnd && !finished && <button className="text-button" onClick={() => { setFinished(true); onProgress(1); }}>Mark finished</button>}<a href={url} target="_blank" rel="noopener noreferrer">Open original file</a></div></div>
    </>}
  </DialogContent></Dialog>;
}
