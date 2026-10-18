const {test}=require('node:test');const assert=require('node:assert/strict');const vm=require('node:vm');const fs=require('node:fs');
const {sekoLocalRoute,sekoLocalDecision,sekoLocalOutput}=require('../scripts/seko_local_resident_page.js');
const source=fs.readFileSync('scripts/seko_local_resident_page.js','utf8');
const complete={jobId:'eedacf2c-49c2-4b6f-9f02-652d60834930',workflow:'seko-public-local-v1',canvasId:'100',storyId:'200',phase:'complete',textModel:'gpt-6.1-sol',imageModel:'BELUGA',
 multishot:{route:{text:'gpt-6.1-sol',video:{model:'abra_i2v_8s'},editing:'seko-native'},phase:'complete',canvasId:'500',timeline:{storyId:'600'}}};
function fixture(jobs=[complete],offline=false){
 const handlers={},requests=[],calls=[],intervals=[],nodes=new Map();
 const make=tag=>({tag,style:{},children:[],textContent:'',setAttribute(){},append(...els){this.children.push(...els);for(const el of els)if(el.id)nodes.set(el.id,el);},
  replaceChildren(...els){this.children=els;},remove(){nodes.delete(this.id);},addEventListener(name,fn){this[name]=fn;}});
 const document={body:make('body'),readyState:'loading',createElement:make,getElementById:id=>nodes.get(id),addEventListener:(name,fn)=>{handlers[name]=fn;}};
 const worker=Object.fromEntries(['resume','resumeVideo','resumeAssembly','resumeMulti','startVideo','startAssembly','startMulti'].map(name=>[name,async(...args)=>calls.push({name,args})]));
 const window={__sekoLocalWorkflow:worker,addEventListener:(name,fn)=>{handlers[name]=fn;},fetch:async()=>({native:true}),postMessage:msg=>{
   requests.push(msg);queueMicrotask(()=>handlers.message({source:window,origin:'https://seko.sensetime.com',data:{source:'flowkit-seko-extension',id:msg.id,...(offline?{error:'service offline'}:{value:jobs})}}));}};
 const context={window,document,URL,URLSearchParams,location:{origin:'https://seko.sensetime.com',search:'?canvasId=500'},
  crypto:require('node:crypto').webcrypto,structuredClone,setTimeout:()=>1,clearTimeout(){},setInterval:fn=>intervals.push(fn),Map,Set,
  installSekoLocalWorkflow:()=>{throw Error('unexpected duplicate worker');}};
 vm.runInNewContext(source+'\ninstallSekoLocalResident();',context);
 return {window,handlers,requests,calls,intervals,nodes,setOffline:v=>{offline=v;}};
}
async function ready(f){f.handlers.DOMContentLoaded();for(let i=0;i<5;i++)await new Promise(setImmediate);}
test('completed task auto-loads with no write or new stage',async()=>{
 const f=fixture();await ready(f);assert.equal(f.window.__flowkitSekoLocal.status.phase,'ready');
 assert.equal(f.window.__flowkitSekoLocal.status.jobs[0].jobId,complete.jobId);assert.equal(f.calls.length,0);
 assert.ok(f.requests.every(x=>x.method==='GET'));assert.ok(f.nodes.has('flowkit-local-resident'));
});
test('fresh document replay remains read-only',async()=>{
 for(let i=0;i<2;i++){const f=fixture();await ready(f);await f.window.__flowkitSekoLocal.tick();assert.equal(f.calls.length,0);assert.ok(f.requests.every(x=>x.method==='GET'));}
});
test('all unknown mutation phases are held without replay',()=>{
 for(const stage of ['video','assembly','multishot'])for(const phase of ['submitting','creating-node','rendering','uploading','needs-inspection','collecting']){
   const s={phase:'complete',[stage]:{phase}};assert.equal(sekoLocalDecision(s).method,null);
 }
});
test('only already-submitted render resumes, never starts the next stage',async()=>{
 const s=structuredClone(complete);s.multishot.phase='render-submitted';const f=fixture([s]);await ready(f);
 assert.deepEqual(f.calls.map(x=>x.name),['resumeMulti']);assert.ok(f.requests.every(x=>x.method==='GET'));
});
test('offline then recovered connection only reads the completed job',async()=>{
 const f=fixture([complete],true);await ready(f);assert.equal(f.window.__flowkitSekoLocal.status.phase,'disconnected');
 f.setOffline(false);await f.window.__flowkitSekoLocal.tick();assert.equal(f.window.__flowkitSekoLocal.status.phase,'ready');
 assert.equal(f.window.__flowkitSekoLocal.status.error,null);assert.equal(f.calls.length,0);assert.ok(f.requests.every(x=>x.method==='GET'));
});
test('vendor generation blocked before discovery; unrelated page released after discovery',async()=>{
 const f=fixture([]);await assert.rejects(f.window.fetch('/seko-api/seko-canvas/v1/canvas-node/gen-image',{method:'POST'}));
 await ready(f);assert.equal(f.window.__flowkitSekoLocal.status.phase,'unconfigured');
 assert.equal((await f.window.fetch('/seko-api/seko-canvas/v1/canvas-node/gen-image',{method:'POST'})).native,true);
});
test('output link has exact native identities and rejects malformed IDs',()=>{
 assert.equal(sekoLocalOutput(complete).url,'https://seko.sensetime.com/creation?id=600&tab=editor&canvasId=500');
 const s=structuredClone(complete);s.multishot.canvasId='https://other';assert.throws(()=>sekoLocalOutput(s));
});
test('static extension package uses source adapters before the legacy bridge',()=>{
 const manifest=JSON.parse(fs.readFileSync('extension/manifest.json','utf8'));
 assert.deepEqual(manifest.content_scripts[0].js,['seko_local_bundle.js','seko_page.js']);
 const bundle=fs.readFileSync('extension/seko_local_bundle.js','utf8');
 assert.match(bundle,/installSekoLocalResident\(\);/);assert.match(bundle,/import\(location.origin\+'\/assets\/LoginContext-Dre9Pek8.js'\)/);
 assert.doesNotMatch(bundle,/eval\(|new Function/);
});

test('fixed model route mismatch stops before any automatic continuation',async()=>{
 const s=structuredClone(complete);s.multishot.phase='render-submitted';s.multishot.route.video.model='other';
 assert.throws(()=>sekoLocalRoute(s));const f=fixture([s]);await ready(f);
 assert.equal(f.calls.length,0);assert.equal(f.window.__flowkitSekoLocal.status.phase,'disconnected');
});
