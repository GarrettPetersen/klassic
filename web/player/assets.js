import {requireValue, validateCharacter, validateStory} from './runtime.js';
import {validateScene} from './staging.js';

async function bytes(url, expected) {
  const response = await fetch(url);
  requireValue(response.ok, `Could not load ${url}: HTTP ${response.status}`);
  const data = await response.arrayBuffer();
  if (expected !== undefined) {
    const hash = [...new Uint8Array(await crypto.subtle.digest('SHA-256', data))].map(v => v.toString(16).padStart(2, '0')).join('');
    requireValue(hash === expected, `Asset changed after export: ${url}`);
  }
  return data;
}
const json = async (url, hash) => JSON.parse(new TextDecoder().decode(await bytes(url, hash)));

export async function loadProject(url, progress = () => {}) {
  const base = new URL(url, location.href);
  const source=await bytes(base);const project=JSON.parse(new TextDecoder().decode(source));
  const revision=[...new Uint8Array(await crypto.subtle.digest('SHA-256',source))].map(v=>v.toString(16).padStart(2,'0')).join('');
  requireValue(project.version === 2 && project.scenes[project.initial_scene], 'Unsupported project or initial scene');
  const specs = {}, images = new Map(), audio = new Map();
  let loaded = 0;
  const tasks = [];
  const decoded=new Map();
  const bitmap=(url,hash)=>{const key=url.href+':'+hash;if(!decoded.has(key))decoded.set(key,bytes(url,hash).then(data=>createImageBitmap(new Blob([data],{type:'image/png'}))));return decoded.get(key);};
  for (const [id, entry] of Object.entries(project.characters)) {
    const characterURL = new URL(entry.file, base);
    const spec = validateCharacter(await json(characterURL, entry.sha256));
    requireValue(spec.id === id, `Character ID mismatch: ${id}`);
    specs[id] = spec;
    for (const [name, asset] of Object.entries(spec.drawings)) {
      tasks.push(async () => {
        const atlas=await bitmap(new URL(asset.file, characterURL),asset.sha256);
        if(asset.region)requireValue(asset.region[0]+asset.region[2]<=atlas.width&&asset.region[1]+asset.region[3]<=atlas.height,`Atlas region outside image: ${name}`);
        const image=asset.region?await createImageBitmap(atlas,...asset.region):atlas;
        requireValue(image.width === asset.size[0] && image.height === asset.size[1], `Drawing size changed: ${id}/${name}`);
        images.set(`${id}/${name}`, image);
      });
    }
  }
  const cast={};
  const sceneImages=[];
  for(const scene of Object.values(project.scenes)) {
    validateScene(scene,specs);
    for(const a of scene.actors){requireValue(!cast[a.id]||cast[a.id].id===a.character,'Actor identity changes between scenes');cast[a.id]=specs[a.character];}
    sceneImages.push(scene.background,...scene.furniture.flatMap(chair=>[chair.rear,chair.front]),...scene.foregrounds);
  }
  for (const asset of sceneImages) tasks.push(async () => images.set(asset.file,
    await createImageBitmap(new Blob([await bytes(new URL(asset.file, base), asset.sha256)], {type: 'image/png'}))));
  for (const [id, take] of Object.entries(project.takes)) tasks.push(async () => {
    audio.set(id, URL.createObjectURL(new Blob([await bytes(new URL(take.file, base), take.sha256)], {type: 'audio/mp4'})));
  });
  validateStory(project.story, cast, project.takes);
  // Bound decoding concurrency instead of allocating every bitmap at once.
  let next = 0;
  await Promise.all(Array.from({length: 8}, async () => {
    while (next < tasks.length) { const task = tasks[next++]; await task(); progress(++loaded, tasks.length); }
  }));
  return {project, specs, images, audio, revision};
}
