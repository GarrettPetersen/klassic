import {requireValue} from './runtime.js';

export class DrawingRenderer {
  constructor(canvas, scene, images) {
    this.canvas = canvas; this.context = canvas.getContext('2d'); this.scene = scene; this.images = images;
    requireValue(this.context, 'Canvas rendering is unavailable');
    [canvas.width, canvas.height] = scene.size;
  }
  render(snapshots, at, {smoke = true, background='scene', silhouette=false, anchors=false, contacts=false} = {}) {
    if(this.canvas.width!==this.scene.size[0]||this.canvas.height!==this.scene.size[1])[this.canvas.width,this.canvas.height]=this.scene.size;
    const ctx = this.context;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    const calls = [{...this.scene.background, image: this.scene.background.file, position: [0, 0], scale: 1, z: -100}];
    for (const chair of this.scene.furniture) {
      calls.push({...chair.rear, image: chair.rear.file, scale: 1});
      calls.push({...chair.front, image: chair.front.file, scale: 1});
    }
    for (const foreground of this.scene.foregrounds ?? []) calls.push({...foreground, image: foreground.file, scale: 1});
    for (const snapshot of snapshots) calls.push(...snapshot.layers);
    if(background!=='scene'){
      if(!['white','checker','dark'].includes(background))throw new Error('Unknown review background');
      ctx.fillStyle=background==='dark'?'#435d73':'#fff';ctx.fillRect(0,0,this.canvas.width,this.canvas.height);
      if(background==='checker'){ctx.fillStyle='#dce3ea';for(let y=0;y<this.canvas.height;y+=24)for(let x=0;x<this.canvas.width;x+=24)if((x/24+y/24)%2)ctx.fillRect(x,y,24,24);}
      for(let i=calls.length-1;i>=0;i--)if(!calls[i].id)calls.splice(i,1);
    }
    calls.sort((a, b) => a.z - b.z);
    for (const call of calls) {
      const image = this.images.get(call.image);
      requireValue(image, `Missing decoded drawing ${call.image}`);
      if(silhouette&&call.id)ctx.filter='brightness(0)';
      if (call.degrees) {
        ctx.save(); ctx.translate(...call.position); ctx.rotate(call.degrees * Math.PI / 180);
        ctx.drawImage(image, 0, 0, image.width * call.scale, image.height * call.scale); ctx.restore();
      } else ctx.drawImage(image, call.position[0], call.position[1], image.width * call.scale, image.height * call.scale);
      if(silhouette&&call.id)ctx.filter='none';
    }
    if (smoke) snapshots.forEach((snapshot, index) => {
      const tip = snapshot.attachments.cigarette;
      if (!tip) return; // A prop-free pose deliberately has no smoke attachment.
      ctx.strokeStyle = 'rgba(230,230,230,.25)'; ctx.lineWidth = 2;
      ctx.beginPath();
      for (let i = 0; i < 36; i++) {
        const rise = i / 35;
        const x = tip[0] + Math.sin(rise * 8 - at * 1.5 + index * 2) * (4 + rise * 14) + rise * 8;
        const y = tip[1] - rise * 160;
        if (i === 0) ctx.moveTo(x, y); else ctx.lineTo(x, y);
      }
      ctx.stroke();
    });
    if(anchors||contacts){ctx.save();ctx.font='14px system-ui';ctx.lineWidth=2;
      for(const snapshot of snapshots){
        if(anchors)for(const [name,p]of Object.entries(snapshot.anchors)){ctx.strokeStyle='#257fc0';ctx.fillStyle='#16456b';ctx.beginPath();ctx.moveTo(p[0]-7,p[1]);ctx.lineTo(p[0]+7,p[1]);ctx.moveTo(p[0],p[1]-7);ctx.lineTo(p[0],p[1]+7);ctx.stroke();ctx.fillText(name,p[0]+10,p[1]-8);}
        if(contacts)for(const c of snapshot.contacts){ctx.strokeStyle=c.locked?'#df7b00':'#a94b86';ctx.fillStyle=ctx.strokeStyle;ctx.beginPath();ctx.arc(...c.point,7,0,Math.PI*2);ctx.stroke();ctx.fillText(c.id+(c.locked?' • contact':''),c.point[0]+10,c.point[1]+17);}
      }ctx.restore();}
    return calls;
  }
}
