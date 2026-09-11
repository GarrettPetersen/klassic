// Saved drawings are the animation. This module never deforms or blends them.
export function requireValue(condition, message) {
  if (!condition) throw new Error(message);
}
const finitePoint = p => Array.isArray(p) && p.length === 2 && p.every(Number.isFinite);
const add = (a,b) => a.map((v,i)=>v+b[i]);

export function transformPoint(point, transform) {
  if (!transform) return [...point];
  const angle = transform.degrees * Math.PI / 180;
  const x = point[0] - transform.origin[0], y = point[1] - transform.origin[1];
  return [transform.position[0] + x * Math.cos(angle) - y * Math.sin(angle),
    transform.position[1] + x * Math.sin(angle) + y * Math.cos(angle)];
}

export function validateCharacter(spec) {
  requireValue(spec.version === 1 && typeof spec.id === 'string', 'Invalid character package');
  requireValue(finitePoint(spec.origin), `${spec.id}: missing local origin`);
  requireValue(Number.isInteger(spec.fps) && spec.fps > 0, `${spec.id}: invalid frame rate`);
  requireValue(spec.states[spec.initial_state], `${spec.id}: missing initial state`);
  requireValue(spec.activities && Object.keys(spec.activities).length, `${spec.id}: missing activities`);
  for (const [name, activity] of Object.entries(spec.activities)) {
    requireValue(typeof activity.label === 'string' && Array.isArray(activity.views) && activity.views.length && new Set(activity.views).size === activity.views.length, `${name}: invalid activity views`);
  }
  for (const [name, drawing] of Object.entries(spec.drawings)) {
    requireValue(typeof drawing.file === 'string' && /^[a-f0-9]{64}$/.test(drawing.sha256), `${spec.id}/${name}: invalid drawing provenance`);
    requireValue(finitePoint(drawing.position), `${spec.id}/${name}: invalid local position`);
    requireValue(Array.isArray(drawing.size) && drawing.size.length===2 && drawing.size.every(n=>Number.isInteger(n)&&n>0), `${name}: invalid drawing size`);
    if (drawing.region) requireValue(drawing.region.length===4 && drawing.region.every(n=>Number.isInteger(n)&&n>=0) && drawing.region[2]===drawing.size[0] && drawing.region[3]===drawing.size[1], `${name}: invalid atlas region`);
  }
  for (const [name, pose] of Object.entries(spec.poses)) {
    requireValue(Array.isArray(pose.layers) && pose.layers.length, `${spec.id}/${name}: empty pose`);
    for (const layer of pose.layers) {
      requireValue(spec.drawings[layer.drawing] && Number.isFinite(layer.z), `${spec.id}/${name}: unknown drawing or depth`);
      if (layer.transform) requireValue(finitePoint(layer.transform.origin) && finitePoint(layer.transform.position) && Number.isFinite(layer.transform.degrees), `${spec.id}/${name}: invalid rigid placement`);
    }
    requireValue(pose.attachments && Object.values(pose.attachments).every(finitePoint), `${spec.id}/${name}: invalid attachments`);
    requireValue(pose.anchors && Object.values(pose.anchors).every(finitePoint), `${spec.id}/${name}: invalid anchors`);
    requireValue(Array.isArray(pose.contacts) && new Set(pose.contacts.map(c=>c.id)).size===pose.contacts.length, `${name}: invalid contacts`);
    for (const c of pose.contacts) requireValue(typeof c.id==='string' && ['foot','seat','hand'].includes(c.kind) && finitePoint(c.point) && typeof c.locked==='boolean', `${name}: invalid contact`);
    if (pose.overlay_offsets) for (const [overlay, offset] of Object.entries(pose.overlay_offsets)) {
      requireValue(spec.overlays[overlay] && finitePoint(offset), `${spec.id}/${name}: invalid face placement`);
    }
  }
  for (const [name, action] of Object.entries(spec.actions)) {
    requireValue(spec.states[action.from] && spec.states[action.to], `${spec.id}/${name}: unknown state`);
    const capability=action.capability ?? spec.states[action.from];
    requireValue(spec.activities[capability.activity]?.views.includes(capability.view), `${name}: unsupported action activity/view`);
    requireValue(typeof action.loop === 'boolean' && action.frames.length > 0, `${spec.id}/${name}: invalid clip`);
    requireValue(!action.loop || action.from === action.to, `${spec.id}/${name}: loop must retain state`);
    for (const frame of action.frames) {
      requireValue(spec.poses[frame.pose] && Number.isInteger(frame.ticks) && frame.ticks > 0, `${spec.id}/${name}: missing pose or invalid duration`);
    }
    if(action.navigation)requireValue(typeof action.navigation.family==='string'&&['stride','step','stop','approach','turn'].includes(action.navigation.kind),`${name}: invalid movement option`);
    if (action.motion) {
      requireValue(finitePoint(action.motion.displacement) && action.motion.roots?.length===action.frames.length && action.motion.roots.every(finitePoint), `${name}: invalid root motion`);
      requireValue(action.motion.roots[0].every(v=>v===0), `${name}: motion must start at zero`);
      if(!action.loop)requireValue(action.motion.roots.at(-1).every((v,i)=>v===action.motion.displacement[i]),`${name}: final drawing must meet the exit root`);
    }
    if (!action.loop) {
      requireValue(action.frames[0].pose === spec.states[action.from].pose && action.frames.at(-1).pose === spec.states[action.to].pose, `${spec.id}/${name}: clip must connect its entry and exit poses`);
    }
  }
  for (const [name, state] of Object.entries(spec.states)) {
    requireValue(spec.activities[state.activity]?.views.includes(state.view), `${name}: unsupported activity/view`);
    const idle = spec.actions[state.idle];
    requireValue(spec.poses[state.pose] && idle?.loop && idle.from === name && idle.frames[0].pose === state.pose, `${spec.id}/${name}: invalid idle action`);
  }
  for (const overlay of Object.values(spec.overlays)) {
    requireValue(Number.isFinite(overlay.z), `${spec.id}: invalid overlay depth`);
    for (const id of Object.values(overlay.drawings)) requireValue(spec.drawings[id], `${spec.id}: missing overlay drawing ${id}`);
  }
  return spec;
}

