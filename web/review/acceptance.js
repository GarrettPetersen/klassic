export const subjectId=(kind,...parts)=>[kind,...parts.map(p=>encodeURIComponent(p).replace(/[!'()*]/g,c=>'%'+c.charCodeAt(0).toString(16).toUpperCase()))].join(':');
export function faceSubject(pose,overlays){return subjectId('face',pose,...Object.keys(overlays).sort().map(k=>`${k}=${overlays[k]}`));}
export function subjectFor(kind,{pose,overlays,clip,drawing,scene}){
 return kind==='face'?faceSubject(pose,overlays):subjectId(kind,{pose,clip,drawing,scene}[kind]);
}
export function statusFor(production,local,owner,subject){return local.get(owner+'/'+subject)?.decision??production?.reviews[subject]??'unreviewed';}
