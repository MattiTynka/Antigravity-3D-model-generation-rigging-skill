#!/usr/bin/env node
// NEW: local run coordinator. Browser actions remain visible, host-agent tool calls.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';
import { fileURLToPath } from 'node:url';
import { spawnSync } from 'node:child_process';
import { safePath,hashFile,readJson,atomicJson,readGlb,validateJob,jobFiles,reserveGeneration,initProject,withLock } from './core.mjs';
const here=path.dirname(fileURLToPath(import.meta.url));
function args(argv) {const out={};for(let i=0;i<argv.length;i++){if(!argv[i].startsWith('--'))throw new Error(`Unexpected argument ${argv[i]}`);const key=argv[i].slice(2);if(i+1>=argv.length||argv[i+1].startsWith('--'))throw new Error(`Missing value for ${key}`);out[key]=argv[++i];}return out;}
function help(){console.log(`Commands:
  init --project PATH
  doctor --project PATH [--blender PATH]
  status --project PATH
  check-glb --project PATH --file RELATIVE.glb
  reserve --project PATH --domain DOMAIN --cost NUMBER --evidence RELATIVE_FILE
  event --project PATH --file RELATIVE_EVENT.json
  blender --project PATH --job RELATIVE_JOB.json [--blender PATH] [--timeout MINUTES]
Node 20.19+; local Blender 4.5 LTS is the intended baseline. No shell interpolation.`);}
try {
  const [command,...argv]=process.argv.slice(2);
  if(!command||command==='--help'){help();process.exit(0);}
  const a=args(argv); if(!a.project)throw new Error('--project is required.');
  const root=path.resolve(a.project.trim());
  if(command==='init'){initProject(root);console.log(root);process.exit(0);}
  const project=readJson(safePath(root,'project.json'));
  if(command==='doctor'){
    const executable=a.blender??process.env.BLENDER_PATH??'blender';
    const version=spawnSync(executable,['--version'],{encoding:'utf8',windowsHide:true,timeout:15000,shell:false});
    console.log(JSON.stringify({node:process.version,platform:process.platform,workspace:root,blender:version.status===0?version.stdout.split('\n')[0]:null,error:version.error?.message??null,browser:'NOT_PROBED: host agent must inspect attached browser tools and authorized tabs',intended_baseline:'Blender 4.5 LTS; run the bundled selftest before assets'},null,2));
    process.exitCode=version.status===0?0:2;
  }else if(command==='status'){console.log(JSON.stringify(readJson(safePath(root,'state.json')),null,2));
  }else if(command==='check-glb'){const p=safePath(root,a.file);const g=readGlb(p);console.log(JSON.stringify({sha256:hashFile(p),bytes:fs.statSync(p).size,meshes:g.meshes?.length??0,skins:g.skins?.length??0,animations:g.animations?.map(x=>x.name??'(unnamed)')??[],note:'Container check only, not a full Khronos glTF Validator result.'},null,2));
  }else if(command==='reserve'||command==='event'){
    withLock(root,()=>{
      const state=readJson(safePath(root,'state.json'));let event;
      if(command==='reserve'){
        if(!project.policy.approved_upload_domains.includes(a.domain))throw new Error('Domain has not been approved in project.json.');
        const evidence=safePath(root,a.evidence); if(!fs.statSync(evidence).isFile())throw new Error('Missing observed price/approval evidence.');
        event={...reserveGeneration(project.policy,state.events,Number(a.cost)),domain:a.domain,evidence:a.evidence,evidence_sha256:hashFile(evidence)};
      }else{
        event=readJson(safePath(root,a.file));
        if(!['browser_observation','generation_submitted','generation_result','checkpoint','blocked','visual_review','operator_approval'].includes(event.type))throw new Error('Unsupported event type.');
        if(typeof event.evidence!=='string')throw new Error('Event requires evidence path.');
        event.evidence_sha256=hashFile(safePath(root,event.evidence));event.time=new Date().toISOString();
      }
      state.events.push(event);atomicJson(safePath(root,'state.json'),state);console.log(JSON.stringify(event,null,2));
    });
  }else if(command==='blender'){
    withLock(root,()=>{
      const job=validateJob(root,readJson(safePath(root,a.job)));const dependencies=jobFiles(root,job);
      // NEW: inspect GLB container dependencies before handing them to Blender.
      for(const dependency of dependencies)if(path.extname(dependency.path).toLowerCase()==='.glb')readGlb(safePath(root,dependency.path));
      // NEW: runtime identity participates in the cache; switching Blender requires revalidation.
      const executable=a.blender??process.env.BLENDER_PATH??'blender';
      const probe=spawnSync(executable,['--version'],{encoding:'utf8',windowsHide:true,timeout:15000,shell:false});
      if(probe.status!==0)throw new Error(probe.error?.message??'Unable to identify Blender executable.');
      const blenderIdentity={executable,version:probe.stdout.trim()};
      const minutes=Number(a.timeout??30);if(!Number.isFinite(minutes)||minutes<=0||minutes>240)throw new Error('Timeout must be greater than zero and at most 240 minutes.');
      const script=path.join(here,'blender_pipeline.py');
      const signature=crypto.createHash('sha256').update(JSON.stringify({job,dependencies,blenderIdentity,script:hashFile(script),math:hashFile(path.join(here,'geometry_math.py'))})).digest('hex');
      const state=readJson(safePath(root,'state.json'));
      const previous=state.runs.find(r=>r.signature===signature&&r.status==='COMPLETED');
      if(previous&&previous.outputs?.every(o=>{try{return hashFile(safePath(root,o.path))===o.sha256;}catch{return false;}})){
        console.log(JSON.stringify({reused:true,...previous},null,2));return;
      }
      const id=`${new Date().toISOString().replace(/[:.]/g,'_')}_${job.task}_${crypto.randomUUID().slice(0,8)}`;
      const rel=`runs/${id}`;const dir=safePath(root,rel);fs.mkdirSync(dir,{recursive:false});
      const request={...job,_workspace:root,_run_dir:dir,_signature:signature};atomicJson(path.join(dir,'request.json'),request);
      const run={id,task:job.task,signature,blender:blenderIdentity,status:'RUNNING',dependencies,outputs:[],started:new Date().toISOString()};
      state.runs.push(run);atomicJson(safePath(root,'state.json'),state);
      // NEW: persist failure even when a malformed report or missing output raises after Blender exits.
      try {
        const log=fs.openSync(path.join(dir,'blender.log'),'wx');
        let result;
        try {
          result=spawnSync(executable,['--background','--factory-startup','--disable-autoexec','--python-exit-code','23','--python',script,'--','--job',path.join(dir,'request.json')],{cwd:root,stdio:['ignore',log,log],windowsHide:true,shell:false,timeout:minutes*60000,killSignal:'SIGTERM'});
        } finally {fs.closeSync(log);}
        const reportFile=path.join(dir,'result.json');
        const report=fs.existsSync(reportFile)?readJson(reportFile):null;
        run.status=result.status===0&&report?.status==='COMPLETED'?'COMPLETED':'FAILED';
        run.exit_code=result.status;run.error=result.error?.message??report?.error??null;
        run.outputs=(report?.outputs??[]).map(p=>({path:path.relative(root,safePath(dir,p)).replaceAll('\\','/'),sha256:hashFile(safePath(dir,p))}));
        if(fs.existsSync(reportFile))run.outputs.push({path:`${rel}/result.json`,sha256:hashFile(reportFile)});
        run.report=`${rel}/result.json`;
      } catch(error) {
        run.status='FAILED';run.error=error.message;
      } finally {
        run.ended=new Date().toISOString();state.status=run.status;atomicJson(safePath(root,'state.json'),state);
      }
      console.log(JSON.stringify(run,null,2));if(run.status!=='COMPLETED')process.exitCode=1;
    });
  }else throw new Error(`Unknown command: ${command}`);
}catch(e){console.error(`ERROR: ${e.message}`);process.exitCode=1;}
