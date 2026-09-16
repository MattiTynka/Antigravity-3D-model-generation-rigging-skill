// NEW: installer integration tests; these run from the distributable archive, not an installed skill copy.
import test from 'node:test';
import assert from 'node:assert/strict';
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import {fileURLToPath} from 'node:url';
import {spawnSync} from 'node:child_process';
const installer=path.resolve(path.dirname(fileURLToPath(import.meta.url)),'../../install.mjs');
const enabled=fs.existsSync(installer);
function fixture(t){const p=fs.mkdtempSync(path.join(os.tmpdir(),'character install '));t.after(()=>fs.rmSync(p,{recursive:true,force:true}));return p;}
function run(root,...args){return spawnSync(process.execPath,[installer,'--project',root,'--target','both',...args],{encoding:'utf8',shell:false,timeout:15000});}
test('both agents install without editing project instruction files',{skip:!enabled},t=>{
  const root=fixture(t);fs.writeFileSync(path.join(root,'AGENTS.md'),'retain codex instructions');fs.writeFileSync(path.join(root,'CLAUDE.md'),'retain claude instructions');
  const result=run(root);assert.equal(result.status,0,result.stderr);
  for(const folder of ['.agents','.claude']) assert.ok(fs.existsSync(path.join(root,folder,'skills','character-pipeline','SKILL.md')));
  assert.equal(fs.readFileSync(path.join(root,'AGENTS.md'),'utf8'),'retain codex instructions');
  assert.equal(fs.readFileSync(path.join(root,'CLAUDE.md'),'utf8'),'retain claude instructions');
});
test('existing skill copies are not overwritten',{skip:!enabled},t=>{
  const root=fixture(t);assert.equal(run(root).status,0);
  const file=path.join(root,'.agents','skills','character-pipeline','SKILL.md');fs.appendFileSync(file,'\nlocal change\n');
  assert.equal(run(root).status,1);assert.match(fs.readFileSync(file,'utf8'),/local change/);
});
test('uninstall removes only unmodified installed copies',{skip:!enabled},t=>{
  const root=fixture(t);assert.equal(run(root).status,0);assert.equal(run(root,'--uninstall').status,0);
  for(const folder of ['.agents','.claude']) assert.equal(fs.existsSync(path.join(root,folder,'skills','character-pipeline')),false);
});
test('uninstall preserves both copies when one contains edits',{skip:!enabled},t=>{
  const root=fixture(t);assert.equal(run(root).status,0);
  const file=path.join(root,'.claude','skills','character-pipeline','SKILL.md');fs.appendFileSync(file,'\nretain this edit\n');
  assert.equal(run(root,'--uninstall').status,1);
  for(const folder of ['.agents','.claude']) assert.ok(fs.existsSync(path.join(root,folder,'skills','character-pipeline','SKILL.md')));
});
test('antigravity target installs cleanly to .agents',{skip:!enabled},t=>{
  const root=fixture(t);
  const res=spawnSync(process.execPath,[installer,'--project',root,'--target','antigravity'],{encoding:'utf8',shell:false,timeout:15000});
  assert.equal(res.status,0,res.stderr);
  assert.ok(fs.existsSync(path.join(root,'.agents','skills','character-pipeline','SKILL.md')));
  assert.equal(fs.existsSync(path.join(root,'.claude','skills','character-pipeline')),false);
});

