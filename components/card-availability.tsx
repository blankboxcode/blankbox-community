import {itemCardCounts} from '@/lib/item-presentation';
import {kindNames,type MediaItem} from '@/lib/media';

export function CardAvailability({item}:{item:MediaItem}) {
  const counts=itemCardCounts(item);
  const date=item.year||kindNames[item.kind];
  const sourceLabel=counts?.sources===1?'Source':'Sources';
  const editionLabel=counts?.editions===1?'Edition':'Editions';
  const text=`${date} · ${counts?.sources??'…'} ${sourceLabel} · ${counts?.editions??'…'} ${editionLabel}`;
  return <span className="card-availability" title={text}><span className="sr-only">{text}</span><span className="card-counts-row" aria-hidden="true"><span className="card-date">{date}</span><i>·</i><span>{counts?.sources??'…'} <span className="card-count-full">{sourceLabel}</span><abbr className="card-count-short" title={sourceLabel}>Src</abbr></span><i>·</i><span>{counts?.editions??'…'} <span className="card-count-full">{editionLabel}</span><abbr className="card-count-short" title={editionLabel}>{counts?.editions===1?'Ed':'Eds'}</abbr></span></span></span>;
}
