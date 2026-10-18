/* Explicit image-driven dialogue stage. Seko currently reanimates a still image;
 * this must never be reported as preserving Flow video motion. No retry of writes.
 * Reload-safe journal records boundaries; an uncertain mutation requires inspection.
 */
async function sekoDialogueStep(plan) {
  const key='flowkit-dialogue-'+plan.storyId;
  const prior=JSON.parse(localStorage.getItem(key)||'null');
  const state=prior||{phase:'new',storyId:plan.storyId,canvasId:plan.canvasId,history:[]};
  const save=(phase,extra={})=>{Object.assign(state,{phase},extra);state.history.push({phase,at:new Date().toISOString()});localStorage.setItem(key,JSON.stringify(state));};
  if(state.storyId!==plan.storyId||state.canvasId!==plan.canvasId)throw Error('Wrong episode');
  if(plan.lines.length!==4||new Set(plan.lines.map(x=>x.jobId)).size!==4)throw Error('Four distinct Flow jobs required');
  const m=await import('/assets/LoginContext-CFHyujin.js');
  const canvas=await import('/assets/canvas-BZat8bJg.js');
  const shot=await import('/assets/shot-BflClSjB.js');
  const same=(a,b)=>{const x=new URL(a),y=new URL(b);return x.origin===y.origin&&x.pathname===y.pathname;};
  if((await canvas.an(plan.canvasId)).storyId!==plan.storyId)throw Error('Canvas/story mismatch');
  if(state.phase==='new'){
    const jobs=window.__flowkitSeko.status.jobs;
    const inputs=plan.lines.map(line=>{
      const job=jobs.find(x=>x.jobId===line.jobId);
      if(!job||job.phase!=='complete'||job.canvasId!==plan.canvasId)throw Error('Flow media incomplete');
      return job;
    });
    const old=await m.aj(plan.storyId);
    if(old.length!==1||old[0].id!==plan.initialShotId)throw Error('Initial timeline changed');
    save('assembling-flow',{flowJobs:inputs});
    const receipts=await canvas.aq({canvasId:plan.canvasId,resolutionType:1,visionRatioId:1,
      nodes:inputs.map((job,i)=>({nodeId:job.receipt.nodeId,action:i===0?'REPLACE':'CREATE',
        ...(i===0?{shotId:old[0].id}:{}),seq:String(i+1),seqValue:String((i+1)*1000)}))});
    const shots=(await m.aj(plan.storyId)).sort((a,b)=>a.seq-b.seq);
    if(shots.length!==4)throw Error('Expected four shots');
    for(let i=0;i<4;i++){
      const node=await canvas.b(inputs[i].receipt.nodeId);
      if(shots[i].genVideoStatus!=='GENERATING_COMPLETED'||!same(shots[i].shotVideoUrl,node.node.genFileUrl))
        throw Error('Timeline does not contain the actual Flow media');
    }
    save('flow-ready',{shots,receipts});
    return state;
  }
  if(state.phase==='flow-ready'){
    // Frame uploads must be supplied from the actual generated videos, not a substitute portrait.
    if(plan.lines.some(x=>!x.frameUpload?.path||!x.audioUpload?.path||x.duration!==5))
      throw Error('Verified Flow first frames and exact five-second audio required');
    save('setting-frames');
    for(let i=0;i<4;i++)await shot.a(state.shots[i].id,{imagePath:plan.lines[i].frameUpload.path});
    save('frames-ready');
    return state;
  }
  if(state.phase==='frames-ready'){
    save('detecting-faces');
    await Promise.all(state.shots.map(s=>shot.p(s.id)));
    save('faces-pending');
    return state;
  }
  if(state.phase==='faces-pending'){
    const details=await Promise.all(state.shots.map(s=>m.ak(s.id)));
    if(details.some(s=>s.faceMaskDetectStatus==='GENERATING'))return state;
    if(details.some(s=>s.faceMaskDetectStatus!=='GENERATING_COMPLETED'||s.faceMaskPosition?.masks?.length!==1))
      throw Error('Exactly one detected face required in every shot');
    save('faces-ready',{details});return state;
  }
  if(state.phase==='faces-ready'){
    const model=m.a.getState().resolutionLibSyncModels.find(x=>x.code==='sensetime'&&x.resolutionType===1);
    if(!model?.supportSingle)throw Error('SekoTalk 720p single-face model unavailable');
    const payloads=[];
    save('preparing-masks');
    for(let i=0;i<4;i++){
      const line=plan.lines[i],detail=state.details[i];
      const character={characterId:crypto.randomUUID(),character:line.character,isTemporaryAdd:false,
        maskPosition:{origin:detail.faceMaskPosition.origin,mask:detail.faceMaskPosition.masks[0]},maskPath:'',audioPath:'',
        speeches:[{speechId:crypto.randomUUID(),startTime:0,endTime:5,volume:1,audioType:'UPLOAD_BY_USER',duration:5,
          audioUrl:line.audioUpload.url,audioPath:line.audioUpload.path,audioName:line.character+'-'+(i+1)+'.wav',
          speedRatio:1,speechSource:'NORMAL',globalStartTime:0,globalEndTime:0}]};
      const size=await m.a2(detail.shotImageUrl);
      const mask=await m.b0([character],{canvasWidth:size.width,canvasHeight:size.height,mimeType:'image/jpeg',quality:.92});
      const regions=await m.aZ(detail.shotImageUrl,[{id:character.characterId,maskPosition:character.maskPosition}]);
      character.maskImageFile=regions.get(character.characterId)?.maskImageFile;
      if(!mask?.reverseMaskImageFile||!character.maskImageFile)throw Error('Native mask generation incomplete');
      const reverse=await m.aS(mask.reverseMaskImageFile);
      const person=await m.aS(character.maskImageFile);
      delete character.maskImageFile;character.maskPath=person.path;
      payloads.push({reverseMaskPath:reverse.path,characterSpeeches:[character],resolutionType:1,
        lipSyncPrompt:'正面固定近景，克制自然的表情，准确跟随输入音频说话，静音段闭嘴，保持角色和背景一致。',
        mode:'SINGLE',lipSyncModel:'sensetime'});
    }
    save('masks-ready',{lipPayloads:payloads});return state;
  }
  if(state.phase==='masks-ready'){
    save('submitting-lips');
    const receipts=await Promise.all(state.shots.map((s,i)=>shot.b(s.id,state.lipPayloads[i])));
    save('lips-pending',{lipReceipts:receipts});return state;
  }
  if(state.phase==='lips-pending'){
    const shots=(await m.aj(plan.storyId)).sort((a,b)=>a.seq-b.seq);
    if(shots.some(s=>['GENERATING','INITIALIZATION'].includes(s.genVideoStatus)))return state;
    if(shots.length!==4||shots.some((s,i)=>s.id!==state.shots[i].id||s.genVideoStatus!=='GENERATING_COMPLETED'||s.videoGenType!=='LIP_SYNC_MULTI'))
      throw Error('Dialogue generation did not complete successfully');
    save('dialogue-ready',{dialogueShots:shots});return state;
  }
  if(state.phase==='dialogue-ready'){
    save('rendering');
    const receipt=await m.bW(plan.storyId,{captionOption:1,splitOption:0,watermarkOption:1});
    save('render-submitted',{render:receipt});return state;
  }
  if(state.phase==='render-submitted')return state;
  throw Error('Uncertain write checkpoint: '+state.phase+'; inspect before any further mutation');
}

async function sekoRunDialogue(plan){
  const key='flowkit-dialogue-'+plan.storyId;
  return navigator.locks.request(key,{ifAvailable:true},async lock=>{
    if(!lock)throw Error('Episode already running');
    const deadline=Date.now()+20*60*1000;
    while(Date.now()<deadline){
      const state=await sekoDialogueStep(plan);
      if(state.phase==='render-submitted')return state;
      if(['faces-pending','lips-pending'].includes(state.phase))await new Promise(resolve=>setTimeout(resolve,10000));
    }
    throw Error('Episode wait limit reached; submitted tasks preserved');
  });
}