export function sampleClip(action, fps, elapsed) {
  requireValue(Number.isFinite(elapsed) && elapsed >= 0, 'Clip time must be finite and nonnegative');
  const total = action.frames.reduce((n, f) => n + f.ticks, 0);
  const ticks = Math.floor(elapsed * fps + 1e-7);
  let local = action.loop ? ticks % total : Math.min(ticks, total - 1);
  for (let i = 0; i < action.frames.length; i++) {
    const frame = action.frames[i];
    if (local < frame.ticks) return {pose: frame.pose, frame: i, tick: ticks, cycles: action.loop ? Math.floor(ticks/total) : 0, done: !action.loop && elapsed >= total / fps, duration: total / fps};
    local -= frame.ticks;
  }
  throw new Error('Clip frame could not be sampled');
}

export class Actor {
  constructor(spec, placement) {
    this.spec = validateCharacter(spec);
    requireValue(finitePoint(placement.position) && Number.isFinite(placement.scale) && placement.scale > 0 && Number.isFinite(placement.z), 'Invalid actor placement');
    this.placement = structuredClone(placement);
    this.state = placement.state ?? spec.initial_state;
    requireValue(spec.states[this.state], 'Unknown initial placement state');
    this.current = spec.states[this.state].idle;
    this.started = 0;
    this.pending = null;
    this.lastTime = 0;
  }
  advance(now) {
    requireValue(Number.isFinite(now) && now >= this.lastTime, 'Actor clock must be monotonic');
    this.lastTime = now;
    const action = this.spec.actions[this.current];
    const sample = sampleClip(action, this.spec.fps, now - this.started);
    if (!sample.done) return sample;
    const ended = this.started + sample.duration;
    if (action.motion) this.placement.position=add(this.placement.position,action.motion.displacement.map(v=>v*this.placement.scale));
    this.state = action.to;
    const next = this.pending ?? this.spec.states[this.state].idle;
    this.pending = null;
    requireValue(this.spec.actions[next].from === this.state, `Action ${next} cannot start in ${this.state}`);
    this.current = next;
    this.started = ended;
    return this.advance(now);
  }
  request(name, now) {
    const sample=this.advance(now);
    const target = this.spec.actions[name];
    requireValue(target, `Unknown action ${name} for ${this.spec.id}`);
    const current = this.spec.actions[this.current];
    const nextState = current.loop ? this.state : current.to;
    requireValue(target.from === nextState, `Action ${name} requires ${target.from}, actor will be ${nextState}`);
    if (current.loop) {
      this.placement.position=add(this.placement.position,this.motionOffset(sample).map(v=>v*this.placement.scale));
      this.current = name; this.started = now;
    }
    else this.pending = name; // Finish the drawn recovery before another action.
  }
  availableActions(now) {
    this.advance(now);
    const state = this.spec.actions[this.current].to;
    return Object.entries(this.spec.actions).filter(([, action]) => !action.loop && action.from === state);
  }
  requestIntent(intent, now) {
    const matches = this.availableActions(now).filter(([, action]) => action.intent === intent);
    requireValue(matches.length === 1, `Expected one ${intent} action from current posture, found ${matches.length}`);
    this.request(matches[0][0], now);
  }
  settle(now) {
    this.advance(now);
    this.pending = null; // Speech may stop immediately; the short gesture completes.
  }
  motionOffset(sample) {
    const motion=this.spec.actions[this.current].motion;
    return motion ? add(motion.roots[sample.frame],motion.displacement.map(v=>v*sample.cycles)) : [0,0];
  }
  save(now) {
    this.advance(now);
    return {state:this.state,current:this.current,started:this.started,pending:this.pending,lastTime:this.lastTime,placement:structuredClone(this.placement)};
  }
  static restore(spec,data,now) {
    const actor=new Actor(spec,data.placement);
    requireValue(spec.states[data.state] && spec.actions[data.current]?.from===data.state, 'Invalid saved actor state');
    requireValue(Number.isFinite(data.started)&&data.started>=0&&data.started<=now&&Number.isFinite(data.lastTime)&&data.lastTime>=data.started&&data.lastTime<=now,'Invalid saved actor clock');
    requireValue(data.pending===null || spec.actions[data.pending]?.from===spec.actions[data.current].to,'Invalid saved queued action');
    for(const key of ['state','current','started','pending','lastTime'])actor[key]=data[key];
    return actor;
  }
  snapshot(now, overlays = {}) {
    const sample = this.advance(now);
    const pose = this.spec.poses[sample.pose];
    const layers = [...pose.layers];
    for (const [name, key] of Object.entries(overlays)) {
      const overlay = this.spec.overlays[name];
      requireValue(overlay?.drawings[key], `Unknown overlay ${name}/${key}`);
      const offset = pose.overlay_offsets?.[name] ?? [0, 0];
      layers.push({drawing: overlay.drawings[key], z: overlay.z,
        transform: {origin: [0, 0], position: offset, degrees: 0}});
    }
    const root=this.motionOffset(sample);
    const point = p => [0, 1].map(i => this.placement.position[i] + (p[i]+root[i] - this.spec.origin[i]) * this.placement.scale);
    return {
      action: this.current, pose: sample.pose, frame: sample.frame,
      layers: layers.map(layer => ({...this.spec.drawings[layer.drawing], id: layer.drawing,
        image: `${this.spec.id}/${layer.drawing}`, position: point(transformPoint(this.spec.drawings[layer.drawing].position, layer.transform)),
        degrees: layer.transform?.degrees ?? 0,
        scale: this.placement.scale, z: this.placement.z + layer.z})),
      attachments: Object.fromEntries(Object.entries(pose.attachments).map(([name, p]) => [name, point(p)]))
      ,anchors: Object.fromEntries(Object.entries(pose.anchors).map(([name,p])=>[name,point(p)])),
      contacts:pose.contacts.map(c=>({...c,point:point(c.point)})),
      activity:(this.spec.actions[this.current].capability??this.spec.states[this.state]).activity,view:(this.spec.actions[this.current].capability??this.spec.states[this.state]).view,tick:sample.tick
    };
  }
}

