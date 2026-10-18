/* Execute through an authorized, same-origin Seko browser developer session.
 * No credentials, persistent injection, generation model call or dependency install.
 * Build-specific imports intentionally fail when the vendor changes its bundle.
 */
async function sekoAdapter(command, input) {
  const canvas = await import('/assets/canvas-BZat8bJg.js');
  const story = await import('/assets/LoginContext-CFHyujin.js');
  const identity = value => {
    const u = new URL(value);
    if (u.protocol !== 'https:') throw new Error('Expected HTTPS media');
    return u.host + u.pathname;
  };
  const snapshot = async () => {
    const current = await canvas.an(input.canvasId);
    if (current.canvasId !== input.canvasId || current.storyId !== input.storyId)
      throw new Error('Canvas/story mismatch');
    const nodes = await canvas.ao(input.canvasId);
    if (!nodes.some(n => n.id === input.nodeId)) throw new Error('Node not in canvas');
    return {canvas: current, node: await canvas.b(input.nodeId), shots: await story.aj(input.storyId)};
  };
  if (command === 'snapshot') return snapshot();
  if (command === 'render-status') return story.bV(input.storyId, input.renderId);
  if (command === 'backfill') {
    const before = await snapshot();
    if (before.canvas.canvasId !== input.canvasId || before.canvas.storyId !== input.storyId)
      throw new Error('Canvas/story mismatch');
    if (identity(before.node.node.genFileUrl) !== identity(input.expectedMediaUrl))
      throw new Error('Target media changed; refusing concurrent overwrite');
    if (before.node.node.genStatus !== 'GENERATING_COMPLETED' || input.duration !== 8)
      throw new Error('Only completed eight-second fixture supported');
    if (!input.filePath || !input.filePath.startsWith('STS/'))
      throw new Error('Expected a verified Seko upload storage path');
    // Unknown outcome is an error to inspect, never an automatic retry.
    await canvas.ap(input.nodeId, {filePath: input.filePath, duration: input.duration});
    const after = await snapshot();
    if (after.node.node.id !== input.nodeId ||
        new URL(after.node.node.genFileUrl).pathname !== '/' + input.filePath)
      throw new Error('Backfill verification failed');
    return {before, after};
  }
  if (command === 'refresh-shots') {
    const before = await snapshot();
    const expectedIds = new Set(input.shotIds);
    if (expectedIds.size !== input.shotIds.length || !expectedIds.size)
      throw new Error('Expected unique explicit shot IDs');
    const selected = before.shots.filter(s => expectedIds.has(s.id));
    if (selected.length !== expectedIds.size || selected.some(s => s.duration !== 8 ||
        s.shotVideoStartTime !== 0 || s.shotVideoEndTime !== 8))
      throw new Error('Unsupported or missing shot: preserve custom trims explicitly');
    await canvas.aq({canvasId: input.canvasId, nodes: selected.map(s => ({
      nodeId: input.nodeId, action: 'REPLACE', shotId: s.id,
      seq: String(s.seq), seqValue: String(s.seqValue),
    }))});
    const after = await snapshot();
    const uri = identity(after.node.node.genFileUrl);
    for (const old of selected) {
      const current = after.shots.find(s => s.id === old.id);
      if (!current || identity(current.shotVideoUrl) !== uri ||
          ['seq', 'seqValue', 'duration', 'shotVideoStartTime', 'shotVideoEndTime'].some(
            k => old[k] !== current[k])) throw new Error('Shot refresh verification failed');
    }
    return {before, after};
  }
  if (command === 'render') {
    const state = await snapshot();
    if (state.shots.length !== 2 || state.shots.some(s =>
        s.duration !== 8 || s.genVideoStatus !== 'GENERATING_COMPLETED' ||
        identity(s.shotVideoUrl) !== identity(state.node.node.genFileUrl)))
      throw new Error('Expected two completed shots of the current source');
    return story.bW(input.storyId, {captionOption: 1, splitOption: 0, watermarkOption: 1});
  }
  throw new Error('Unsupported operation: ' + command);
}
