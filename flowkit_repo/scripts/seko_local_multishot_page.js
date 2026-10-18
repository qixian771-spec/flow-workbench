/* Same-run two-shot export. Every native mutation has a durable preceding checkpoint. */
function sekoMultiSources(s){return [
  {path:s.video.upload.path,sha256:s.video.sha256,mediaId:s.video.mediaId,nodeId:s.video.receipt.nodeId},
  {path:s.multishot.upload.path,sha256:s.multishot.sha256,mediaId:s.multishot.mediaId,nodeId:s.multishot.receipt.nodeId}];}
function sekoMultiNode(n,source,hash){
  if(!n||!/^\d+$/.test(n.id)||!/^\d+$/.test(n.genId)||n.nodeType!=='VIDEO'||
    n.genStatus!=='GENERATING_COMPLETED'||n.duration!==8||new URL(n.genFileUrl).pathname!=='/'+source.path||hash!==source.sha256)
    throw Error('Multishot node/source bytes mismatch');
  return {nodeId:n.id,nodeGenId:n.genId,filePath:source.path,readbackSha256:hash,duration:8,status:n.genStatus};
}
function sekoMultiTimeline(s,storyId,shots,trims){
  const m=s.multishot,src=sekoMultiSources(s);
  if(shots.length!==2||new Set(shots.map(x=>x.id)).size!==2)throw Error('Exactly two distinct timeline shots required');
  return {storyId,clips:shots.map((x,i)=>{
    const trim=i<trims?m.route.clips[i]:{in_s:0,out_s:8};
    if(x.seq!==i+1||x.genVideoStatus!=='GENERATING_COMPLETED'||
      new URL(x.shotVideoUrl).pathname!=='/'+src[i].path||x.shotVideoStartTime!==trim.in_s||
      x.shotVideoEndTime!==trim.out_s||(i<trims&&x.bindAudioSync!==false)||
      (trims&&x.id!==m.timeline.clips[i].shotId))throw Error('Wrong clip order/source/trim');
    return {shotId:x.id,nodeId:m.nodes[i].nodeId,filePath:src[i].path,seq:x.seq,start:x.shotVideoStartTime,
      end:x.shotVideoEndTime,duration:x.duration,status:x.genVideoStatus,bindAudioSync:x.bindAudioSync};
  })};
}
function sekoMultiTrim(m,shotId,trim){
  if(!/^\d+$/.test(shotId))throw Error('Invalid shot identity');
  return m.k.put(`guodong-studio/v1/shots/${shotId}/trim`,
    {json:{bindAudioSync:false,startTime:trim.in_s,endTime:trim.out_s},retry:0}).json();
}
function createSekoMultiRunner({call,load,sha,emit,fail}){
  const stepId='multishot_export:1';let timer;
  const get=async(jobId,canvasId)=>{
    const s=(await call('jobs?canvasId='+canvasId)).find(x=>x.jobId===jobId);
    if(!s)throw Error('Same local run missing');return s;
  };
  const cp=(s,phase,extra={})=>call(`jobs/${s.jobId}/checkpoint`,'POST',
    {stepId,expectedPhase:s.multishot.phase,phase,...extra});
  const verifiedNode=async(c,id,source)=>{
    const n=(await c.b(id)).node;
    const r=await fetch(n.genFileUrl);if(!r.ok)throw Error('Native media readback failed');
    return sekoMultiNode(n,source,await sha(await r.arrayBuffer()));
  };
  async function tick(jobId,canvasId){
    return navigator.locks.request('seko-local-'+jobId,{ifAvailable:true},async lock=>{
      if(!lock)return;
      let s=await get(jobId,canvasId);
      try{
        emit('多镜 · '+s.multishot.phase,{state:s,jobId});
        if(s.multishot.phase==='complete'){clearInterval(timer);emit('两镜自动出片完成',{state:s});return s;}
        if(s.multishot.phase==='submitted'){
          s=await call(`jobs/${jobId}/collect`,'POST',{stepId});
          if(s.multishot.phase==='submitted'){emit('等待第二镜 Omni 生成',{state:s});return s;}
        }
        const [m,c,moderation]=await load();
        if(s.multishot.phase==='ready'){
          const current=await c.an(canvasId);
          if(current.storyId!==s.storyId)throw Error('Source canvas ownership changed');
          const parts=[];
          for(let offset=0;offset<s.multishot.size;){
            const chunk=await call(`jobs/${jobId}/media?kind=multishot&offset=${offset}`);
            const bytes=Uint8Array.from(atob(chunk.base64),c=>c.charCodeAt(0));
            if(chunk.offset!==offset||!chunk.length||bytes.length!==chunk.length)throw Error('Incomplete second video transfer');
            parts.push(bytes);offset+=chunk.length;
          }
          const blob=new Blob(parts,{type:'video/mp4'});
          if(blob.size!==s.multishot.size||await sha(await blob.arrayBuffer())!==s.multishot.sha256)throw Error('Second video hash mismatch');
          s=await cp(s,'uploading');emit('回填第二镜真实视频',{state:s});
          const upload=await m.Y(new File([blob],jobId+'-shot-2.mp4',{type:'video/mp4'}),{videoDurationSeconds:8}).promise;
          s=await cp(s,'uploaded',{upload:{path:upload.path}});
        }
        if(s.multishot.phase==='uploaded'){
          if(!(await moderation.m({videoPath:s.multishot.upload.path})).passed)throw Error('Second video moderation rejected');
          s=await cp(s,'creating-node');
          const r=await c.D({bizId:'',canvasId,storyId:s.storyId,fileSource:'USER_UPLOAD',nodeType:'VIDEO',
            filePath:s.multishot.upload.path,duration:8,prompt:s.multishot.plan.prompt});
          if(!(await c.ao(canvasId)).some(n=>n.id===r.nodeId))throw Error('Second video absent from original canvas');
          s=await cp(s,'backfilled',{receipt:await verifiedNode(c,r.nodeId,{path:s.multishot.upload.path,sha256:s.multishot.sha256})});
        }
        if(s.multishot.phase==='backfilled'){
          const src=sekoMultiSources(s);
          if(src[0].mediaId===src[1].mediaId||src[0].sha256===src[1].sha256)throw Error('Repeated video is not multi-shot');
          await verifiedNode(c,src[0].nodeId,src[0]);await verifiedNode(c,src[1].nodeId,src[1]);
          s=await cp(s,'creating-canvas');emit('建立两镜独立剪辑工程',{state:s});
          const r=await c.H({bizId:'',filePath:src[0].path,fileSource:'USER_UPLOAD',imageModel:'',nodeType:'VIDEO',
            prompt:s.video.plan.prompt,storyId:'',visionRatioId:1,duration:8});
          if(!(await c.ao(r.canvasId)).some(n=>n.id===r.canvasNodeId))throw Error('First target node absent');
          s=await cp(s,'canvas-ready',{canvasId:r.canvasId,node:await verifiedNode(c,r.canvasNodeId,src[0])});
        }
        if(s.multishot.phase==='canvas-ready'){
          s=await cp(s,'adding-node');
          const r=await c.D({bizId:'',canvasId:s.multishot.canvasId,storyId:'',fileSource:'USER_UPLOAD',
            nodeType:'VIDEO',filePath:s.multishot.upload.path,duration:8,prompt:s.multishot.plan.prompt});
          if(!(await c.ao(s.multishot.canvasId)).some(n=>n.id===r.nodeId))throw Error('Second target node absent');
          s=await cp(s,'nodes-ready',{node:await verifiedNode(c,r.nodeId,sekoMultiSources(s)[1])});
        }
        if(s.multishot.phase==='nodes-ready'){
          const target=await c.an(s.multishot.canvasId);
          if(target.storyId&&(await m.aj(target.storyId)).length)throw Error('Target timeline is not empty');
          s=await cp(s,'adding-timeline');emit('按 A → B 自动加入时间线',{state:s});
          const r=await c.aq({canvasId:s.multishot.canvasId,resolutionType:1,visionRatioId:1,
            nodes:s.multishot.nodes.map((n,i)=>({nodeId:n.nodeId,action:'CREATE',seq:String(i+1),seqValue:String(i+1)}))});
          if(r.length!==2||new Set(r.map(x=>x.storyId)).size!==1)throw Error('Two-shot native receipts missing');
          const storyId=r[0].storyId;
          if((await c.an(s.multishot.canvasId)).storyId!==storyId)throw Error('Target story ownership changed');
          const timeline=sekoMultiTimeline(s,storyId,await m.aj(storyId),0);
          if(!timeline.clips.every(x=>r.some(y=>y.nodeId===x.nodeId&&y.shotId===x.shotId)))throw Error('Native shot receipts changed');
          s=await cp(s,'timeline-ready',{timeline});
        }
        if(s.multishot.phase==='timeline-ready'){
          sekoMultiTimeline(s,s.multishot.timeline.storyId,await m.aj(s.multishot.timeline.storyId),0);
          s=await cp(s,'trimming-first');await sekoMultiTrim(m,s.multishot.timeline.clips[0].shotId,s.multishot.route.clips[0]);
          s=await cp(s,'first-trimmed',{timeline:sekoMultiTimeline(s,s.multishot.timeline.storyId,await m.aj(s.multishot.timeline.storyId),1)});
        }
        if(s.multishot.phase==='first-trimmed'){
          sekoMultiTimeline(s,s.multishot.timeline.storyId,await m.aj(s.multishot.timeline.storyId),1);
          s=await cp(s,'trimming-second');await sekoMultiTrim(m,s.multishot.timeline.clips[1].shotId,s.multishot.route.clips[1]);
          s=await cp(s,'trimmed',{timeline:sekoMultiTimeline(s,s.multishot.timeline.storyId,await m.aj(s.multishot.timeline.storyId),2)});
        }
        if(s.multishot.phase==='trimmed'){
          sekoMultiTimeline(s,s.multishot.timeline.storyId,await m.aj(s.multishot.timeline.storyId),2);
          s=await cp(s,'rendering');emit('原生导出：两镜硬切衔接',{state:s});
          s=await cp(s,'render-submitted',{render:await m.bW(s.multishot.timeline.storyId,s.multishot.route.render_options)});
        }
        if(s.multishot.phase==='render-submitted'){
          const r=await m.bV(s.multishot.timeline.storyId,s.multishot.render.id);
          if(r.id!==s.multishot.render.id)throw Error('Wrong render identity');
          if(['INITIALIZATION','GENERATING'].includes(r.renderVideoStatus)){emit('等待两镜成片',{state:s});return s;}
          if(r.renderVideoStatus!=='GENERATING_COMPLETED')throw Error('Native two-shot render failed');
          s=await cp(s,'render-ready',{render:r});
        }
        if(s.multishot.phase==='render-ready')s=await call(`jobs/${jobId}/collect`,'POST',{stepId});
        if(s.multishot.phase!=='complete')throw Error(s.multishot.error||'Unknown write; inspect '+s.multishot.phase);
        clearInterval(timer);emit('两镜自动出片完成',{state:s});return s;
      }catch(error){
        clearInterval(timer);const fresh=await get(jobId,canvasId);
        if(fresh.multishot.phase===s.multishot.phase&&!['complete','needs-inspection'].includes(fresh.multishot.phase))
          await cp(fresh,'needs-inspection',{error:String(error)});
        fail(error);throw error;
      }
    });
  }
  async function start(jobId,canvasId){
    clearInterval(timer);let s=await get(jobId,canvasId);
    emit('GPT-6.1-Sol 第二镜策划 → Omni',{jobId,state:s});
    await call(`jobs/${jobId}/checkpoint`,'POST',{action:'start_multishot',stepId,
      sourceMediaId:s.video.mediaId,sourceImageMediaId:s.mediaId,previousRenderId:s.assembly.render.id});
    const r=await tick(jobId,canvasId);
    if(['submitted','render-submitted'].includes(r?.multishot.phase))timer=setInterval(()=>tick(jobId,canvasId).catch(fail),5000);
    return r;
  }
  return {start,tick};
}
if(typeof module!=='undefined')module.exports={sekoMultiSources,sekoMultiNode,sekoMultiTimeline,sekoMultiTrim};