export function validateStory(story, cast, takes) {
  requireValue(story.version === 1 && story.nodes[story.start], 'Invalid story entry');
  for (const [id, node] of Object.entries(story.nodes)) {
    requireValue(['choice', 'line', 'end'].includes(node.kind), `Unknown node type at ${id}`);
    const links = node.kind === 'choice' ? node.choices.map(c => c.next) : node.kind === 'line' ? [node.next] : [];
    for (const next of links) requireValue(story.nodes[next], `Missing story node ${next}`);
    if (node.kind === 'choice') {
      requireValue(node.choices.length && node.choices.every(c => typeof c.label === 'string' && c.set && typeof c.set === 'object'), `Invalid choices at ${id}`);
    }
    if (node.kind === 'line') {
      const spec = cast[node.actor]; const take = takes[node.take];
      requireValue(spec && take && take.actor === node.actor, `Missing/mismatched actor or take at ${id}`);
      requireValue(node.gesture === null || Object.values(spec.actions).some(a => !a.loop && a.intent === node.gesture), `Missing gesture intent at ${id}`);
      requireValue(node.gesture === null || Number.isFinite(node.gesture_at) && node.gesture_at >= 0 && node.gesture_at < take.duration, `Gesture outside line ${id}`);
      requireValue(take.fps === spec.fps && take.frames.length === Math.ceil(take.duration * take.fps), `Invalid speech frames at ${id}`);
      for (const frame of take.frames) requireValue(spec.overlays.mouth.drawings[frame], `Missing mouth frame at ${id}: ${frame}`);
      requireValue(take.captions.length && take.captions.every(c => Number.isFinite(c.start) && Number.isFinite(c.end) && c.start >= 0 && c.end > c.start && c.end <= take.duration + .001), `Invalid captions at ${id}`);
    }
  }
  return story;
}

