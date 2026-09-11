import {requireValue, validateCharacter, validateStory} from './runtime.js';

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
  const project = await json(base);
  requireValue(project.version === 1, 'Unsupported project version');
  const specs = {}, images = new Map(), audio = new Map();
  let loaded = 0;
  const tasks = [];
  for (const [id, entry] of Object.entries(project.characters)) {
    const characterURL = new URL(entry.file, base);
    const spec = validateCharacter(await json(characterURL, entry.sha256));
    requireValue(spec.id === id, `Character ID mismatch: ${id}`);
    specs[id] = spec;
    for (const [name, asset] of Object.entries(spec.drawings)) {
      tasks.push(async () => {
        const data = await bytes(new URL(asset.file, characterURL), asset.sha256);
        const image = await createImageBitmap(new Blob([data], {type: 'image/png'}));
        requireValue(image.width === asset.size[0] && image.height === asset.size[1], `Drawing size changed: ${id}/${name}`);
        images.set(`${id}/${name}`, image);
      });
    }
  }
  const scene = project.scene;
  requireValue(scene.version === 1 && scene.size.length === 2 && scene.size.every(n => Number.isInteger(n) && n > 0), 'Invalid scene');
  const ids = scene.actors.map(a => a.id);
  requireValue(new Set(ids).size === ids.length && ids.length > 0, 'Duplicate or missing scene actors');
  const cast = Object.fromEntries(scene.actors.map(a => {
    requireValue(specs[a.character], `Missing character for actor ${a.id}`);
    return [a.id, specs[a.character]];
  }));
  for (const chair of scene.furniture) requireValue(ids.includes(chair.seat), `Unknown seat occupant ${chair.seat}`);
  const sceneImages = [scene.background, ...scene.furniture.flatMap(chair => [chair.rear, chair.front]), ...(scene.foregrounds ?? [])];
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
  return {project, specs, images, audio};
}
