const {test}=require('node:test');
const assert=require('node:assert/strict');
const fs=require('node:fs');
const vm=require('node:vm');
const {webcrypto,createHash}=require('node:crypto');
const {File}=require('node:buffer');
const source=fs.readFileSync(require('node:path').join(__dirname,'../scripts/seko_native_backfill.js'),'utf8')
 .replaceAll("await import('/assets/LoginContext-CFHyujin.js')",'modules.story')
 .replaceAll("await import('/assets/canvas-BZat8bJg.js')",'modules.canvas')
 .replaceAll("await import('/assets/useOSSUploader-BaPQIV7u.js')",'modules.moderation');
function fixture(options={}) {
 const bytes=Buffer.from('real transfer fixture'),calls=[];
 const job={jobId:'j',state:'submitted',canvasId:'c',nativeRequest:{videoPrompt:'action'}};
 let shot={id:'s1',seq:0,seqValue:1,duration:8,shotVideoStartTime:0,shotVideoEndTime:8,
   shotVideoUrl:'https://media.test/old',genVideoStatus:'GENERATING_COMPLETED',bindAudioSync:true,linesAudioEnabledFlag:true};
 Object.assign(shot,options.shot);
 const node={id:'n',duration:8,genStatus:'GENERATING_COMPLETED',genFileUrl:'https://media.test/STS/new'};
 const bridge={snapshot:()=>({jobs:[job]}),beginBackfill:()=>job.state='backfilling',
   finish:()=>{calls.push('finish');job.state='complete'},fail:()=>job.state='failed'};
 const modules={story:{aj:async()=>[{...shot}],Y:()=>{calls.push('upload');return{promise:Promise.resolve({path:'STS/new',url:node.genFileUrl})}},
   bW:async()=>{calls.push('render');return{id:'render'}}},
   canvas:{an:async()=>({storyId:options.storyId??'story'}),
     D:async()=>{calls.push('create');return{nodeId:'n',nodeGenId:'ng'}},b:async()=>({node}),
     aq:async()=>{calls.push('refresh');shot={...shot,shotVideoUrl:options.stale?'https://media.test/old':node.genFileUrl}}},
   moderation:{m:async()=>({passed:!options.rejectModeration})}};
 const window={__sekoFlowBridge:bridge,__flowUploadParts:[bytes]};
 const context=vm.createContext({modules,window,URL,Blob,File,crypto:webcrypto});vm.runInContext(source,context);
 const input={jobId:'j',storyId:'story',shotId:'s1',expectedMediaUrl:'https://media.test/old',duration:8,
   sha256:createHash('sha256').update(bytes).digest('hex')};
 return{context,window,calls,input,run:(arg=input)=>context.sekoNativeBackfill(arg)};
}
test('real upload/moderation/receipt/refresh happen in order',async()=>{
 const f=fixture();const result=await f.run();assert.equal(result.phase,'complete');
 assert.deepEqual(f.calls,['upload','create','finish','refresh']);assert.equal(result.after.id,'s1');
});
test('wrong story or concurrent shot prevents upload',async()=>{
 for(const options of [{storyId:'other'},{shot:{shotVideoUrl:'https://media.test/concurrent'}},{shot:{shotVideoEndTime:7}}]){
  const f=fixture(options);await assert.rejects(f.run());assert.deepEqual(f.calls,[]);
 }
});
test('wrong media digest prevents upload',async()=>{
 const f=fixture();await assert.rejects(f.run({...f.input,sha256:'bad'}),/digest/);assert.deepEqual(f.calls,[]);
});
test('failed moderation never creates a node or updates timeline',async()=>{
 const f=fixture({rejectModeration:true});await assert.rejects(f.run(),/moderation/);assert.deepEqual(f.calls,['upload']);
 assert.equal(f.window.__sekoBackfills.j.phase,'failed');
});
test('stale timeline response is a failure even if node creation succeeded',async()=>{
 const f=fixture({stale:true});await assert.rejects(f.run(),/verification/);assert.equal(f.window.__sekoBackfills.j.phase,'failed');
});
test('render refuses incomplete/missing shot mappings',async()=>{
 const f=fixture();await f.run();await assert.rejects(f.context.sekoNativeRender({canvasId:'c',storyId:'story',jobs:[{jobId:'j',shotId:'s1'}]}),/two/);
 assert.ok(!f.calls.includes('render'));
});
