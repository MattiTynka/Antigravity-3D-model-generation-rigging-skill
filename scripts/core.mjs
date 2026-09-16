// NEW: dependency-free workspace, file-integrity and budget helpers.
import fs from 'node:fs';
import path from 'node:path';
import crypto from 'node:crypto';

export const TASKS = new Set(['inspect','prepare','uv','retopo','bake','materials','rig','face_rig','animate','retarget','qa','export','preview','studio_render','handoff','export_candidate','selftest']);
export function safePath(root, relative) {
  if (typeof relative !== 'string' || !relative || relative.includes('\0') || path.isAbsolute(relative) || /^[A-Za-z]:/.test(relative) || relative.startsWith('\\\\')) throw new Error('Use a nonempty workspace-relative path.');
  const base = path.resolve(root);
  const candidate = path.resolve(base, relative);
  if (candidate !== base && !candidate.startsWith(base + path.sep)) throw new Error(`Path escapes workspace: ${relative}`);
  let current = base;
  if (fs.existsSync(base) && fs.lstatSync(base).isSymbolicLink()) throw new Error('Workspace root must not be a symlink.');
  for (const part of path.relative(base, candidate).split(path.sep).filter(Boolean)) {
    current = path.join(current, part);
    if (fs.existsSync(current) && fs.lstatSync(current).isSymbolicLink()) throw new Error(`Symlink path refused: ${relative}`);
  }
  return candidate;
}
export function hashFile(filename) {
  const h = crypto.createHash('sha256');
  const fd = fs.openSync(filename, 'r');
  const chunk = Buffer.alloc(1024 * 1024);
  try { let n; while ((n = fs.readSync(fd, chunk, 0, chunk.length, null)) > 0) h.update(chunk.subarray(0,n)); }
  finally { fs.closeSync(fd); }
  return h.digest('hex');
}
export function readJson(filename) { return JSON.parse(fs.readFileSync(filename, 'utf8').replace(/^\uFEFF/,'')); }
export function atomicJson(filename, value) {
  fs.mkdirSync(path.dirname(filename), {recursive:true});
  const temporary = `${filename}.${crypto.randomUUID()}.tmp`;
  fs.writeFileSync(temporary, JSON.stringify(value,null,2)+'\n', {flag:'wx'});
  fs.renameSync(temporary,filename);
}
export function readGlb(filename) {
  const fd=fs.openSync(filename,'r');
  try {
    const head=Buffer.alloc(20); const n=fs.readSync(fd,head,0,20,0);
    if(n!==20 || head.toString('ascii',0,4)!=='glTF' || head.readUInt32LE(4)!==2) throw new Error('Not a GLB 2 file.');
    if(head.readUInt32LE(8)!==fs.fstatSync(fd).size) throw new Error('GLB length mismatch.');
    const len=head.readUInt32LE(12);
    if(head.readUInt32LE(16)!==0x4E4F534A || len>64*1024*1024 || len%4 || 20+len>fs.fstatSync(fd).size) throw new Error('Invalid GLB JSON chunk.');
    const data=Buffer.alloc(len); if(fs.readSync(fd,data,0,len,20)!==len) throw new Error('Truncated GLB JSON.');
    const json=JSON.parse(data.toString('utf8'));
    if(json.asset?.version!=='2.0') throw new Error('Unexpected glTF asset version.');
    for(const item of [...(json.images??[]),...(json.buffers??[])]) {
      if(item.uri && !item.uri.startsWith('data:')) throw new Error('External GLB dependencies require a separately audited glTF workflow.');
    }
    return json;
  } finally {fs.closeSync(fd);}
}
const PATH_FIELDS=new Set(['input','high','skeleton','motion','mapping','source','base_color','roughness_map','metallic_map','normal_map','ao_map','emission_map','approval_file','qa_report']);
export function validateJob(root,job) {
  if(!job || typeof job!=='object' || Array.isArray(job) || !TASKS.has(job.task)) throw new Error('Unknown Blender task.');
  const walk=(v,key='')=>{
    // NEW: nested bake pairs use high as an array of object names, not a filename.
    if(PATH_FIELDS.has(key) && v!==null && v!==undefined && !(key==='high' && Array.isArray(v))) safePath(root,v);
    if(Array.isArray(v)) v.forEach(x=>walk(x));
    else if(v && typeof v==='object') Object.entries(v).forEach(([k,x])=>walk(x,k));
  }; walk(job);
  if(job.high!==undefined && typeof job.high!=='string') throw new Error('Top-level high must be a relative file path.');
  if(job.task!=='selftest' && !job.input) throw new Error('Job requires input.');
  if(job.resolution!==undefined && (!Number.isInteger(job.resolution) || job.resolution<64 || job.resolution>8192)) throw new Error('Resolution must be 64..8192.');
  if(job.fps!==undefined && (!Number.isFinite(job.fps) || job.fps<1 || job.fps>120)) throw new Error('FPS must be 1..120.');
  return job;
}
export function jobFiles(root,job) {
  const files=new Set();
  function walk(v,key='') {
    if(PATH_FIELDS.has(key) && typeof v==='string') files.add(v);
    if(Array.isArray(v)) v.forEach(x=>walk(x));
    else if(v && typeof v==='object') Object.entries(v).forEach(([k,x])=>walk(x,k));
  } walk(job);
  for(const p of job.dependencies??[]) {safePath(root,p); files.add(p);}
  return [...files].sort().map(p=>({path:p,sha256:hashFile(safePath(root,p))}));
}
export function reserveGeneration(policy,events,cost) {
  if(!Number.isFinite(cost) || cost<0) throw new Error('Unknown generation price: obtain operator approval first.');
  const reserved=events.filter(e=>e.type==='generation_reserved');
  if(!Number.isInteger(policy.max_generations) || policy.max_generations<0 || reserved.length>=policy.max_generations) throw new Error('Generation count budget exhausted.');
  const spent=reserved.reduce((sum,e)=>sum+e.cost_credits,0);
  if(!Number.isFinite(policy.max_credits) || spent+cost>policy.max_credits) throw new Error('Credit budget exhausted.');
  return {type:'generation_reserved',id:crypto.randomUUID(),time:new Date().toISOString(),cost_credits:cost};
}
export function initProject(root) {
  fs.mkdirSync(root,{recursive:true});
  const cfg=safePath(root,'project.json');
  if(fs.existsSync(cfg)) throw new Error('Project already initialized; existing configuration was preserved.');
  for(const p of ['inputs/references','inputs/hunyuan','inputs/modddif','inputs/motion','jobs','approvals','evidence','runs','delivery']) fs.mkdirSync(safePath(root,p),{recursive:true});
  atomicJson(cfg,{schema_version:1,character_name:path.basename(root),target:'generic-glb',height_m:1.8,policy:{max_generations:0,max_credits:0,approved_upload_domains:[],allow_public_projects:false},quality:{max_triangles:80000,max_influences:4,weight_tolerance:0.0001},notes:'Budgets are deliberately zero until the user authorizes service use. Paths are workspace-relative.'});
  atomicJson(safePath(root,'state.json'),{schema_version:1,status:'INITIALIZED',runs:[],events:[]});
  fs.writeFileSync(safePath(root,'.gitignore'),'inputs/\nruns/\nevidence/\napprovals/\ndelivery/\n*.lock\n');
}
export function withLock(root,fn) {
  const p=safePath(root,'pipeline.lock');
  let fd;
  try {fd=fs.openSync(p,'wx');}
  catch(e) {if(e.code==='EEXIST') throw new Error('Another run or stale lock exists. Check its PID before manually removing pipeline.lock.'); throw e;}
  fs.writeFileSync(fd,JSON.stringify({pid:process.pid,time:new Date().toISOString()}));
  try {return fn();} finally {fs.closeSync(fd);fs.unlinkSync(p);}
}
