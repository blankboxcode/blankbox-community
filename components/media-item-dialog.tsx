'use client';

import type {ComponentProps} from 'react';
import {MediaItemPage} from '@/components/media-item-page';
import {Dialog,DialogContent,DialogDescription,DialogTitle} from '@/components/ui/dialog';

export function MediaItemDialog(props:ComponentProps<typeof MediaItemPage>) {
  return <Dialog open onOpenChange={open=>{if(!open)props.onBack();}}>
    <DialogContent className="media-item-dialog" onOpenAutoFocus={event=>{
      event.preventDefault();
      document.getElementById('media-item-title')?.focus({preventScroll:true});
    }} onCloseAutoFocus={event=>event.preventDefault()}>
      <div className="media-item-dialog-header">
        <span>Item details</span>
        <DialogTitle className="sr-only">{props.item.title}</DialogTitle>
        <DialogDescription className="sr-only">Artwork, editions, playback and saved details. Close to return to your library.</DialogDescription>
      </div>
      <div className="media-item-dialog-scroll"><MediaItemPage {...props}/></div>
    </DialogContent>
  </Dialog>;
}
