/* Isolated diagnostic adapter. Not loaded by the production manifest. */
(function (root) {
  'use strict';
  function installContinueBarrier(client) {
    const original = client.post;
    let blocked = 0;
    function barrier(path, options) {
      if (/^\/?seko-agent-canvas\/v1\/agent\/run\/\d+\/continue$/.test(String(path))) {
        blocked++;
        const p = Promise.reject(new Error('Flow diagnostic: native continuation is held until a bound adapter is ready'));
        p.catch(() => {}); p.json = () => p; return p;
      }
      return original.call(this, path, options);
    }
    client.post = barrier;
    return {get blocked() {return blocked;}, restore() {
      if (client.post !== barrier) throw new Error('Remove the bound adapter before its barrier');
      client.post = original;
    }};
  }
  function armAgentHandoff(client, paused) {
    const requirements = paused?.requirements;
    if (paused?.event !== 'RunPaused' || !/^\d+$/.test(paused.run_id) ||
        !Array.isArray(requirements) || requirements.length !== 1)
      throw new Error('One observed paused run is required');
    const requirement = requirements[0], tool = requirement.tool;
    if (!requirement.id || tool?.tool_name !== 'generate_image' ||
        tool.requires_user_input !== true || tool.answered === true || !tool.tool_call_id)
      throw new Error('A real unanswered generate_image tool is required');
    const original = client.post;
    const path = `seko-agent-canvas/v1/agent/run/${paused.run_id}/continue`;
    const state = {phase: 'armed', runId: paused.run_id, sessionId: paused.session_id,
      requirementId: requirement.id, toolCallId: tool.tool_call_id, capture: null};
    let rejectHeld;
    function intercepted(requestPath, options) {
      if (String(requestPath).replace(/^\//, '') !== path)
        return original.call(this, requestPath, options);
      const fail = message => {
        const p = Promise.reject(new Error(message));
        p.catch(() => {}); p.json = () => p; return p;
      };
      if (state.phase !== 'armed') return fail('This tool already has a captured handoff; no resubmission');
      const body = options?.json;
      if (body?.session_id !== state.sessionId || body?.canvas_id !== '2110204684884787202' ||
          Object.keys(body?.user_inputs || {}).length !== 1 || !body.user_inputs[requirement.id])
        return fail('Run, canvas, session or requirement mismatch; native continue blocked');
      const args = {...tool.tool_args, ...body.user_inputs[requirement.id]};
      if (Number(args.count) !== 1 || Number(args.vision_ratio_id) !== 1 ||
          Number(args.resolution_type) !== 2 || !args.prompt?.trim() ||
          (args.ref_node_ids != null && (!Array.isArray(args.ref_node_ids) || args.ref_node_ids.length)))
        return fail('Only this single 16:9 1K unreferenced image probe is supported');
      state.capture = JSON.parse(JSON.stringify({nativeRequest: body, args,
        route: {provider: 'flow', task: 'GENERATE_IMAGE', model: 'NANO_BANANA_2_1',
          resolvedModel: 'BELUGA', orientation: 'HORIZONTAL'},
        capturedAt: new Date().toISOString()}));
      state.phase = 'captured';
      // Do not forge a ToolCallCompleted event or resolve the native promise.
      // Server result acceptance is a separate, currently unproven contract.
      const held = new Promise((resolve, reject) => { rejectHeld = reject; });
      held.catch(() => {}); held.json = () => held; return held;
    }
    client.post = intercepted;
    return {state, restore() {
      if (client.post !== intercepted) throw new Error('Adapter changed concurrently');
      client.post = original;
      rejectHeld?.(new Error('Diagnostic adapter removed; server run remains paused'));
      state.phase = 'disarmed';
    }};
  }
  if (typeof module !== 'undefined') module.exports = {armAgentHandoff, installContinueBarrier};
  else {root.armAgentHandoff = armAgentHandoff; root.installContinueBarrier = installContinueBarrier;}
})(typeof window !== 'undefined' ? window : this);
