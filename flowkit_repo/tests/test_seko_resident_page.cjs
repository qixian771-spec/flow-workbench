const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('extension/seko_page.js','utf8').replaceAll(/import\(location.origin\+'\/assets\/[^']+'\)/g,'Promise.resolve(modules.shift())');
function fixture(jobs=[],failConfigOnce=false){
  const handlers={},requests=[],native=[],timers=[];
  const client={post(path){native.push(path);return Promise.resolve({native:true});}};
  const config={enabled:true,projects:[{canvasId:'123',storyId:'789'}]};
  const window={addEventListener(name,fn){(handlers[name]??=[]).push(fn);},
    fetch:async()=>({native:true}),
    postMessage(msg){requests.push(msg);queueMicrotask(()=>{
      const value=msg.path==='config'?config:msg.path.startsWith('jobs?')?jobs:null;
      for(const f of handlers.message||[])f({source:window,origin:'https://seko.sensetime.com',
        data:{source:'flowkit-seko-extension',id:msg.id,...(msg.path==='config'&&failConfigOnce?{error:'service offline'}:{value})}});
      if(msg.path==='config')failConfigOnce=false;
    });}};
  const nodes=new Map();
  const document={readyState:'loading',body:{append(el){nodes.set(el.id,el);}},
    getElementById:id=>nodes.get(id),createElement:()=>({style:{},setAttribute(){}}),
    addEventListener(name,fn){handlers[name]=[fn];}};
  const context={window,document,URL,URLSearchParams,location:{origin:'https://seko.sensetime.com',search:'?id=789'},
    crypto:require('node:crypto').webcrypto,structuredClone,Promise,Map,Set,Blob,Uint8Array,
    setTimeout:(fn,ms)=>{timers.push({fn,ms});return 1;},clearTimeout(){},setInterval(){},
    navigator:{locks:{request:async(name,opts,fn)=>fn({})}},
    modules:[{g:client,k:client},{},{}]};
  vm.runInNewContext(source,context);
  return {window,handlers,requests,native,client,nodes,timers};
}
async function ready(f){f.handlers.DOMContentLoaded[0]();for(let i=0;i<8;i++)await new Promise(setImmediate);}
test('automatic startup after a fresh document uses the saved mapping',async()=>{
  const f=fixture();await ready(f);
  assert.equal(f.window.__flowkitSeko.status.phase,'ready');
  assert.match(f.nodes.get('flowkit-seko-status').textContent,/刷新后自动启用/);
  assert.equal(f.requests.filter(x=>x.path==='config').length,1);
});
test('refresh reads existing completed jobs without submitting new paid work',async()=>{
  const jobs=[{jobId:'old',phase:'complete',receipt:{nodeId:'real',nodeGenId:'real-gen'}}];
  for(let n=0;n<2;n++){
    const f=fixture(jobs);await ready(f);
    assert.equal(f.window.__flowkitSeko.status.jobs[0].jobId,'old');
    assert.equal(f.requests.some(x=>x.method==='POST'),false);
  }
});
test('native generation is blocked even before startup; uploads still pass',async()=>{
  const f=fixture();
  await assert.rejects(f.window.fetch('https://seko.sensetime.com/seko-canvas/v1/canvas-node/gen-video'),/blocked/);
  await assert.rejects(f.window.fetch(new URL('https://seko.sensetime.com/x/multi-ref-video')),/blocked/);
  assert.equal((await f.window.fetch('https://seko.sensetime.com/normal-upload')).native,true);
  await ready(f);await f.client.post('upload');assert.deepEqual(f.native,['upload']);
});

test('initial service outage reconnects without any paid write',async()=>{
  const f=fixture([],true);await ready(f);
  assert.equal(f.window.__flowkitSeko.status.phase,'failed');
  const retry=f.timers.find(x=>x.ms===15000);assert.ok(retry);retry.fn();
  for(let i=0;i<8;i++)await new Promise(setImmediate);
  assert.equal(f.window.__flowkitSeko.status.phase,'ready');
  assert.equal(f.requests.some(x=>x.method==='POST'),false);
});
test('local-owned page never starts the obsolete native bridge',async()=>{
  const f=fixture();f.window.__flowkitSekoLocal={ownsPage:async()=>true};await ready(f);
  assert.equal(f.window.__flowkitSeko.status.phase,'local-workflow');
  assert.equal(f.requests.length,0);assert.equal(f.native.length,0);
});
test('legacy polling does not consume local-workflow task records',async()=>{
  const f=fixture([{jobId:'local',workflow:'seko-public-local-v1',phase:'complete'},
    {jobId:'legacy',phase:'complete',receipt:{nodeId:'123'}}]);await ready(f);
  assert.deepEqual(Array.from(f.window.__flowkitSeko.status.jobs,x=>x.jobId),['legacy']);
  assert.equal(f.requests.some(x=>x.method==='POST'),false);
});
