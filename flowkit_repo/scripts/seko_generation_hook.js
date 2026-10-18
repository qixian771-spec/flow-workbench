/* Session-scoped interception of Seko's native canvas image-to-video request.
 * Loaded only through the authorized CUA developer session. No credential export.
 * Restore with dispose(); reload also removes it. All other generation routes fail
 * while armed; there is no automatic submission to Seko's native generation service.
 */
function installSekoGenerationHook(config, deps) {
  const {canvasId, referenceNodeId} = config;
  if (!/^\d+$/.test(canvasId) || !/^\d+$/.test(referenceNodeId))
    throw new Error('Explicit canvas and reference IDs required');
  const jobs = new Map();
  const audit = [];
  const clients = [...new Set(deps.clients)];
  const originals = clients.map(c => c.post);
  const route = 'seko-canvas/v1/canvas-node/gen-video';
  const generationRoute = /(?:\/gen-(?:video|image|text|audio)|\/multi-ref-(?:video|audio)|\/regenerate|\/video-retake|\/story-tasks)(?:$|[/?])/;
  const log = (kind, detail) => audit.push({at: new Date().toISOString(), kind, ...detail});
  const reject = message => { const p = Promise.reject(new Error(message)); p.catch(() => {}); p.json = () => p; return p; };
  const hooks = clients.map((client, i) => function(input, options) {
    const path = typeof input === 'string' ? input.replace(/^\//, '') : '';
    if (path !== route) {
      if (generationRoute.test(String(input))) {
        log('blocked-unsupported', {route: String(input)});
        return reject('Flow bridge: unsupported generation route; nothing submitted');
      }
      return originals[i].call(this, input, options);
    }
    const body = structuredClone(options?.json);
    if (!body || body.canvasId !== canvasId || body.firstFrameNodeId !== referenceNodeId ||
        body.lastFrameNodeId || body.refNodeIds?.length || body.selectedVideoDuration !== 8 ||
        !body.videoPrompt?.trim()) {
      log('blocked-invalid', {route: path});
      return reject('Flow bridge: request outside the explicit eight-second reference contract');
    }
    if ([...jobs.values()].some(j => !['complete', 'failed'].includes(j.state)))
      return reject('Flow bridge: another request is pending; no duplicate submission');
    const jobId = deps.uuid();
    let resolve, fail;
    const pending = new Promise((yes, no) => {resolve = yes; fail = no;});
    pending.catch(() => {});
    pending.json = () => pending;
    jobs.set(jobId, {jobId, state: 'captured', canvasId, nativeRoute: path,
      nativeRequest: body, actualProvider: 'flow', actualModelFamily: 'omni_flash', resolve, fail});
    log('captured-native-request', {jobId, route: path, upstreamSubmitted: false});
    deps.onStatus?.('Flow 已接管原生生成请求，等待本机调度');
    return pending;
  });
  clients.forEach((client, i) => {client.post = hooks[i];});
  const get = id => {const job = jobs.get(id); if (!job) throw new Error('Unknown job'); return job;};
  return {
    version: 1,
    snapshot: () => ({canvasId, referenceNodeId, audit: structuredClone(audit),
      jobs: [...jobs.values()].map(({resolve, fail, ...j}) => structuredClone(j))}),
    markSubmitted(id, requestId) {
      const job = get(id);
      if (job.state !== 'captured' || !requestId) throw new Error('Invalid submit transition');
      job.state = 'submitted'; job.flowRequestId = requestId;
      log('flow-submitted', {jobId: id, requestId});
      deps.onStatus?.('Flow Omni Flash 正在生成 · 8 秒');
    },
    beginBackfill(id) {
      const job = get(id);
      if (job.state !== 'submitted') throw new Error('Backfill requires submitted job');
      job.state = 'backfilling';
      deps.onStatus?.('Flow 生成完成，正在上传并回填 Seko');
    },
    finish(id, receipt) {
      const job = get(id);
      if (job.state !== 'backfilling' || !receipt.nodeId || !receipt.nodeGenId)
        throw new Error('Verified real Seko node receipt required');
      job.state = 'complete'; job.receipt = structuredClone(receipt);
      log('completed-real-node', {jobId: id, nodeId: receipt.nodeId, nodeGenId: receipt.nodeGenId});
      job.resolve(receipt);
      deps.onStatus?.('Flow 素材已回填 Seko · 可自动出片');
    },
    fail(id, message) {
      const job = get(id);
      if (['complete','failed'].includes(job.state)) throw new Error('Terminal job');
      job.state = 'failed'; job.error = message;
      job.fail(new Error(message)); log('failed', {jobId: id, message});
      deps.onStatus?.('Flow 流程停止：' + message);
    },
    dispose() {
      if ([...jobs.values()].some(j => !['complete','failed'].includes(j.state)))
        throw new Error('Cannot disarm while a request is pending');
      clients.forEach((client, i) => {
        if (client.post !== hooks[i]) throw new Error('Request client changed concurrently');
      });
      clients.forEach((client, i) => {client.post = originals[i];});
      deps.onStatus?.('本次 Flow 接管已结束');
    },
  };
}
if (typeof module !== 'undefined') module.exports = {installSekoGenerationHook};