export class Conversation {
  constructor(story) { this.story = story; this.restart(); }
  restart() { this.id = this.story.start; this.values = {}; this.revision = (this.revision ?? 0) + 1; }
  get node() { return this.story.nodes[this.id]; }
  save() {return {id:this.id,values:structuredClone(this.values),revision:this.revision};}
  restore(data) {
    requireValue(this.story.nodes[data.id] && data.values && typeof data.values==='object' && !Array.isArray(data.values) && Number.isInteger(data.revision)&&data.revision>0,'Invalid saved story');
    this.id=data.id;this.values=structuredClone(data.values);this.revision=data.revision;
  }
  choices() {
    requireValue(this.node.kind === 'choice', 'Current node has no choices');
    const result = this.node.choices.filter(c => !c.when || Object.entries(c.when).every(([k, v]) => this.values[k] === v));
    requireValue(result.length, 'No eligible choices');
    return result;
  }
  choose(index) {
    const choice = this.choices()[index];
    requireValue(choice, 'Invalid choice');
    Object.assign(this.values, choice.set); this.id = choice.next; this.revision++;
  }
  finishLine(revision) {
    if (revision !== this.revision) return false; // Discard a cancelled audio completion.
    requireValue(this.node.kind === 'line', 'Only a line can finish');
    this.id = this.node.next; this.revision++; return true;
  }
}

export function speechFrame(take, at) {
  requireValue(Number.isFinite(at) && at >= 0, 'Invalid speech time');
  return at >= take.duration ? 'X' : take.frames[Math.floor(at * take.fps)];
}
