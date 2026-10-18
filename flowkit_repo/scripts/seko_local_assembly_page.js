/* Current-build native editing; no uploads, generation, or local rendering. */
function sekoAssemblyNode(s, detail, nodeId) {
  const n=detail.node,a=s.assembly;
  if(!n||n.id!==nodeId||n.nodeType!=='VIDEO'||n.genStatus!=='GENERATING_COMPLETED'||
    new URL(n.genFileUrl).pathname!=='/'+a.sourcePath||n.duration!==8)
    throw Error('Assembly node does not contain the accepted video');
  return n;
}
function sekoAssemblyTimeline(s,shots,trimmed){
  const a=s.assembly;
  if(shots.length!==1)throw Error('Isolated export requires exactly one shot');
  const x=shots[0],start=trimmed?1:0,end=trimmed?7:8;
  if(x.genVideoStatus!=='GENERATING_COMPLETED'||new URL(x.shotVideoUrl).pathname!=='/'+a.sourcePath||
     x.seq!==1||x.shotVideoStartTime!==start||x.shotVideoEndTime!==end||
     (trimmed&&x.bindAudioSync!==false)||!(trimmed?[6,8]:[8]).includes(x.duration)||
     (trimmed&&x.id!==a.timeline.shotId))throw Error('Native timeline source or trim mismatch');
  return {storyId:a.storyId,shotId:x.id,nodeId:a.target.nodeId,filePath:a.sourcePath,
    status:x.genVideoStatus,seq:x.seq,start:x.shotVideoStartTime,end:x.shotVideoEndTime,
    duration:x.duration,bindAudioSync:x.bindAudioSync};
}
function sekoAssemblyTrim(m,shotId){
  if(typeof shotId!=='string'||!/^\d+$/.test(shotId))throw Error('Exact shot ID required');
  // Same authenticated native client/path/body as shot-BLVxxKZl.i; explicitly
  // disable its client's default PUT retries when the outcome is uncertain.
  return m.k.put(`guodong-studio/v1/shots/${shotId}/trim`,
    {json:{bindAudioSync:false,startTime:1,endTime:7},retry:0}).json();
}
function createSekoAssemblyRunner({call,load,sha,emit,fail}){
  let timer;
  const stepId='assemble_export:1';
  const cp=(s,phase,extra={})=>call(`jobs/${s.jobId}/checkpoint`,'POST',
    {stepId,expectedPhase:s.assembly.phase,phase,...extra});
  const get=async(jobId,canvasId)=>{
    const s=(await call('jobs?canvasId='+canvasId)).find(x=>x.jobId===jobId);
    if(!s)throw Error('Original local task missing');return s;
  };
  const readBytes=async n=>{const r=await fetch(n.genFileUrl);if(!r.ok)throw Error('Source readback unavailable');return sha(await r.arrayBuffer());};
  async function tick(jobId,canvasId){
    return navigator.locks.request('seko-local-'+jobId,{ifAvailable:true},async lock=>{
      if(!lock)return;
      let s=await get(jobId,canvasId);
      try{
        if(s.assembly.phase==='complete'){clearInterval(timer);emit('同任务自动出片完成',{state:s});return s;}
        const [m,c]=await load();
        if(s.assembly.phase==='reserved'){
          const source=sekoAssemblyNode(s,await c.b(s.assembly.sourceNodeId),s.assembly.sourceNodeId);
          if(await readBytes(source)!==s.assembly.sourceSha256)throw Error('Original Seko video changed');
          s=await cp(s,'creating-canvas');emit('建立本任务的独立剪辑工程',{state:s});
          const created=await c.H({bizId:'',filePath:s.assembly.sourcePath,fileSource:'USER_UPLOAD',
            imageModel:'',nodeType:'VIDEO',prompt:s.video.plan.prompt,storyId:'',visionRatioId:1,duration:8});
          const n=sekoAssemblyNode(s,await c.b(created.canvasNodeId),created.canvasNodeId);
          if(!(await c.ao(created.canvasId)).some(x=>x.id===n.id))throw Error('New node absent from target canvas');
          s=await cp(s,'canvas-ready',{target:{canvasId:created.canvasId,nodeId:n.id,nodeGenId:n.genId,
            filePath:s.assembly.sourcePath,readbackSha256:await readBytes(n)}});
        }
        if(s.assembly.phase==='canvas-ready'){
          const target=await c.an(s.assembly.target.canvasId);
          if(target.storyId&&(await m.aj(target.storyId)).length)throw Error('Target timeline is not empty');
          s=await cp(s,'adding');emit('加入原生时间线',{state:s});
          const receipts=await c.aq({canvasId:s.assembly.target.canvasId,resolutionType:1,visionRatioId:1,
            nodes:[{nodeId:s.assembly.target.nodeId,action:'CREATE',seq:'1',seqValue:'1'}]});
          if(receipts.length!==1||receipts[0].nodeId!==s.assembly.target.nodeId)throw Error('Timeline receipt mismatch');
          const storyId=receipts[0].storyId;
          if((await c.an(s.assembly.target.canvasId)).storyId!==storyId)throw Error('Target story ownership mismatch');
          s.assembly.storyId=storyId;
          const timeline=sekoAssemblyTimeline(s,await m.aj(storyId),false);
          if(timeline.shotId!==receipts[0].shotId)throw Error('Created shot identity changed');
          s=await cp(s,'timeline-ready',{timeline});
        }
        if(s.assembly.phase==='timeline-ready'){
          s.assembly.storyId=s.assembly.timeline.storyId;
          sekoAssemblyTimeline(s,await m.aj(s.assembly.storyId),false);
          s=await cp(s,'trimming');emit('原生裁剪：保留第 1–7 秒',{state:s});
          await sekoAssemblyTrim(m,s.assembly.timeline.shotId);
          s.assembly.storyId=s.assembly.timeline.storyId;
          s=await cp(s,'trimmed',{timeline:sekoAssemblyTimeline(s,await m.aj(s.assembly.storyId),true)});
        }
        if(s.assembly.phase==='trimmed'){
          s.assembly.storyId=s.assembly.timeline.storyId;
          sekoAssemblyTimeline(s,await m.aj(s.assembly.storyId),true);
          s=await cp(s,'rendering');emit('Seko 原生导出中',{state:s});
          const render=await m.bW(s.assembly.timeline.storyId,s.assembly.route.render_options);
          s=await cp(s,'render-submitted',{render});
        }
        if(s.assembly.phase==='render-submitted'){
          const r=await m.bV(s.assembly.timeline.storyId,s.assembly.render.id);
          if(r.id!==s.assembly.render.id)throw Error('Render status belongs to another task');
          if(['INITIALIZATION','GENERATING'].includes(r.renderVideoStatus)){emit('等待 Seko 成片',{state:s});return s;}
          if(r.renderVideoStatus!=='GENERATING_COMPLETED')throw Error('Native render failed: '+r.renderVideoStatus);
          s=await cp(s,'render-ready',{renderStatus:r});
        }
        if(s.assembly.phase==='render-ready'){
          emit('核验成片时长、解码与来源画面',{state:s});
          s=await call(`jobs/${jobId}/collect`,'POST',{stepId});
        }
        if(s.assembly.phase!=='complete')throw Error(s.assembly.error||'Unknown write; inspect '+s.assembly.phase);
        clearInterval(timer);emit('同任务自动出片完成',{state:s});return s;
      }catch(error){
        clearInterval(timer);
        // Never rewrite an unknown checkpoint or resend its external mutation.
        const fresh=await get(jobId,canvasId);
        if(fresh.assembly.phase===s.assembly.phase&&fresh.assembly.phase!=='complete'&&fresh.assembly.phase!=='needs-inspection')
          await cp(fresh,'needs-inspection',{error:String(error)});
        fail(error);throw error;
      }
    });
  }
  async function start(jobId,canvasId){
    clearInterval(timer);
    let s=await get(jobId,canvasId);
    s=await call(`jobs/${jobId}/checkpoint`,'POST',{action:'start_assembly',stepId,
      videoMediaId:s.video.mediaId,videoNodeId:s.video.receipt.nodeId,
      editManifest:s.video.editManifest,
      in_s:1,out_s:7});
    const result=await tick(jobId,canvasId);
    if(result?.assembly.phase==='render-submitted')timer=setInterval(()=>tick(jobId,canvasId).catch(fail),5000);
    return result;
  }
  return {start,tick};
}
if(typeof module!=='undefined')module.exports={sekoAssemblyNode,sekoAssemblyTimeline,sekoAssemblyTrim};
