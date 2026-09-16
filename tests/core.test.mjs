// NEW: deterministic safety and workspace tests for the character pipeline.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { safePath, hashFile, readGlb, validateJob, reserveGeneration, initProject } from '../scripts/core.mjs';

function temp(t) {
  const root = fs.mkdtempSync(path.join(os.tmpdir(), 'character-pipeline-'));
  t.after(() => fs.rmSync(root, { recursive: true, force: true }));
  return root;
}
test('workspace confinement rejects traversal and absolute paths', t => {
  const root = temp(t);
  assert.throws(() => safePath(root, '../outside'));
  assert.throws(() => safePath(root, path.resolve(root, '..', 'outside')));
  assert.equal(safePath(root, 'inputs/model.glb'), path.join(root, 'inputs', 'model.glb'));
});
test('workspace confinement refuses existing symlink ancestors', t => {
  const root = temp(t); const other = temp(t);
  try { fs.symlinkSync(other, path.join(root, 'escape'), 'dir'); }
  catch (e) { if (e.code === 'EPERM') return t.skip('OS denies symlink creation'); throw e; }
  assert.throws(() => safePath(root, 'escape/model.glb'));
});
test('initialization refuses to overwrite existing project configuration', t => {
  const root = temp(t); initProject(root);
  const p = path.join(root, 'project.json'); const before = hashFile(p);
  assert.throws(() => initProject(root)); assert.equal(hashFile(p), before);
});
test('GLB validation rejects HTML disguised as an asset', t => {
  const root = temp(t); const p = path.join(root, 'bad.glb');
  fs.writeFileSync(p, '<html>Login</html>'); assert.throws(() => readGlb(p));
});
test('GLB validation checks declared size and embedded JSON', t => {
  const root = temp(t); const p = path.join(root, 'good.glb');
  let txt = JSON.stringify({asset:{version:'2.0'}, scenes:[{}]});
  txt = txt.padEnd(Math.ceil(txt.length / 4) * 4, ' ');
  const b = Buffer.alloc(20 + Buffer.byteLength(txt));
  b.write('glTF',0); b.writeUInt32LE(2,4); b.writeUInt32LE(b.length,8);
  b.writeUInt32LE(Buffer.byteLength(txt),12); b.writeUInt32LE(0x4E4F534A,16); b.write(txt,20);
  fs.writeFileSync(p,b); assert.equal(readGlb(p).asset.version, '2.0');
  b.writeUInt32LE(8,8); fs.writeFileSync(p,b); assert.throws(()=>readGlb(p));
});
test('job validation rejects arbitrary tasks and nested path escapes', t => {
  const root=temp(t);
  assert.throws(()=>validateJob(root,{task:'exec',input:'x'}));
  assert.throws(()=>validateJob(root,{task:'materials',input:'in.blend', materials:[{base_color:'../../secret.png'}]}));
  assert.throws(()=>validateJob(root,{task:'bake',input:'in.blend',resolution:32768}));
});
test('generation budget is reserved before a browser submit', () => {
  const p={max_generations:2, max_credits:5};
  const e=[{type:'generation_reserved',cost_credits:3}];
  assert.throws(()=>reserveGeneration(p,e,3));
  assert.throws(()=>reserveGeneration(p,e,null));
  const r=reserveGeneration(p,e,2); assert.equal(r.type,'generation_reserved');
  assert.throws(()=>reserveGeneration(p,[...e,r],0));
});
// NEW: regression coverage for bake object names versus dependency file paths.
test('bake pairs accept object-name arrays without treating names as file paths', t => {
  const root=temp(t);
  const job={task:'bake',input:'inputs/low.blend',high:'inputs/high.glb',pairs:[{low:'Body',high:['HIGH__Body','HIGH__Buttons']}]};
  assert.equal(validateJob(root,job),job);
});
test('a top-level high-poly dependency must be a relative file path', t => {
  const root=temp(t);
  assert.throws(()=>validateJob(root,{task:'bake',input:'inputs/low.blend',high:['Body']}));
});
// NEW: intermediate exports are distinct from a final release and must be available before rigging.
test('pre-rig handoff, candidate export, face_rig and studio_render are recognized tasks', t => {
  const root=temp(t);
  for(const task of ['handoff','export_candidate','face_rig','studio_render']) assert.equal(validateJob(root,{task,input:'inputs/current.blend'}).task,task);
});

