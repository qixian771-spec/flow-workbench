const {test}=require('node:test');const assert=require('node:assert/strict');
const {sekoMultiTimeline,sekoMultiNode,sekoMultiTrim}=require('../scripts/seko_local_multishot_page.js');
const s={video:{upload:{path:'STS/a.mp4'},sha256:'a',mediaId:'A',receipt:{nodeId:'10'}},multishot:{upload:{path:'STS/b.mp4'},sha256:'b',mediaId:'B',receipt:{nodeId:'20'},nodes:[{nodeId:'30'},{nodeId:'40'}],route:{clips:[{in_s:1,out_s:5},{in_s:2,out_s:6}]},timeline:{clips:[{shotId:'50'},{shotId:'60'}]}}};
const shots=['a','b'].map((name,i)=>({id:i?'60':'50',seq:i+1,genVideoStatus:'GENERATING_COMPLETED',shotVideoUrl:`https://seko-resource.sensetime.com/STS/${name}.mp4`,shotVideoStartTime:i+1,shotVideoEndTime:i+5,duration:4,bindAudioSync:false}));
test('two ordered and distinctly sourced trimmed shots',()=>assert.equal(sekoMultiTimeline(s,'100',shots,2).clips.length,2));
test('reverse, repeat, wrong trim and missing clip rejected',()=>{
 for(const rows of [[...shots].reverse(),[shots[0],shots[0]],[shots[0]],shots.map((x,i)=>({...x,shotVideoStartTime:i?0:1})),shots.map(x=>({...x,shotVideoUrl:shots[0].shotVideoUrl}))])assert.throws(()=>sekoMultiTimeline(s,'100',rows,2));
});
test('node validates actual bytes, type and persisted status',()=>{
 const n={id:'1',genId:'2',nodeType:'VIDEO',genStatus:'GENERATING_COMPLETED',duration:8,genFileUrl:'https://seko-resource.sensetime.com/STS/b.mp4'};
 assert.equal(sekoMultiNode(n,{path:'STS/b.mp4',sha256:'b'},'b').nodeId,'1');
 assert.throws(()=>sekoMultiNode(n,{path:'STS/b.mp4',sha256:'b'},'a'));
 assert.throws(()=>sekoMultiNode({...n,nodeType:'IMAGE'},{path:'STS/b.mp4',sha256:'b'},'b'));
});
test('each native trim uses its own range with automatic retry disabled',async()=>{
 let count=0;const m={k:{put:(path,opts)=>{count++;assert.equal(path,'guodong-studio/v1/shots/60/trim');assert.deepEqual(opts,{json:{bindAudioSync:false,startTime:2,endTime:6},retry:0});return {json:async()=>{throw Error('unknown');}};}}};
 await assert.rejects(sekoMultiTrim(m,'60',{in_s:2,out_s:6}));assert.equal(count,1);
});
