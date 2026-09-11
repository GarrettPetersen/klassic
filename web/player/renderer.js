import {requireValue} from './runtime.js';

export class DrawingRenderer {
  constructor(canvas, scene, images) {
    this.canvas = canvas; this.context = canvas.getContext('2d'); this.scene = scene; this.images = images;
    requireValue(this.context, 'Canvas rendering is unavailable');
    [canvas.width, canvas.height] = scene.size;
  }
  render(snapshots, at, {smoke = true} = {}) {
    const ctx = this.context;
    ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
    const calls = [{...this.scene.background, image: this.scene.background.file, position: [0, 0], scale: 1, z: -100}];
    for (const chair of this.scene.furniture) {
      calls.push({...chair.rear, image: chair.rear.file, scale: 1});
      calls.push({...chair.front, image: chair.front.file, scale: 1});
    }
    for (const foreground of this.scene.foregrounds ?? []) calls.push({...foreground, image: foreground.file, scale: 1});
    for (const snapshot of snapshots) calls.push(...snapshot.layers);
    calls.sort((a, b) => a.z - b.z);
    for (const call of calls) {
      const image = this.images.get(call.image);
      requireValue(image, `Missing decoded drawing ${call.image}`);
      if (call.degrees) {
        ctx.save(); ctx.translate(...call.position); ctx.rotate(call.degrees * Math.PI / 180);
        ctx.drawImage(image, 0, 0, image.width * call.scale, image.height * call.scale); ctx.restore();
      } else ctx.drawImage(image, call.position[0], call.position[1], image.width * call.scale, image.height * call.scale);
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
    return calls;
  }
}
