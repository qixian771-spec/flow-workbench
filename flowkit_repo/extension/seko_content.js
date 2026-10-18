// Narrow relay: the page cannot choose an arbitrary network URL or read credentials.
window.addEventListener('message', async event => {
  if (event.source!==window || event.origin!==location.origin || event.data?.source!=='flowkit-seko-page') return;
  const {id,path,method,body}=event.data;
  if(typeof id!=='string'||id.length>80)return;
  try {
    const result=await chrome.runtime.sendMessage({type:'SEKO_BRIDGE',path,method,body});
    window.postMessage({source:'flowkit-seko-extension',id,...result},location.origin);
  } catch(error) {
    window.postMessage({source:'flowkit-seko-extension',id,error:String(error)},location.origin);
  }
});
