/* Packaged in the existing extension; no downloaded code and no new permissions. */
function sekoLocalRoute(s){
  if(s.textModel!=='gpt-6.1-sol'||s.imageModel!=='BELUGA')throw Error('文字或生图路由与固定配置不符');
  const v=s.video?.route;
  if(v&&(v.provider!=='flow'||v.model!=='abra_i2v_8s'||v.mode!=='frame_to_video'||v.duration_s!==8||v.resolution!=='720p'||v.orientation!=='HORIZONTAL'))
    throw Error('视频路由与固定 Omni 配置不符');
  if(s.assembly&&(s.assembly.route?.provider!=='seko-native'||s.assembly.route?.model!==null))throw Error('剪辑执行方不符');
  if(s.multishot&&(s.multishot.route?.text!=='gpt-6.1-sol'||s.multishot.route?.video?.model!=='abra_i2v_8s'||s.multishot.route?.editing!=='seko-native'))
    throw Error('多镜路由与固定配置不符');
  return '文字 GPT-6.1-Sol · 生图 Nano Banana 2.1 · 视频 Omni · 剪辑导出 Seko';
}
function sekoLocalDecision(s){
  const stages=[['multishot',s.multishot,'resumeMulti'],['assembly',s.assembly,'resumeAssembly'],
    ['video',s.video,'resumeVideo'],['image',s,'resume']];
  const [stage,step,method]=stages.find(x=>x[1]);
  const safe={image:['submitted','ready','uploaded'],video:['submitted','ready','uploaded'],
    assembly:['reserved','canvas-ready','timeline-ready','trimmed','render-submitted','render-ready'],
    multishot:['submitted','ready','uploaded','backfilled','canvas-ready','nodes-ready','timeline-ready',
      'first-trimmed','trimmed','render-submitted','render-ready']};
  if(step.phase==='complete')return {stage,phase:step.phase,kind:'complete',method:null};
  if(safe[stage].includes(step.phase))return {stage,phase:step.phase,kind:'resumable',method};
  return {stage,phase:step.phase,kind:'inspect',method:null};
}
function sekoLocalOutput(s){
  const value=s.multishot?.phase==='complete'?s.multishot:s.assembly?.phase==='complete'?s.assembly:null;
  if(!value)return null;
  const canvasId=value.canvasId||value.target?.canvasId,storyId=value.timeline?.storyId;
  if(!/^\d+$/.test(canvasId)||!/^\d+$/.test(storyId))throw Error('Output workspace identity missing');
  return {canvasId,storyId,url:`https://seko.sensetime.com/creation?id=${storyId}&tab=editor&canvasId=${canvasId}`};
}
function installSekoLocalResident(){
  if(window.__flowkitSekoLocal)return window.__flowkitSekoLocal;
  const status={version:1,source:'packaged-extension',phase:'starting',jobs:[],error:null,
    autoResumes:[],blocked:[],lastReadAt:null};
  const pending=new Map(),running=new Set();let worker,busy=false,discovery;
  const pageKey=()=>{const p=new URLSearchParams(location.search);return p.get('canvasId')||p.get('id');};
  const request=path=>new Promise((resolve,reject)=>{
    const id=crypto.randomUUID();const timer=setTimeout(()=>{pending.delete(id);reject(Error('本机服务响应超时'));},10000);
    pending.set(id,{resolve,reject,timer});window.postMessage({source:'flowkit-seko-page',id,path,method:'GET'},location.origin);
  });
  window.addEventListener('message',event=>{
    if(event.source!==window||event.origin!==location.origin||event.data?.source!=='flowkit-seko-extension')return;
    const p=pending.get(event.data.id);if(!p)return;pending.delete(event.data.id);clearTimeout(p.timer);
    event.data.error?p.reject(Error(event.data.error)):p.resolve(event.data.value);
  });
  // Before discovery, no vendor generation can race startup. Once an unrelated
  // page is identified this guard releases it; the legacy video guard is separate.
  const previousFetch=window.fetch;
  window.fetch=function(input,options){
    const url=new URL(typeof input==='string'||input instanceof URL?input:input.url,location.origin);
    const method=(options?.method||input?.method||'GET').toUpperCase();
    if(status.phase!=='unconfigured'&&url.origin===location.origin&&method!=='GET'&&
      (/\/canvas-node\/(?:gen-|regenerate|multi-ref|video-retake|image-lighting)/.test(url.pathname)||
       /\/seko-agent-canvas\/v1\/agent\/run/.test(url.pathname)||/\/openapi\/v1\/(?:plan|story)-tasks/.test(url.pathname))){
      status.blocked.push({method,path:url.pathname});return Promise.reject(Error('本地工作流禁止厂家生成；请使用 Flow 步骤'));
    }
    return previousFetch.call(this,input,options);
  };
  async function discover(){
    const key=pageKey();if(!key||!/^\d+$/.test(key))return [];
    const rows=await request('jobs?canvasId='+key);
    if(!Array.isArray(rows))throw Error('本地任务列表格式错误');
    return rows.filter(s=>s.workflow==='seko-public-local-v1');
  }
  const ownsPage=async()=>{
    discovery??=discover().finally(()=>{discovery=null;});
    return (await discovery).length>0;
  };
  function element(tag,text){const el=document.createElement(tag);if(text)el.textContent=text;return el;}
  function render(){
    if(!document.body)return;
    let panel=document.getElementById('flowkit-local-resident');
    if(status.phase==='unconfigured'){panel?.remove();return;}
    if(!panel){panel=element('section');panel.id='flowkit-local-resident';panel.setAttribute('aria-label','Flow 本地任务');
      Object.assign(panel.style,{position:'fixed',right:'12px',top:'12px',zIndex:'2147483646',maxWidth:'360px',
        maxHeight:'65vh',overflow:'auto',background:'#153b32',color:'#fff',padding:'14px',borderRadius:'10px',
        font:'13px/1.65 system-ui',boxShadow:'0 4px 20px #0006'});document.body.append(panel);}
    panel.replaceChildren(element('strong','Flow 本地任务 · 刷新自动接续'));
    if(status.error){panel.append(element('p','连接暂停：'+status.error),element('p','恢复连接后只读核对；不重复提交。'));return;}
    if(status.jobs.length)panel.append(element('p',sekoLocalRoute(status.jobs[0])));
    for(const s of status.jobs){
      const d=sekoLocalDecision(s),card=element('div');card.style.borderTop='1px solid #ffffff40';
      card.append(element('p',`任务 ${s.jobId.slice(0,8)} · ${d.stage==='multishot'&&d.kind==='complete'?'双镜成片已完成':d.stage==='assembly'&&d.kind==='complete'?'单镜成片已完成':d.kind==='complete'?'当前步骤已完成':d.kind==='inspect'?'执行结果待核对':'正在接续已有步骤'}`));
      if(d.kind==='inspect')card.append(element('p',`阶段：${d.phase}。未重新派发。`));
      const output=sekoLocalOutput(s);
      if(output){const a=element('a','打开已完成的成片工程');a.href=output.url;a.style.color='#9fe8c4';card.append(a);}
      if(d.kind==='complete'&&d.stage!=='multishot'){
        const next={image:['startVideo','生成视频（Omni）'],video:['startAssembly','剪辑并导出'],assembly:['startMulti','生成第二镜并出片（Omni）']}[d.stage];
        const button=element('button',next[1]);button.style.margin='8px 0';button.disabled=running.has(s.jobId);
        button.addEventListener('click',async()=>{
          if(running.has(s.jobId))return;running.add(s.jobId);button.disabled=true;
          try{await worker[next[0]](s.jobId,s.canvasId);}catch(error){status.error=String(error);render();}
          finally{running.delete(s.jobId);await tick();}
        });card.append(button);
      }
      panel.append(card);
    }
  }
  async function tick(){
    if(busy)return;busy=true;
    try{
      const jobs=await discover();status.jobs=jobs;status.lastReadAt=new Date().toISOString();status.error=null;
      status.phase=jobs.length?'ready':'unconfigured';
      if(jobs.length){
        document.getElementById('flowkit-seko-status')?.remove();
        worker??=window.__sekoLocalWorkflow||installSekoLocalWorkflow();
        const legacyPanel=document.getElementById('seko-local-workflow-status');if(legacyPanel)legacyPanel.style.display='none';
        for(const s of jobs){
          sekoLocalRoute(s);
          const d=sekoLocalDecision(s);
          if(d.kind==='resumable'&&!running.has(s.jobId)){
            running.add(s.jobId);status.autoResumes.push({jobId:s.jobId,phase:d.phase,at:new Date().toISOString()});
            // Resume only persisted steps; never start the next paid step on refresh.
            try{await worker[d.method](s.jobId,s.canvasId);}finally{running.delete(s.jobId);}
          }
        }
      }
      render();
    }catch(error){status.phase='disconnected';status.error=String(error);render();}
    finally{busy=false;}
  }
  const api={status,ownsPage,tick,snapshot:()=>structuredClone(status)};
  window.__flowkitSekoLocal=api;
  const boot=()=>{tick();setInterval(tick,15000);};
  if(document.readyState==='loading')document.addEventListener('DOMContentLoaded',boot,{once:true});else boot();
  return api;
}
if(typeof module!=='undefined')module.exports={sekoLocalRoute,sekoLocalDecision,sekoLocalOutput,installSekoLocalResident};
