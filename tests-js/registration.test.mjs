import test from 'node:test';
import assert from 'node:assert/strict';
import {RegistrationEditor,canvasPoint,localPoint} from '../web/review/registration.js';
import {faceSubject,statusFor,subjectId} from '../web/review/acceptance.js';
test('dragging a shoulder moves the whole arm and prop, with undo and a reviewable source patch',()=>{
 const spec={id:'fixture',production:{source_signature:'source'},drawings:{arm:{position:[0,0]}},poses:{idle:{layers:[{drawing:'arm',z:40}],anchors:{shoulder:[10,20]},attachments:{cup:[50,60]},contacts:[{id:'foot',point:[30,80],kind:'foot',locked:true}],anchor_bindings:{shoulder:{layers:[0],overlays:[],attachments:['cup']}}}}};
 assert.equal(subjectId('pose',"offer (host's)"),'pose:offer%20%28host%27s%29');
 const editor=new RegistrationEditor(spec);editor.begin('idle');editor.move('idle','anchor','shoulder',[15,27]);editor.commit();
 assert.deepEqual(spec.poses.idle.layers[0].transform.position,[5,7]);assert.deepEqual(spec.poses.idle.attachments.cup,[55,67]);assert.deepEqual(spec.poses.idle.contacts[0].point,[30,80]);
 const patch=editor.patch();assert.equal(patch.base_signature,'source');assert.deepEqual(patch.changes[0].before.anchors.shoulder,[10,20]);
 editor.undo();assert.equal(editor.dirty,false);editor.redo();assert.equal(editor.dirty,true);
});
test('pointer coordinates account for canvas letterboxing, actor scale and moving root',()=>{
 const canvas={width:1000,height:500,getBoundingClientRect:()=>({left:10,top:20,width:500,height:500})};
 assert.deepEqual(canvasPoint({clientX:260,clientY:270},canvas),[500,250]);
 assert.deepEqual(localPoint([500,250],{position:[100,100],scale:2},[30,40],[10,0]),[220,115]);
});
test('a face case approval never implies acceptance of another expression or the body',()=>{
 const id=faceSubject('sit',{mouth:'X',eyes:'open'}),local=new Map([['actor/'+id,{decision:'approved'}]]);
 assert.equal(id,'face:sit:eyes%3Dopen:mouth%3DX');assert.equal(statusFor({reviews:{}},local,'actor',id),'approved');
 assert.equal(statusFor({reviews:{}},local,'actor','pose:sit'),'unreviewed');assert.equal(statusFor({reviews:{}},local,'actor',faceSubject('sit',{mouth:'A',eyes:'open'})),'unreviewed');
});
