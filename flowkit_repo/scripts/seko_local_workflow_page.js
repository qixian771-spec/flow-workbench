/* Local Seko workflow upload worker. Existing extension relay, no new permissions.
 * The server owns run/step state; this page never emits vendor Agent completion.
 * Exact observed build imports fail explicitly when Seko changes the build.
 */
function verifySekoLocalNode(state, upload, receipt, detail, readbackSha256) {
  const node = detail.node;
  if (!node || node.id !== receipt.nodeId || node.genId !== receipt.nodeGenId || node.genStatus !== 'GENERATING_COMPLETED' ||
      node.nodeType !== 'IMAGE' || new URL(node.genFileUrl).pathname !== '/' + upload.path ||
      readbackSha256 !== state.sha256 || !/^\d+$/.test(receipt.nodeGenId))
    throw new Error('Persisted Seko image identity or bytes mismatch');
  return {jobId:state.jobId,stepId:state.stepId,requestId:state.requestId,mediaId:state.mediaId,
    sha256:state.sha256,canvasId:state.canvasId,storyId:state.storyId,
    nodeId:receipt.nodeId,nodeGenId:receipt.nodeGenId,nodeStatus:node.genStatus,
    readbackSha256,filePath:upload.path};
}

function verifySekoLocalVideoNode(state, receipt, detail, readbackSha256, meta) {
  const v=state.video,node=detail.node;
  if(!node||node.id!==receipt.nodeId||node.genId!==receipt.nodeGenId||
     node.genStatus!=='GENERATING_COMPLETED'||node.nodeType!=='VIDEO'||
     new URL(node.genFileUrl).pathname!=='/'+v.upload.path||readbackSha256!==v.sha256||
     !/^\d+$/.test(receipt.nodeGenId)||node.id===state.receipt.nodeId||
     !Number.isFinite(meta.duration)||Math.abs(meta.duration-8)>.1||meta.width!==1280||meta.height!==720)
    throw new Error('Persisted Seko video identity, bytes or metadata mismatch');
  return {jobId:state.jobId,canvasId:state.canvasId,storyId:state.storyId,stepId:v.stepId,
    requestId:v.requestId,mediaId:v.mediaId,sha256:v.sha256,sourceImageMediaId:v.sourceImageMediaId,
    sourceImageNodeId:v.sourceImageNodeId,nodeId:receipt.nodeId,nodeGenId:receipt.nodeGenId,
    nodeStatus:node.genStatus,nodeType:node.nodeType,filePath:v.upload.path,readbackSha256,
    duration:meta.duration,width:meta.width,height:meta.height};
}

