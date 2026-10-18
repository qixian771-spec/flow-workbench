const {test} = require('node:test');
const assert = require('node:assert/strict');
const {armAgentHandoff,installContinueBarrier} = require('../extension/seko_agent_handoff_probe.js');
const paused = () => ({event:'RunPaused',run_id:'123',session_id:'session',requirements:[{
  id:'requirement',tool:{tool_name:'generate_image',tool_call_id:'tool',requires_user_input:true,
  tool_args:{count:1,vision_ratio_id:'1',resolution_type:'2',prompt:'rain'}}}]});
test('preparation barrier blocks every native continue before a tool is bound',async()=>{
  let native=0;const client={post(){native++;}};const original=client.post;
  const barrier=installContinueBarrier(client);
  await assert.rejects(client.post('seko-agent-canvas/v1/agent/run/999/continue',{}));
  assert.equal(native,0);assert.equal(barrier.blocked,1);barrier.restore();assert.equal(client.post,original);
});
const body = () => ({canvas_id:'2110204684884787202',session_id:'session',user_inputs:{requirement:{prompt:'rain'}}});
test('captures a real-shaped pending generation without calling native continue or claiming completion',async()=>{
  const calls=[];const client={post(...args){calls.push(args);return 'other';}};
  const original=client.post, adapter=armAgentHandoff(client,paused());
  let completed=false;client.post('seko-agent-canvas/v1/agent/run/123/continue',{json:body()}).then(()=>{completed=true;},()=>{});
  await Promise.resolve();assert.equal(completed,false);assert.equal(calls.length,0);
  assert.equal(adapter.state.capture.route.resolvedModel,'BELUGA');assert.equal(adapter.state.phase,'captured');
  await assert.rejects(client.post('seko-agent-canvas/v1/agent/run/123/continue',{json:body()}));
  assert.equal(client.post('unrelated',{}),'other');adapter.restore();assert.equal(client.post,original);
});
test('questionnaire, answered tool, mismatched identity and unsupported settings never dispatch',async()=>{
  for(const mutation of [p=>p.requirements[0].tool.tool_name='ask_user_question',p=>p.requirements[0].tool.answered=true]){
    const p=paused();mutation(p);assert.throws(()=>armAgentHandoff({post(){throw Error('native');}},p));
  }
  for(const mutate of [b=>b.session_id='other',b=>b.canvas_id='other',b=>b.user_inputs.requirement.count=2,
    b=>b.user_inputs.requirement.ref_node_ids=['reference'],b=>b.user_inputs.requirement.resolution_type=3]){
    let calls=0;const client={post(){calls++;}};const adapter=armAgentHandoff(client,paused());const b=body();mutate(b);
    await assert.rejects(client.post('seko-agent-canvas/v1/agent/run/123/continue',{json:b}));
    assert.equal(calls,0);assert.equal(adapter.state.capture,null);adapter.restore();
  }
});
