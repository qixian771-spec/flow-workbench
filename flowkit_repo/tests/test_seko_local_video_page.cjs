const test=require('node:test');const assert=require('node:assert/strict');
const {verifySekoLocalVideoNode:verify}=require('../scripts/seko_local_workflow_page.js');
const s={jobId:'j',canvasId:'c',storyId:'s',receipt:{nodeId:'1'},video:{stepId:'generate_video:1',
  requestId:'r',mediaId:'m',sha256:'hash',sourceImageMediaId:'i',sourceImageNodeId:'1',upload:{path:'STS/video.mp4'}}};
const r={nodeId:'2',nodeGenId:'3'},n={node:{id:'2',genId:'3',genStatus:'GENERATING_COMPLETED',nodeType:'VIDEO',genFileUrl:'https://example.com/STS/video.mp4'}};
const meta={duration:8,width:1280,height:720};
test('video receipt binds new node and real video geometry',()=>assert.equal(verify(s,r,n,'hash',meta).nodeType,'VIDEO'));
test('image reuse, wrong node/gen/hash/type/status/path/geometry rejected',()=>{
 for(const [key,value] of [['id','1'],['genId','4'],['genStatus','PENDING'],['nodeType','IMAGE'],['genFileUrl','https://example.com/other.mp4']])
   assert.throws(()=>verify(s,r,{node:{...n.node,[key]:value}},'hash',meta));
 assert.throws(()=>verify(s,r,n,'different',meta));
 for(const m of [{...meta,duration:6},{...meta,width:720},{...meta,height:1280},{...meta,duration:NaN}])assert.throws(()=>verify(s,r,n,'hash',m));
});
