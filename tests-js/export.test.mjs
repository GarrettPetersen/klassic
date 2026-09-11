import test from 'node:test';
import assert from 'node:assert/strict';
import {DrawingRenderer} from '../web/player/renderer.js';

// Scene furniture and actors meet through depth, never character-specific masks.
test('a seated hip is between the chair back and near arm; resting hand is above it', () => {
  const images=new Map(['room','rear','front','hip','hand'].map(name=>[name,{name,width:10,height:10}]));
  const painted=[];
  const canvas={getContext:()=>({clearRect(){},drawImage(img){painted.push(img.name);}})};
  const renderer=new DrawingRenderer(canvas,{size:[100,100],background:{file:'room'},
    furniture:[{rear:{file:'rear',position:[0,0],z:-50},front:{file:'front',position:[0,0],z:30}}]},images);
  renderer.render([{layers:[{image:'hip',position:[0,0],scale:1,z:20},{image:'hand',position:[0,0],scale:1,z:40}],attachments:{}}],0,{smoke:false});
  assert.deepEqual(painted,['room','rear','hip','front','hand']);
});
