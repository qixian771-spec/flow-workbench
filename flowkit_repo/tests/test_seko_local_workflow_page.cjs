const test=require('node:test');
const assert=require('node:assert/strict');
const {verifySekoLocalNode}=require('../scripts/seko_local_workflow_page.js');
const state={jobId:'run',stepId:'generate_image:1',requestId:'req',mediaId:'media',sha256:'hash',canvasId:'canvas',storyId:'story'};
const upload={path:'STS/local.png'};
const receipt={nodeId:'123',nodeGenId:'456'};
const detail={node:{id:'123',genId:'456',nodeType:'IMAGE',genStatus:'GENERATING_COMPLETED',genFileUrl:'https://seko-resource.sensetime.com/STS/local.png'}};
test('persisted image receipt carries the original local run and step',()=>{
 const r=verifySekoLocalNode(state,upload,receipt,detail,'hash');
 assert.equal(r.jobId,'run');assert.equal(r.stepId,'generate_image:1');assert.equal(r.nodeGenId,'456');
});
test('upload alone, incorrect generation, stale URL, wrong hash and wrong node are rejected',()=>{
 for(const [field,value] of [['id','789'],['genId','999'],['genStatus','ALGO_GENERATION'],['nodeType','VIDEO'],['genFileUrl','https://example.com/other']]){
  assert.throws(()=>verifySekoLocalNode(state,upload,receipt,{node:{...detail.node,[field]:value}},'hash'));
 }
 assert.throws(()=>verifySekoLocalNode(state,upload,receipt,detail,'wrong'));
 assert.throws(()=>verifySekoLocalNode(state,upload,receipt,{},'hash'));
});
