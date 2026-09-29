"""Conservative, offline clues from an indexed file's path; never rename or open it."""
from __future__ import annotations

import re
from pathlib import PurePosixPath

GENERIC = re.compile(r'^(?:video|movie|film|episode|ep|track|audio|book|comic|issue|scan|file|disc|disk|part|img|vid|dsc|mov)[ _.-]*\d*$|^\d{1,3}$',re.I)
SEASON = re.compile(r'^season[ ._-]*\d{1,2}$',re.I)

def clean_name(value):
    text=re.sub(r'[._]+',' ',str(value)).strip()
    return re.sub(r'\s+',' ',text)

def named_year(value):
    text=clean_name(value)
    match=re.search(r'\s*[\[(]((?:18|19|20|21)\d{2})[\])]\s*$',text)
    return (text[:match.start()].strip(),int(match.group(1))) if match else (text,None)

def path_clues(relative_path,kind,filename_title,filename_year):
    parts=PurePosixPath(relative_path).parts
    folders=list(parts[:-1]);title=filename_title;year=filename_year
    clues={'title':title,'year':year,'evidence':['file name']}
    quality_match=re.search(r'(?i)(?:\b2160p?\b|\b4k\b|\buhd\b|\b1080p?\b|\b720p?\b|\bhd\b)',relative_path)
    if quality_match:
        token=quality_match.group(0).casefold()
        clues['quality']='4K / UHD' if token in ('2160','2160p','4k','uhd') else 'HD'
    parent=folders[-1] if folders else ''
    parent_title,parent_year=named_year(parent) if parent else ('',None)
    if kind=='tv':
        episode=re.search(r'(?i)\bS(\d{1,2})[ ._-]*E(\d{1,3})(?:[ ._-]*E(\d{1,3}))?',parts[-1])
        if episode:
            clues['season']=int(episode.group(1));clues['episode']=int(episode.group(2))
            if episode.group(3):clues['episodeEnd']=int(episode.group(3))
            title=re.split(r'(?i)\bS\d{1,2}[ ._-]*E\d{1,3}',title,1)[0].strip(' ._-') or title
        show_folder=folders[-2] if parent and SEASON.match(parent) and len(folders)>1 else parent
        show_title,show_year=named_year(show_folder) if show_folder else ('',None)
        if show_title and not GENERIC.match(show_title) and (GENERIC.match(title) or title==filename_title and episode):
            title=show_title;year=show_year or year;clues['evidence'].append('show folder')
    elif kind=='music':
        album_title,album_year=named_year(parent) if parent else ('',None)
        if album_title and not GENERIC.match(album_title):
            title=album_title;year=album_year or year;clues['evidence'].append('album folder')
            if len(folders)>1 and not GENERIC.match(clean_name(folders[-2])):clues['artist']=clean_name(folders[-2]);clues['evidence'].append('artist folder')
            number_match=re.match(r'^\s*(\d{1,3})[ ._-]+',filename_title)
            if number_match:clues['trackNumber']=int(number_match.group(1))
            track=re.sub(r'^\d{1,3}[ ._-]+','',filename_title).strip()
            if track and not GENERIC.match(track):clues['trackTitle']=track
    elif kind=='book' and relative_path.casefold().endswith('.m4b'):
        clues['audioBook']=True;clues['evidence'].append('audiobook file extension')
        if parent_title and not GENERIC.match(parent_title) and re.match(r'(?i)^(?:part|chapter|disc|disk)[ ._-]*\d{1,3}(?:\b|[ ._-])',title):
            title=parent_title;year=parent_year or year;clues['evidence'].append('audiobook folder')
    elif kind in ('movie','book','comic') and parent_title and not GENERIC.match(parent_title) and GENERIC.match(title):
        title=parent_title;year=parent_year or year;clues['evidence'].append('parent folder')
    clues['title']=title;clues['year']=year
    key=''.join(char for char in title.casefold() if char.isalnum())
    if kind=='tv' and clues.get('season') is not None:key+=f":s{clues['season']:02d}"
    if kind=='music' and clues.get('artist'):key=''.join(char for char in clues['artist'].casefold() if char.isalnum())+':'+key
    clues['groupKey']=f'{kind}:{key}' if key else f'{kind}:unknown'
    return clues

def proposed_filename(relative_path,title,year,kind,clues=None):
    """Suggest a same-folder name only; this function never changes a source."""
    path=PurePosixPath(relative_path)
    clues=clues or {}
    if kind=='tv':
        if not isinstance(clues.get('season'),int) or not isinstance(clues.get('episode'),int):
            raise ValueError('Confirm the season and episode before proposing a TV filename.')
        title=f"{title} - S{clues['season']:02d}E{clues['episode']:02d}"
    elif kind=='music':
        track=clues.get('trackTitle')
        if not isinstance(track,str) or not track.strip():
            raise ValueError('Confirm the track title before proposing a music filename.')
        title=track
    elif year and kind=='movie' and not re.search(rf'\b{year}\b',title):
        title=f'{title} ({year})'
    stem=re.sub(r'[<>:"/\\|?*\x00-\x1f]',' ',title)
    stem=re.sub(r'\s+',' ',stem).strip(' .')[:180].rstrip(' .')
    if not stem or stem in ('.','..'):raise ValueError('Enter a usable title before previewing a filename.')
    return str(path.with_name(stem+path.suffix))
