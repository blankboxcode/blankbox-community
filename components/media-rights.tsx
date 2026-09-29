'use client';

export function MediaRightsChoice({accepted,onChange}:{accepted:boolean;onChange:(accepted:boolean)=>void}){
 return <section className="media-rights-choice"><h3>Your media, your responsibility</h3><p>Blank Box is designed to organize and play media and files you own or otherwise have permission to use. Blank Box does not provide copyrighted media or verify ownership of imported content.</p><label className="setup-tip-choice"><input type="checkbox" checked={accepted} onChange={event=>onChange(event.target.checked)}/><span>I understand and confirm that I have the necessary rights or permission to use content I add to Blank Box.</span></label></section>;
}
