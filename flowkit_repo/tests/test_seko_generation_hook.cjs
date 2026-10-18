const {test} = require('node:test');
const assert = require('node:assert/strict');
const {installSekoGenerationHook} = require('../scripts/seko_generation_hook.js');
function setup() {
  const calls=[]; const post=(...args)=>{calls.push(args);return 'native-nongeneration';};
  const client={post}; const bridge=installSekoGenerationHook({canvasId:'123',referenceNodeId:'456'},
    {clients:[client,client],uuid:()=> 'test-job'});
  const body={canvasId:'123',firstFrameNodeId:'456',lastFrameNodeId:'',selectedVideoDuration:8,videoPrompt:'Action'};
  return {client,bridge,calls,body,post};
}
test('native generation stays pending and never reaches original client',async()=>{
  const {client,bridge,calls,body}=setup();const p=client.post('seko-canvas/v1/canvas-node/gen-video',{json:body}).json();
  assert.equal(calls.length,0);assert.equal(bridge.snapshot().jobs[0].state,'captured');
  bridge.markSubmitted('test-job','flow-request');bridge.beginBackfill('test-job');
  bridge.finish('test-job',{nodeId:'789',nodeGenId:'790'});
  assert.deepEqual(await p,{nodeId:'789',nodeGenId:'790'});assert.equal(calls.length,0);
});
test('foreign project, reference, tail frame and duration reject without upstream',async()=>{
  for (const delta of [{canvasId:'999'},{firstFrameNodeId:'999'},{lastFrameNodeId:'999'},
    {selectedVideoDuration:5},{videoPrompt:''},{refNodeIds:['888']}]) {
    const {client,calls,body}=setup();await assert.rejects(client.post('seko-canvas/v1/canvas-node/gen-video',{json:{...body,...delta}}).json());
    assert.equal(calls.length,0);
  }
});
test('other known generation routes reject while media upload passes through',async()=>{
  const {client,calls}=setup();await assert.rejects(client.post('seko-canvas/v1/canvas-node/multi-ref-video',{}).json());
  assert.equal(client.post('seko-canvas/v1/canvas-node',{}),'native-nongeneration');assert.equal(calls.length,1);
});
test('duplicate active request does not create another job',async()=>{
  const {client,bridge,body,calls}=setup();client.post('seko-canvas/v1/canvas-node/gen-video',{json:body});
  await assert.rejects(client.post('seko-canvas/v1/canvas-node/gen-video',{json:body}).json());
  assert.equal(bridge.snapshot().jobs.length,1);assert.equal(calls.length,0);bridge.fail('test-job','stop');
});
test('no premature completion or disarm while job pending',()=>{
  const {client,bridge,body}=setup();client.post('seko-canvas/v1/canvas-node/gen-video',{json:body});
  assert.throws(()=>bridge.finish('test-job',{nodeId:'1',nodeGenId:'2'}));assert.throws(()=>bridge.dispose());
  bridge.fail('test-job','stop');bridge.dispose();
});
test('disarm restores exactly the original client',()=>{
  const {client,bridge,post}=setup();bridge.dispose();assert.equal(client.post,post);
});
