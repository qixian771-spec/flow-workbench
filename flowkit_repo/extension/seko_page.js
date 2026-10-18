/* Automatically loaded by the existing Flow Kit extension on every Seko refresh. */
(() => {
  const pending=new Map(), active=new Map();
  const status={version:1,phase:'starting',jobs:[],error:null};
  const request=(path,method='GET',body)=>new Promise((resolve,reject)=>{
    const id=crypto.randomUUID();
    const timeout=setTimeout(()=>{pending.delete(id);reject(new Error('Bridge response unknown; inspect stored job before retrying'));},240000);
    pending.set(id,{resolve,reject,timeout});
    window.postMessage({source:'flowkit-seko-page',id,path,method,body},location.origin);
  });
  window.addEventListener('message',event=>{
    if(event.source!==window||event.origin!==location.origin||event.data?.source!=='flowkit-seko-extension')return;
    const p=pending.get(event.data.id);if(!p)return;
    pending.delete(event.data.id);clearTimeout(p.timeout);
    event.data.error?p.reject(new Error(event.data.error)):p.resolve(event.data.value);
  });
  function show(text,error=false){
    status.message=text;
    let el=document.getElementById('flowkit-seko-status');
    if(!document.body)return;
    if(!el){el=document.createElement('div');el.id='flowkit-seko-status';el.setAttribute('role','status');
      Object.assign(el.style,{position:'fixed',bottom:'4px',left:'12px',zIndex:'2147483647',padding:'7px 12px',
        borderRadius:'6px',fontSize:'12px',color:'white',pointerEvents:'none'});document.body.append(el);}
    el.style.background=error?'#922':'#175a41';el.textContent=text;
  }
  // Guard starts before the application. Unknown video generation must not go upstream.
  const originalFetch=window.fetch;
  window.fetch=function(input,options){
    const url=new URL(typeof input==='string'||input instanceof URL?input:input.url,location.origin);
    if(/\/(?:gen-video|multi-ref-video|regenerate|video-retake)(?:$|\?)/.test(url.pathname))
      return Promise.reject(new Error('Flow Kit: use a mapped first-frame request; native video generation blocked'));
    return originalFetch.call(this,input,options);
  };
  let config,project,m,canvas,moderation;
  const receiptPromise=p=>{p.catch(()=>{});p.json=()=>p;return p;};
  async function enqueue(nativeRequest){
    if(!project)throw new Error('Current canvas is not configured for Flow');
    const jobId=crypto.randomUUID();
    show('Flow 常驻接管 · 正在提交 Omni Flash');
    const state=await request('jobs','POST',{jobId,nativeRequest});
    if(state.phase==='failed')throw new Error(state.error);
    const completion=new Promise((resolve,reject)=>{
      const previous=active.get(state.jobId);
      active.set(state.jobId,{resolve:value=>{previous?.resolve(value);resolve(value);},reject:error=>{previous?.reject(error);reject(error);}});
    });
    run(state).catch(e=>failJob(state.jobId,e));
    return completion;
  }
  function failJob(id,error){status.error=String(error);show('Flow 停止：'+error.message,true);active.get(id)?.reject(error);active.delete(id);}
  async function checkpoint(state,phase,extra={}){
    return request('jobs/'+state.jobId+'/checkpoint','POST',{expectedPhase:state.phase,phase,...extra});
  }
  async function run(initial){
    return navigator.locks.request('flowkit-seko-job-'+initial.jobId,{ifAvailable:true},async lock=>{
      if(!lock)return;
      let state=initial;
      if(state.phase==='submitted')state=await request('jobs/'+state.jobId+'/collect','POST',{});
      if(state.phase==='submitted'){show('Flow Omni Flash 正在生成 · 刷新后可接续');return;}
      if(state.phase==='complete'){active.get(state.jobId)?.resolve(state.receipt);active.delete(state.jobId);return;}
      if(state.phase==='failed')throw new Error(state.error);
      if(state.phase==='needs-inspection')throw new Error(state.error||'Task requires inspection');
      if(['submitting','uploading','creating-node'].includes(state.phase))throw new Error('上次写入结果待检查：'+state.phase+'；未重复提交');
      if(state.phase==='ready'){
        const parts=[];
        for(let offset=0;offset<state.size;){
          const chunk=await request('jobs/'+state.jobId+'/media?offset='+offset);
          if(chunk.offset!==offset||!chunk.length)throw new Error('Incomplete media transfer');
          const bytes=Uint8Array.from(atob(chunk.base64),c=>c.charCodeAt(0));
          if(bytes.length!==chunk.length)throw new Error('Media chunk length mismatch');
          parts.push(bytes);offset+=bytes.length;
        }
        const blob=new Blob(parts,{type:'video/mp4'});
        const hash=[...new Uint8Array(await crypto.subtle.digest('SHA-256',await blob.arrayBuffer()))].map(x=>x.toString(16).padStart(2,'0')).join('');
        if(hash!==state.sha256)throw new Error('Flow file digest mismatch');
        if((await canvas.an(state.canvasId)).storyId!==state.storyId)throw new Error('Canvas/story mismatch');
        state=await checkpoint(state,'uploading');show('Flow 常驻接管 · 正在上传新素材');
        const upload=await m.Y(new File([blob],state.jobId+'.mp4',{type:'video/mp4'}),{videoDurationSeconds:8}).promise;
        state=await checkpoint(state,'uploaded',{upload});
      }
      if(state.phase==='uploaded'){
        const checked=await moderation.m({videoPath:state.upload.path});
        if(!checked.passed){await checkpoint(state,'failed',{error:'Seko moderation rejected'});throw new Error('Seko 内容检查未通过');}
        state=await checkpoint(state,'creating-node');
        const receipt=await canvas.D({bizId:'',canvasId:state.canvasId,storyId:state.storyId,fileSource:'USER_UPLOAD',
          nodeType:'VIDEO',filePath:state.upload.path,duration:8,prompt:state.nativeRequest.videoPrompt});
        const node=await canvas.b(receipt.nodeId);
        if(node.node.genStatus!=='GENERATING_COMPLETED'||new URL(node.node.genFileUrl).pathname!=='/'+state.upload.path)
          throw new Error('Uploaded node verification failed');
        state=await checkpoint(state,'complete',{receipt});
        active.get(state.jobId)?.resolve(receipt);active.delete(state.jobId);
        show('Flow 常驻接管 · 新素材已回填画布');
      }
    });
  }
  async function tick(){
    if(!project)return;
    status.jobs=(await request('jobs?canvasId='+project.canvasId)).filter(job=>job.workflow!=='seko-public-local-v1');
    for(const job of status.jobs){
      if(['failed','needs-inspection'].includes(job.phase))continue;
      try{await run(job);}catch(error){failJob(job.jobId,error);}
    }
    status.attention=status.jobs.filter(x=>['failed','needs-inspection'].includes(x.phase)).map(x=>({jobId:x.jobId,error:x.error}));
    if(status.jobs.length&&status.jobs.every(x=>['complete','failed','needs-inspection'].includes(x.phase)))
      show('Flow 常驻接管 · '+status.jobs.filter(x=>x.phase==='complete').length+' 个完成'+(status.attention.length?' · '+status.attention.length+' 个待检查':''));
  }
  async function start(){
    if(window.__flowkitSekoLocal&&await window.__flowkitSekoLocal.ownsPage()){
      status.phase='local-workflow';return;
    }
    config=await request('config');
    const params=new URLSearchParams(location.search);
    project=config.projects.find(p=>p.canvasId===params.get('canvasId')||p.storyId===params.get('id'));
    if(!config.enabled||!project){status.phase='unconfigured';show('Flow 视频生成已保护 · 当前工程尚未配置',true);return;}
    [m,canvas,moderation]=await Promise.all([import(location.origin+'/assets/LoginContext-CFHyujin.js'),import(location.origin+'/assets/canvas-BZat8bJg.js'),import(location.origin+'/assets/useOSSUploader-BaPQIV7u.js')]);
    for(const client of new Set([m.g,m.k])){
      const original=client.post;
      client.post=function(path,options){
        if(String(path).replace(/^\//,'')==='seko-canvas/v1/canvas-node/gen-video')return receiptPromise(enqueue(structuredClone(options.json)));
        return original.call(this,path,options);
      };
    }
    status.phase='ready';show('Flow 常驻接管已就绪 · Omni Flash · 刷新后自动启用');
    const poll=()=>tick().catch(error=>{status.error=String(error);show('Flow 连接中断：'+error.message,true);});
    await poll();
    setInterval(poll,15000);
  }
  window.__flowkitSeko={status,enqueue:body=>enqueue(body),tick};
  const boot=()=>start().catch(error=>{
    status.phase='failed';status.error=String(error);
    show('Flow 连接未就绪，正在重新连接：'+error.message,true);
    // Read-only initialization can reconnect; submitted mutations remain journaled.
    setTimeout(boot,15000);
  });
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});
  else boot();
})();
