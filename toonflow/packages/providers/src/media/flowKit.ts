function object(value: unknown): Record<string, unknown> {
  if (!value || typeof value !== "object" || Array.isArray(value)) throw new Error("FlowKit 返回格式错误");
  return value as Record<string, unknown>;
}

async function runJob(context: ProviderContext, request: MediaRequest, kind: "image" | "video", body: Record<string, unknown>): Promise<MediaAsset[]> {
  const jobId = request.other?.flowJobId;
  if (typeof jobId !== "string" || !/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/.test(jobId)) throw new Error("缺少本地任务身份，请从工作区生成");
  const baseUrl = "http://127.0.0.1:8100/api/toonflow";
  const signal = AbortSignal.any([AbortSignal.timeout(15 * 60_000), ...(context.signal ? [context.signal] : [])]);
  const submit = await context.tool.fetch(`${baseUrl}/${kind === "image" ? "jobs" : "video-jobs"}`, {
    method: "POST", headers: { "Content-Type": "application/json" }, signal,
    body: JSON.stringify({ job_id: jobId, ...body }),
  }).catch(error => {
    if (signal.aborted) throw error;
    throw new Error(`本机 FlowKit 连接中断；未自动重发。请恢复服务并核查原任务 ${jobId}`);
  });
  if (!submit.ok) throw new Error(`FlowKit 提交失败：HTTP ${submit.status}；未自动重发`);
  let state = object(await submit.json());
  for (;;) {
    if (state.jobId !== jobId || state.kind !== kind) throw new Error("FlowKit 回执属于其他任务或媒体类型");
    if (state.phase === "complete") return [{ mediaType: kind, type: "url", url: `${baseUrl}/jobs/${jobId}/media` }];
    if (state.phase !== "submitted") throw new Error(`FlowKit 任务暂停：${String(state.error ?? state.phase)}；请核查原任务 ${jobId}`);
    signal.throwIfAborted();
    await new Promise<void>((resolve, reject) => {
      const abort = () => { clearTimeout(timer); reject(signal.reason); };
      const timer = setTimeout(() => { signal.removeEventListener("abort", abort); resolve(); }, 2000);
      signal.addEventListener("abort", abort, { once: true });
    });
    const response = await context.tool.fetch(`${baseUrl}/jobs/${jobId}`, { signal });
    if (!response.ok) throw new Error(`FlowKit 状态读取失败：HTTP ${response.status}；原任务保留`);
    state = object(await response.json());
  }
}

export default {
  id: "flowKit",
  label: "本机 FlowKit",
  icon: "",
  version: "1.1.0",
  readme: "通过本机 FlowKit 固定路由生成。文字模型独立配置；生成失败不自动换模型或重发。视频首帧必须来自本地已验收的Flow图片。",
  rules: [],
  models: [
    { id: "BELUGA", label: "Nano Banana 2.1 · Flow", type: "image", mode: ["text"], imageRatios: ["16:9"], imageSizes: ["native"] },
    { id: "abra_i2v_8s", label: "Omni · Flow · 8s 720p", type: "video", mode: ["singleImage"], audio: false, durationResolutionMap: [{ duration: [8], resolution: ["720p"] }] },
  ],
  async generateImage(request) {
    if (request.model !== "BELUGA" || request.ratio !== "16:9" || (request.size && request.size !== "native") || request.images?.length || request.mask) {
      throw new Error("本卡仅支持 Nano Banana 2.1 横屏原生尺寸文生图；参考图与其他参数尚未接通");
    }
    return runJob(this, request, "image", { model: request.model, prompt: request.prompt, ratio: request.ratio });
  },
  async generateVideo(request) {
    if (request.model !== "abra_i2v_8s" || request.duration !== 8 || request.resolution !== "720p" || request.ratio !== "16:9" ||
      request.mode !== "singleImage" || request.firstFrame || request.lastFrame || request.images?.length !== 1 || request.videos?.length || request.audios?.length || request.generateAudio) {
      throw new Error("Omni 参数不匹配：" + JSON.stringify({ model: request.model, duration: request.duration, resolution: request.resolution, ratio: request.ratio, mode: request.mode, firstFrame: !!request.firstFrame, lastFrame: !!request.lastFrame, images: request.images?.length, videos: request.videos?.length, audios: request.audios?.length, generateAudio: request.generateAudio }));
    }
    if (typeof request.other?.sourceImageSha256 !== "string") throw new Error("缺少工作区首帧指纹");
    const prompt = `Use the supplied first frame as the exact visual starting point. Preserve the scene, objects, lighting and art style. One continuous 8-second shot. ${request.prompt} Silent, no speech, no music, no added text.`;
    return runJob(this, request, "video", { model: request.model, prompt, ratio: request.ratio, duration: request.duration,
      resolution: request.resolution, source_image_sha256: request.other.sourceImageSha256 });
  },
} satisfies ProviderDefinition;
