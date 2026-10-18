// Uses the existing localhost bridge secret; never sends site cookies to localhost.
chrome.runtime.onMessage.addListener((msg, sender, reply) => {
  if (msg?.type !== 'SEKO_BRIDGE') return;
  if (sender.id !== chrome.runtime.id || !sender.tab ||
      new URL(sender.url).origin !== 'https://seko.sensetime.com') {
    reply({error:'Seko tab required'}); return;
  }
  const allowed = /^(?:config|jobs(?:\/[0-9a-f-]{36}\/(?:collect|checkpoint|media))?)(?:\?[^#]*)?$/;
  if (!allowed.test(msg.path) || !['GET','POST'].includes(msg.method)) {
    reply({error:'Unsupported bridge operation'}); return;
  }
  (async () => {
    if (!callbackSecret) throw new Error('Flow Kit is not connected');
    const response = await fetch('http://127.0.0.1:8100/api/seko/'+msg.path, {
      method:msg.method, headers:{'content-type':'application/json','x-flowkit-seko':callbackSecret},
      ...(msg.method==='POST'?{body:JSON.stringify(msg.body)}:{})
    });
    if (!response.ok) throw new Error('Flow bridge '+response.status+': '+await response.text());
    reply({value:await response.json()});
  })().catch(error=>reply({error:String(error)}));
  return true;
});