function installSekoLocalWorkflow() {
  if (window.__sekoLocalWorkflow) throw new Error('Local worker already installed in this tab');
  const pending = new Map();
  const status = {phase:'idle',jobId:null,error:null,events:[],blockedVendorRequests:[]};
  const emit = (phase, extra={}) => {
    Object.assign(status,{phase},extra);
    status.events.push({phase,at:new Date().toISOString()});
    let panel=document.getElementById('seko-local-workflow-status');
    if(!panel){panel=document.createElement('div');panel.id='seko-local-workflow-status';
      panel.setAttribute('role','status');
      Object.assign(panel.style,{position:'fixed',top:'12px',right:'12px',zIndex:'2147483647',
        background:'#173a32',color:'white',padding:'12px',borderRadius:'8px',maxWidth:'410px'});
      document.body.append(panel);}
    const route=['assemble_export:1','multishot_export:1'].includes(status.state?.activeStepId)?'Seko 原生剪辑导出':'GPT-6.1-Sol → Flow';
    panel.textContent=`本地 Seko · ${route} · ${phase}` + (status.error?' · '+status.error:'');
  };
  const call = (path,method='GET',body) => new Promise((resolve,reject)=>{
    const id=crypto.randomUUID();
    const timer=setTimeout(()=>{pending.delete(id);reject(new Error('Bridge result unknown; inspect the same job'));},240000);
    pending.set(id,{resolve,reject,timer});
    window.postMessage({source:'flowkit-seko-page',id,path,method,body},location.origin);
  });
  window.addEventListener('message',event=>{
    if(event.source!==window||event.origin!==location.origin||event.data?.source!=='flowkit-seko-extension')return;
    const item=pending.get(event.data.id);if(!item)return;
    pending.delete(event.data.id);clearTimeout(item.timer);
    event.data.error?item.reject(new Error(event.data.error)):item.resolve(event.data.value);
  });
  const previousFetch=window.fetch;
  window.fetch=function(input,options){
    const url=new URL(typeof input==='string'||input instanceof URL?input:input.url,location.origin);
    const method=(options?.method||input?.method||'GET').toUpperCase();
    if(url.origin===location.origin && method!=='GET' &&
       (/\/canvas-node\/(?:gen-|regenerate|multi-ref|video-retake|image-lighting)/.test(url.pathname)||
        /\/seko-agent-canvas\/v1\/agent\/run/.test(url.pathname)||
        /\/openapi\/v1\/(?:plan|story)-tasks/.test(url.pathname))){
      status.blockedVendorRequests.push({path:url.pathname,method});
      return Promise.reject(new Error('This local run does not dispatch vendor generation'));
    }
    return previousFetch.call(this,input,options);
  };
  const sha = async bytes => [...new Uint8Array(await crypto.subtle.digest('SHA-256',bytes))]
    .map(x=>x.toString(16).padStart(2,'0')).join('');
  let modules, timer;
  const load = async()=>{
    if(!modules)modules=await Promise.all([
      import(location.origin+'/assets/LoginContext-Dre9Pek8.js'),import(location.origin+'/assets/canvas-BLeYbv0U.js'),
      import(location.origin+'/assets/useOSSUploader-BWv-OPvK.js')]);
    return modules;
  };
  const checkpoint=(s,phase,extra={})=>call(`jobs/${s.jobId}/checkpoint`,'POST',
    {expectedPhase:s.phase,stepId:s.stepId,phase,...extra});
  async function tick(jobId,canvasId) {
    return navigator.locks.request('seko-local-'+jobId,{ifAvailable:true},async lock=>{
      if(!lock)return;
      let state=(await call('jobs?canvasId='+canvasId)).find(s=>s.jobId===jobId);
      if(!state||state.workflow!=='seko-public-local-v1')throw new Error('Local run missing');
      if(state.phase==='submitted')state=await call(`jobs/${jobId}/collect`,'POST',{});
      emit(state.phase,{jobId,state});
      if(state.phase==='submitted')return;
      if(state.phase==='complete'){
        clearInterval(timer);emit('同一任务已继续 · 视频待执行',{state});return;
      }
      if(['needs-inspection','planning','creating-video','creating-scene','submitting',
          'uploading','creating-node','backfilled','continuing'].includes(state.phase))
        throw new Error('Stored operation requires inspection: '+state.phase);
      const [m,canvas,moderation]=await load();
      const current=await canvas.an(canvasId);
      if(current.canvasId!==state.canvasId||current.storyId!==state.storyId)
        throw new Error('Seko canvas/story ownership changed');
      if(state.phase==='ready'){
        const parts=[];
        for(let offset=0;offset<state.size;){
          const c=await call(`jobs/${jobId}/media?offset=${offset}`);
          const bytes=Uint8Array.from(atob(c.base64),v=>v.charCodeAt(0));
          if(c.offset!==offset||!c.length||bytes.length!==c.length)throw new Error('Incomplete Flow media');
          parts.push(bytes);offset+=c.length;
        }
        if(!['image/png','image/jpeg'].includes(state.mimeType))throw new Error('Unsupported verified image type');
        const blob=new Blob(parts,{type:state.mimeType});
        if(blob.size!==state.size||await sha(await blob.arrayBuffer())!==state.sha256)
          throw new Error('Flow transfer hash mismatch');
        state=await checkpoint(state,'uploading');emit('上传 Flow 新图');
        const upload=await m.Y(new File([blob],jobId+(state.mimeType==='image/png'?'.png':'.jpg'),{type:state.mimeType})).promise;
        state=await checkpoint(state,'uploaded',{upload:{path:upload.path}});
      }
      if(state.phase==='uploaded'){
        const checked=await moderation.m({imagePath:state.upload.path});
        if(!checked.passed)throw new Error('Seko image moderation rejected');
        state=await checkpoint(state,'creating-node');emit('回填并核验原站素材');
        const receipt=await canvas.D({bizId:'',canvasId:state.canvasId,storyId:state.storyId,
          fileSource:'USER_UPLOAD',nodeType:'IMAGE',filePath:state.upload.path,
          prompt:state.plan.image_prompt});
        const detail=await canvas.b(receipt.nodeId);
        if(!(await canvas.ao(state.canvasId)).some(n=>n.id===receipt.nodeId))
          throw new Error('Created image is not a member of the intended canvas');
        const response=await fetch(detail.node.genFileUrl);
        if(!response.ok)throw new Error('Seko readback failed');
        const verified=verifySekoLocalNode(state,state.upload,receipt,detail,
          await sha(await response.arrayBuffer()));
        status.receipt=verified;
        emit('素材已核验 · 同一任务继续文字编排');
        state=await checkpoint(state,'backfilled',{receipt:verified});
        status.state=state;
        if(state.phase!=='complete')throw new Error(state.error||'Local continuation did not complete');
        clearInterval(timer);emit('同一任务已继续 · 视频待执行',{state});
      }
    });
  }
  const videoCheckpoint=(s,phase,extra={})=>call(`jobs/${s.jobId}/checkpoint`,'POST',
    {expectedPhase:s.video.phase,stepId:'generate_video:1',phase,...extra});
  const videoMeta = bytes => new Promise((resolve,reject)=>{
    const url=URL.createObjectURL(new Blob([bytes],{type:'video/mp4'}));
    const player=document.createElement('video');player.preload='metadata';
    const finish=(error)=>{clearTimeout(timeout);URL.revokeObjectURL(url);
      error?reject(error):resolve({duration:player.duration,width:player.videoWidth,height:player.videoHeight});};
    const timeout=setTimeout(()=>finish(new Error('Video metadata timeout')),15000);
    player.onloadedmetadata=()=>finish();player.onerror=()=>finish(new Error('Invalid readback video'));
    player.src=url;
  });
  async function tickVideo(jobId,canvasId){
    return navigator.locks.request('seko-local-'+jobId,{ifAvailable:true},async lock=>{
      if(!lock)return;
      let state=(await call('jobs?canvasId='+canvasId)).find(s=>s.jobId===jobId);
      if(!state?.video)throw new Error('Same local video step missing');
      if(state.video.phase==='submitted')state=await call(`jobs/${jobId}/collect`,'POST',{stepId:'generate_video:1'});
      emit('视频 · '+state.video.phase,{jobId,state});
      if(state.video.phase==='submitted')return;
      if(state.video.phase==='complete'){
        clearInterval(timer);emit('同一任务已继续 · 剪辑待执行',{state});return;
      }
      if(!['ready','uploaded'].includes(state.video.phase))
        throw new Error(state.video.error||'Video operation requires inspection: '+state.video.phase);
      const [m,canvas,moderation]=await load();
      const current=await canvas.an(canvasId);
      if(current.canvasId!==state.canvasId||current.storyId!==state.storyId)
        throw new Error('Video canvas/story changed');
      if(state.video.phase==='ready'){
        const parts=[];
        for(let offset=0;offset<state.video.size;){
          const c=await call(`jobs/${jobId}/media?offset=${offset}&kind=video`);
          const bytes=Uint8Array.from(atob(c.base64),v=>v.charCodeAt(0));
          if(c.offset!==offset||!c.length||bytes.length!==c.length)throw new Error('Incomplete video transfer');
          parts.push(bytes);offset+=c.length;
        }
        const blob=new Blob(parts,{type:'video/mp4'});
        if(blob.size!==state.video.size||await sha(await blob.arrayBuffer())!==state.video.sha256)
          throw new Error('Flow video transfer hash mismatch');
        state=await videoCheckpoint(state,'uploading');emit('上传 Omni 新视频');
        const upload=await m.Y(new File([blob],jobId+'.mp4',{type:'video/mp4'}),{videoDurationSeconds:8}).promise;
        state=await videoCheckpoint(state,'uploaded',{upload:{path:upload.path}});
      }
      const checked=await moderation.m({videoPath:state.video.upload.path});
      if(!checked.passed)throw new Error('Seko video moderation rejected');
      state=await videoCheckpoint(state,'creating-node');emit('视频回填与字节核验');
      const receipt=await canvas.D({bizId:'',canvasId:state.canvasId,storyId:state.storyId,
        fileSource:'USER_UPLOAD',nodeType:'VIDEO',filePath:state.video.upload.path,duration:8,prompt:state.video.plan.prompt});
      const detail=await canvas.b(receipt.nodeId);
      if(!(await canvas.ao(canvasId)).some(n=>n.id===receipt.nodeId))throw new Error('Video absent from intended canvas');
      const response=await fetch(detail.node.genFileUrl);
      if(!response.ok)throw new Error('Video readback failed');
      const bytes=await response.arrayBuffer();
      const verified=verifySekoLocalVideoNode(state,receipt,detail,await sha(bytes),await videoMeta(bytes));
      status.videoReceipt=verified;
      emit('视频已核验 · GPT-6.1-Sol 同任务续行');
      state=await videoCheckpoint(state,'backfilled',{receipt:verified});
      status.state=state;
      if(state.video.phase!=='complete')throw new Error(state.video.error||'Video continuation incomplete');
      clearInterval(timer);emit('同一任务已继续 · 剪辑待执行',{state});
    });
  }
  async function resumeVideo(jobId,canvasId){
    clearInterval(timer);status.error=null;status.jobId=jobId;
    await tickVideo(jobId,canvasId);
    if(status.state?.video?.phase!=='complete'&&!status.error)
      timer=setInterval(()=>tickVideo(jobId,canvasId).catch(fail),5000);
    return status;
  }
  async function startVideo(jobId,canvasId){
    try{
      const state=(await call('jobs?canvasId='+canvasId)).find(s=>s.jobId===jobId);
      if(!state)throw new Error('Original local job missing');
      const [,canvas]=await load();
      const current=await canvas.an(canvasId);
      if(current.storyId!==state.storyId)throw new Error('Original canvas/story mismatch');
      if(!state.video){
        const node=await canvas.b(state.receipt.nodeId);
        const response=await fetch(node.node.genFileUrl);
        if(!response.ok)throw new Error('Original image readback unavailable');
        verifySekoLocalNode(state,state.upload,state.receipt,node,await sha(await response.arrayBuffer()));
      }
      emit('GPT-6.1-Sol 视频提示词 → Omni 提交',{jobId});
      await call(`jobs/${jobId}/checkpoint`,'POST',{action:'start_video',stepId:'generate_video:1',
        imageMediaId:state.mediaId,imageNodeId:state.receipt.nodeId,
        sourcePromptHash:await sha(new TextEncoder().encode(JSON.stringify(state.nextStep.video_prompt)))});
      return await resumeVideo(jobId,canvasId);
    }catch(error){fail(error);throw error;}
  }
  function fail(error){clearInterval(timer);emit('停止',{error:String(error)});}
  async function resume(jobId,canvasId){
    clearInterval(timer);status.error=null;status.jobId=jobId;await tick(jobId,canvasId);
    if(status.state?.phase!=='complete'&&!status.error)
      timer=setInterval(()=>tick(jobId,canvasId).catch(fail),5000);
    return status;
  }
  async function start(input){
    try{
      const [,canvas]=await load();
      const current=await canvas.an(input.canvasId);
      if(current.storyId!==input.storyId)throw new Error('Canvas/story mismatch before start');
      emit('GPT-6.1-Sol 策划与 Flow 提交');
      const state=await call('jobs','POST',input);
      return await resume(state.jobId,state.canvasId);
    }catch(error){fail(error);throw error;}
  }
  async function recheck(jobId,canvasId){
    await call(`jobs/${jobId}/collect`,'POST',{recheckCompletedMedia:true});
    return resume(jobId,canvasId);
  }
  let assemblyRunner;
  const startAssembly=(jobId,canvasId)=>{
    if(typeof createSekoAssemblyRunner!=='function')throw Error('Explicit assembly adapter must be loaded');
    assemblyRunner??=createSekoAssemblyRunner({call,load,sha,emit,fail});
    return assemblyRunner.start(jobId,canvasId);
  };
  let multiRunner;
  const startMulti=(jobId,canvasId)=>{
    if(typeof createSekoMultiRunner!=='function')throw Error('Explicit multishot adapter must be loaded');
    multiRunner??=createSekoMultiRunner({call,load,sha,emit,fail});
    return multiRunner.start(jobId,canvasId);
  };
  const resumeAssembly=(jobId,canvasId)=>{
    if(typeof createSekoAssemblyRunner!=='function')throw Error('Assembly adapter missing');
    assemblyRunner??=createSekoAssemblyRunner({call,load,sha,emit,fail});
    return assemblyRunner.tick(jobId,canvasId);
  };
  const resumeMulti=(jobId,canvasId)=>{
    if(typeof createSekoMultiRunner!=='function')throw Error('Multishot adapter missing');
    multiRunner??=createSekoMultiRunner({call,load,sha,emit,fail});
    return multiRunner.tick(jobId,canvasId);
  };
  window.__sekoLocalWorkflow={status,start,resume,recheck,startVideo,resumeVideo,startAssembly,startMulti,resumeAssembly,resumeMulti,snapshot:()=>structuredClone(status)};
  emit('等待启动');
  return window.__sekoLocalWorkflow;
}
if(typeof module!=='undefined')module.exports={verifySekoLocalNode,verifySekoLocalVideoNode};
