const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const source=fs.readFileSync('scripts/seko_dialogue_pipeline.js','utf8')
  .replace("import('/assets/LoginContext-CFHyujin.js')",'Promise.resolve(modules.m)')
  .replace("import('/assets/canvas-BZat8bJg.js')",'Promise.resolve(modules.canvas)')
  .replace("import('/assets/shot-BflClSjB.js')",'Promise.resolve(modules.shot)');
function fixture(phase,extra={}){
  const plan={storyId:'story',canvasId:'canvas',initialShotId:'shot1',lines:[1,2,3,4].map(i=>({jobId:'job'+i,duration:5}))};
  let state=phase?JSON.stringify({phase,storyId:'story',canvasId:'canvas',history:[],...extra}):null;
  const calls=[];
  const modules={m:{aj:async()=>[],ak:async()=>({}),bW:async()=>{calls.push('render');return {id:'real-render'};}},
    canvas:{an:async()=>({storyId:'story'}),aq:async()=>{calls.push('assemble');return [];}},
    shot:{b:async()=>{calls.push('lip');throw Error('native rejection');}}};
  const ctx={modules,URL,crypto:require('node:crypto').webcrypto,setTimeout,
    window:{__flowkitSeko:{status:{jobs:[]}}},
    localStorage:{getItem:()=>state,setItem:(k,v)=>{state=v;}}};
  vm.createContext(ctx);vm.runInContext(source,ctx);
  return {plan,ctx,modules,calls,state:()=>JSON.parse(state),step:()=>ctx.sekoDialogueStep(plan)};
}
test('incomplete Flow jobs cannot reach timeline writes',async()=>{
  const f=fixture();await assert.rejects(f.step(),/Flow media incomplete/);assert.equal(f.calls.length,0);
});
test('missing actual Flow frames or exact audio prevents the dialogue stage',async()=>{
  const f=fixture('flow-ready');await assert.rejects(f.step(),/Verified Flow first frames/);assert.equal(f.state().phase,'flow-ready');
});
test('unknown native mutation is not retried after refresh',async()=>{
  const f=fixture('submitting-lips');await assert.rejects(f.step(),/Uncertain write checkpoint/);assert.equal(f.calls.length,0);
});
test('missing or multiple faces block lip generation',async()=>{
  const f=fixture('faces-pending',{shots:[{id:'one'}]});
  f.modules.m.ak=async()=>({faceMaskDetectStatus:'GENERATING_COMPLETED',faceMaskPosition:{masks:[]}});
  await assert.rejects(f.step(),/Exactly one detected face/);assert.equal(f.calls.length,0);
});
test('original completed Flow video is not accepted as a completed lip result',async()=>{
  const shots=[1,2,3,4].map(i=>({id:'shot'+i,genVideoStatus:'GENERATING_COMPLETED',videoGenType:'FIRST_FRAME'}));
  const f=fixture('lips-pending',{shots});f.modules.m.aj=async()=>shots;
  await assert.rejects(f.step(),/Dialogue generation did not complete/);assert.equal(f.calls.length,0);
});
test('native render receipt is saved and repeat invocation does not render again',async()=>{
  const f=fixture('dialogue-ready');await f.step();await f.step();assert.deepEqual(f.calls,['render']);assert.equal(f.state().render.id,'real-render');
});
