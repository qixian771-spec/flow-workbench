const {test}=require('node:test');const assert=require('node:assert/strict');
const {sekoAssemblyNode,sekoAssemblyTimeline,sekoAssemblyTrim}=require('../scripts/seko_local_assembly_page.js');
const s={assembly:{sourcePath:'STS/video.mp4',storyId:'30',target:{nodeId:'200'},timeline:{shotId:'400'}}};
const shot={id:'400',genVideoStatus:'GENERATING_COMPLETED',shotVideoUrl:'https://seko-resource.sensetime.com/STS/video.mp4',seq:1,shotVideoStartTime:1,shotVideoEndTime:7,duration:6,bindAudioSync:false};
test('one verified native trimmed shot maps to original source',()=>assert.equal(sekoAssemblyTimeline(s,[shot],true).shotId,'400'));
test('wrong source, trim, duplicated clips or changed identity fail',()=>{
 for(const [k,v] of Object.entries({id:'401',shotVideoUrl:'https://seko-resource.sensetime.com/STS/old.mp4',shotVideoStartTime:0,shotVideoEndTime:8,bindAudioSync:true,genVideoStatus:'GENERATING'}))
   assert.throws(()=>sekoAssemblyTimeline(s,[{...shot,[k]:v}],true));
 assert.throws(()=>sekoAssemblyTimeline(s,[shot,shot],true));
});
test('node must still be the original eight second source',()=>{
 const n={id:'200',nodeType:'VIDEO',genStatus:'GENERATING_COMPLETED',genFileUrl:shot.shotVideoUrl,duration:8};
 assert.equal(sekoAssemblyNode(s,{node:n},'200'),n);
 for(const [k,v] of Object.entries({id:'201',nodeType:'IMAGE',duration:6,genStatus:'GENERATING'}))assert.throws(()=>sekoAssemblyNode(s,{node:{...n,[k]:v}},'200'));
});
test('native trim uses the observed contract and disables uncertain PUT replay',async()=>{
 let calls=0;const m={k:{put:(path,options)=>{calls++;assert.equal(path,'guodong-studio/v1/shots/400/trim');
   assert.deepEqual(options,{json:{bindAudioSync:false,startTime:1,endTime:7},retry:0});
   return {json:async()=>{throw Error('unknown write');}};}}};
 await assert.rejects(sekoAssemblyTrim(m,'400'),/unknown write/);assert.equal(calls,1);
 assert.throws(()=>sekoAssemblyTrim(m,'wrong'));assert.equal(calls,1);
});
