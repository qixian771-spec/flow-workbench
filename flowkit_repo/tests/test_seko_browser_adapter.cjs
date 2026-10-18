const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const source = fs.readFileSync(path.join(__dirname, '../scripts/seko_browser_adapter.js'), 'utf8')
  .replace("await import('/assets/canvas-BZat8bJg.js')", 'modules.canvas')
  .replace("await import('/assets/LoginContext-CFHyujin.js')", 'modules.story');
const input = {canvasId: 'c', storyId: 's', nodeId: 'n', duration: 8,
  expectedMediaUrl: 'https://example.com/old', filePath: 'STS/new', shotIds: ['1','2']};
function fixture(change = {}) {
  let writes = 0;
  const shot = id => ({id, seq: +id, seqValue: +id, duration: 8, shotVideoStartTime: 0,
    shotVideoEndTime: 8, genVideoStatus: 'GENERATING_COMPLETED', shotVideoUrl: 'https://example.com/old'});
  const node = {id: 'n', genStatus: 'GENERATING_COMPLETED', genFileUrl: 'https://example.com/old'};
  const modules = {
    canvas: {an: async () => ({canvasId:'c',storyId:'s'}), ao: async () => [{id:'n'}],
      b: async () => ({node}), ap: async () => { writes++; }, aq: async () => { writes++; }},
    story: {aj: async () => [shot('1'), shot('2')], bW: async () => { writes++; return {id:'render'}; }},
  };
  if (change.node) Object.assign(node, change.node);
  if (change.canvas) Object.assign(modules.canvas, change.canvas);
  if (change.story) Object.assign(modules.story, change.story);
  const ctx = vm.createContext({modules, URL});
  vm.runInContext(source, ctx);
  return {run: (op, data = input) => ctx.sekoAdapter(op, data), writes: () => writes};
}
(async () => {
  let f = fixture({node:{genFileUrl:'https://example.com/concurrent'}});
  await assert.rejects(f.run('backfill'), /changed/); assert.equal(f.writes(),0);
  f=fixture({canvas:{an:async()=>({canvasId:'c',storyId:'wrong'})}});
  await assert.rejects(f.run('backfill'), /mismatch/); assert.equal(f.writes(),0);
  f=fixture({canvas:{ao:async()=>[]}});
  await assert.rejects(f.run('backfill'), /not in canvas/); assert.equal(f.writes(),0);
  f=fixture();
  await assert.rejects(f.run('refresh-shots',{...input,shotIds:['1','1']}), /unique/);
  assert.equal(f.writes(),0);
  f=fixture({story:{aj:async()=>[{id:'1',duration:7}]}});
  await assert.rejects(f.run('refresh-shots'), /Unsupported/); assert.equal(f.writes(),0);
  f=fixture({node:{genFileUrl:'https://example.com/new'}});
  await assert.rejects(f.run('render'), /current source/); assert.equal(f.writes(),0);
  f=fixture(); await f.run('render'); assert.equal(f.writes(),1);
  await assert.rejects(f.run('native-generation'), /Unsupported operation/);
  console.log('8 Seko adapter guard checks passed');
})().catch(error => {console.error(error);process.exitCode=1;});
