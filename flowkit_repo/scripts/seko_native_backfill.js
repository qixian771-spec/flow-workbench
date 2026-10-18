/* Completes an already submitted Flow job using Seko's own upload and moderation.
 * Execute in the same authorized page as seko_generation_hook.js. Input bytes are
 * transferred in bounded CUA messages; the page verifies SHA-256 before upload.
 */
async function sekoNativeBackfill(input) {
  const bridge = window.__sekoFlowBridge;
  const job = bridge.snapshot().jobs.find(j => j.jobId === input.jobId);
  if (!job || job.state !== 'submitted' || input.duration !== 8)
    throw new Error('Expected submitted eight-second Flow job');
  const m = await import('/assets/LoginContext-CFHyujin.js');
  const canvas = await import('/assets/canvas-BZat8bJg.js');
  const moderation = await import('/assets/useOSSUploader-BaPQIV7u.js');
  const current = await canvas.an(job.canvasId);
  if (current.storyId !== input.storyId) throw new Error('Story ownership mismatch');
  const identity = url => {const u=new URL(url);if(u.protocol!=='https:')throw new Error('HTTPS required');return u.host+u.pathname;};
  const shots = await m.aj(input.storyId);
  const before = shots.find(s => s.id === input.shotId);
  if (!before || identity(before.shotVideoUrl) !== identity(input.expectedMediaUrl) ||
      before.duration !== 8 || before.shotVideoStartTime !== 0 || before.shotVideoEndTime !== 8)
    throw new Error('Shot changed or unsupported trim; refusing overwrite');
  const bytes = new Blob(window.__flowUploadParts, {type:'video/mp4'});
  delete window.__flowUploadParts;
  const digest = [...new Uint8Array(await crypto.subtle.digest('SHA-256', await bytes.arrayBuffer()))]
    .map(x=>x.toString(16).padStart(2,'0')).join('');
  if (digest !== input.sha256) throw new Error('Transferred media digest mismatch');
  const state = {phase:'uploading',jobId:job.jobId,before,sourceSha256:digest};
  window.__sekoBackfills ??= {};
  if (window.__sekoBackfills[job.jobId]) throw new Error('Backfill already started; inspect existing outcome');
  window.__sekoBackfills[job.jobId]=state;
  bridge.beginBackfill(job.jobId);
  try {
    const file = new File([bytes], 'Flow-native-'+job.jobId+'.mp4', {type:'video/mp4'});
    state.upload = await m.Y(file,{videoDurationSeconds:8}).promise;
    state.phase='moderating';
    state.moderation=await moderation.m({videoPath:state.upload.path});
    if(!state.moderation.passed)throw new Error('Seko video moderation did not pass');
    state.phase='creating-real-node';
    state.receipt=await canvas.D({bizId:'',canvasId:job.canvasId,storyId:input.storyId,
      fileSource:'USER_UPLOAD',nodeType:'VIDEO',filePath:state.upload.path,duration:8,
      prompt:job.nativeRequest.videoPrompt});
    state.node=await canvas.b(state.receipt.nodeId);
    if(state.node.node.genStatus!=='GENERATING_COMPLETED' || state.node.node.duration!==8 ||
       new URL(state.node.node.genFileUrl).pathname!=='/'+state.upload.path)
      throw new Error('Seko node did not persist the uploaded result');
    // Resume the native UI only with an actual persisted Seko node receipt.
    bridge.finish(job.jobId,state.receipt);
    state.phase='refreshing-shot';
    const fresh=(await m.aj(input.storyId)).find(s=>s.id===input.shotId);
    if(identity(fresh.shotVideoUrl)!==identity(before.shotVideoUrl) ||
       ['seq','seqValue','duration','shotVideoStartTime','shotVideoEndTime','bindAudioSync','linesAudioEnabledFlag'].some(k=>fresh[k]!==before[k]))
      throw new Error('Concurrent timeline change');
    await canvas.aq({canvasId:job.canvasId,nodes:[{nodeId:state.receipt.nodeId,
      action:'REPLACE',shotId:before.id,seq:String(before.seq),seqValue:String(before.seqValue)}]});
    state.after=(await m.aj(input.storyId)).find(s=>s.id===before.id);
    if(state.after.genVideoStatus!=='GENERATING_COMPLETED' ||
       identity(state.after.shotVideoUrl)!==identity(state.node.node.genFileUrl) ||
       ['id','seq','seqValue','duration','shotVideoStartTime','shotVideoEndTime','bindAudioSync','linesAudioEnabledFlag'].some(k=>state.after[k]!==before[k]))
      throw new Error('Timeline backfill verification failed');
    state.phase='complete';
  } catch(error) {
    state.phase='failed';state.error=String(error);
    const phase=bridge.snapshot().jobs.find(j=>j.jobId===job.jobId)?.state;
    if(phase!=='complete'&&phase!=='failed')bridge.fail(job.jobId,String(error));
    throw error;
  }
  return state;
}

async function sekoNativeRender(input) {
  const m=await import('/assets/LoginContext-CFHyujin.js');
  const canvas=await import('/assets/canvas-BZat8bJg.js');
  const current=await canvas.an(input.canvasId);
  if(current.storyId!==input.storyId)throw new Error('Story ownership mismatch');
  const shots=await m.aj(input.storyId);
  if(input.jobs.length!==2 || shots.length!==2 || new Set(input.jobs.map(x=>x.shotId)).size!==2)
    throw new Error('Exactly two explicitly mapped shots required');
  for(const target of input.jobs){
    const state=window.__sekoBackfills?.[target.jobId];
    const shot=shots.find(x=>x.id===target.shotId);
    if(state?.phase!=='complete'||!shot||shot.genVideoStatus!=='GENERATING_COMPLETED'||
      shot.duration!==8||shot.shotVideoStartTime!==0||shot.shotVideoEndTime!==8||
      new URL(shot.shotVideoUrl).origin!==new URL(state.node.node.genFileUrl).origin||
      new URL(shot.shotVideoUrl).pathname!==new URL(state.node.node.genFileUrl).pathname)
      throw new Error('Not all shots are the verified new Flow results');
  }
  if(window.__sekoNativeRender)throw new Error('Render already reserved; inspect outcome');
  window.__sekoNativeRender={phase:'submitting',storyId:input.storyId,shots};
  const receipt=await m.bW(input.storyId,{captionOption:1,splitOption:0,watermarkOption:1});
  Object.assign(window.__sekoNativeRender,{phase:'submitted',receipt});
  return window.__sekoNativeRender;
}
