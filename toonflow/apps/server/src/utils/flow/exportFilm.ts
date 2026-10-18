import { createHash } from "node:crypto";
import { join } from "node:path";
import { mkdir, readFile, rename, stat, writeAtomic } from "@toonflow/file";
import type { FfmpegFactory, FfprobeData } from "@toonflow/ffmpeg/types";
import { createWorkspaceFfmpeg } from "@/utils/ffmpeg";
import type { AutoTask } from "./autoTask";
import conf from "@/utils/conf";
import { lockWorkspaceFiles, resolveWorkspacePath } from "@/utils/workspace/files";

export interface FilmInput {
  taskId: string;
  workflow?: true;
  canvas: string;
  shots: { nodeId: string; jobId: string; sha256: string; qualityAccepted: true }[];
}
interface FilmState {
  exportId: string;
  taskId: string;
  input: FilmInput;
  phase: "rendering" | "complete" | "needs-inspection";
  path: string;
  sha256?: string;
  bytes?: number;
  duration?: number;
  error?: string;
}
function invalid(message: string): never { throw Object.assign(new Error(message), { status: 409 }); }
function hash(bytes: Uint8Array | string) { return createHash("sha256").update(bytes).digest("hex"); }
async function receipt(jobId: string) {
  const response = await fetch(`http://127.0.0.1:8100/api/toonflow/jobs/${jobId}`, { signal: AbortSignal.timeout(30_000) });
  if (!response.ok) invalid(`Flow 任务回执读取失败：HTTP ${response.status}`);
  return await response.json() as Record<string, unknown>;
}
function probe(ffmpeg: FfmpegFactory, path: string) {
  return new Promise<FfprobeData>((resolve, reject) => ffmpeg.ffprobe(path, (error, data) => error ? reject(error) : resolve(data)));
}
function verifyVideo(data: FfprobeData, duration: number, silent = false) {
  const videos = data.streams.filter(stream => stream.codec_type === "video");
  if (videos.length !== 1 || videos[0]!.width !== 1280 || videos[0]!.height !== 720 || Math.abs(Number(data.format.duration) - duration) > 0.1) invalid("视频尺寸或时长与镜头清单不一致");
  if (silent && data.streams.some(stream => stream.codec_type === "audio")) invalid("静音成片不应含音轨");
}

export async function exportFilm(directory: string, input: FilmInput): Promise<FilmState> {
  if (new Set(input.shots.map(shot => shot.nodeId)).size !== input.shots.length ||
    new Set(input.shots.map(shot => shot.jobId)).size !== input.shots.length ||
    new Set(input.shots.map(shot => shot.sha256)).size !== input.shots.length) invalid("镜头节点、任务和素材必须各不相同");
  const canvasPath = (await resolveWorkspacePath(directory, input.canvas)).path;
  const canvas = JSON.parse(await readFile(canvasPath, "utf8"));
  if (canvas.toonflowCanvas !== true || !Array.isArray(canvas.nodes)) invalid("需要有效的本地画布");
  let workflow: AutoTask | undefined;
  if (input.workflow) {
    const path = (await resolveWorkspacePath(directory, `tasks/${input.taskId}/state.json`)).path;
    workflow = JSON.parse(await readFile(path, "utf8")) as AutoTask;
    if (workflow.version !== 1 || workflow.taskId !== input.taskId || !["exporting", "complete"].includes(workflow.phase) || workflow.canvas !== input.canvas || workflow.shots.length !== input.shots.length || workflow.inputHash !== hash(JSON.stringify(workflow.input))) invalid("自动总任务身份或导出状态不匹配");
    for (const [index, shot] of input.shots.entries()) {
      const expected = workflow.shots[index];
      if (!expected || expected.error || !expected.quality?.accepted || expected.videoNodeId !== shot.nodeId || expected.video?.flowJobId !== shot.jobId || expected.video.sha256 !== shot.sha256 || !expected.image?.flowJobId) invalid("镜头与自动任务的已审核清单不匹配");
    }
  } else {
    const root = await receipt(input.taskId);
    if (root.jobId !== input.taskId || root.kind !== "image" || root.phase !== "complete") invalid("根任务尚未完成生图");
  }
  const sources: string[] = [];
  for (const shot of input.shots) {
    if (shot.qualityAccepted !== true) invalid("镜头质量未验收，不能出最终片");
    const matches = canvas.nodes.filter((node: { id: string }) => node.id === shot.nodeId);
    if (matches.length !== 1) invalid("镜头节点缺失或重复");
    const value = matches[0].data?.outputs?.video?.value;
    if (!value?.url || value.mimeType !== "video/mp4") invalid("镜头尚未生成本地视频");
    const path = (await resolveWorkspacePath(directory, value.url)).path;
    if (hash(await readFile(path)) !== shot.sha256) invalid("画布视频文件指纹已变化");
    const expectedImage = workflow?.shots.find(item => item.videoNodeId === shot.nodeId)?.image;
    if (expectedImage) {
      const root = await receipt(expectedImage.flowJobId!);
      if (root.kind !== "image" || root.phase !== "complete" || root.sha256 !== expectedImage.sha256) invalid("自动任务图片回执不匹配");
    }
    const state = await receipt(shot.jobId);
    const route = state.route as Record<string, unknown> | undefined;
    if (state.jobId !== shot.jobId || state.kind !== "video" || state.phase !== "complete" || state.rootJobId !== (expectedImage?.flowJobId ?? input.taskId) ||
      state.sha256 !== shot.sha256 || route?.model !== "abra_i2v_8s" || route?.provider !== "flow") invalid("镜头与同一根任务的 Omni 回执不匹配");
    sources.push(path);
  }
  const exportId = hash(JSON.stringify(input));
  const relativeFolder = `exports/flow${exportId.slice(0, 20)}`;
  const folder = (await resolveWorkspacePath(directory, relativeFolder, true)).path;
  const release = lockWorkspaceFiles([folder, ...sources]);
  try {
    await mkdir(folder, { recursive: true });
    const manifest = join(folder, "manifest.json");
    const old = await readFile(manifest, "utf8").catch((error: NodeJS.ErrnoException) => {
      if (error.code === "ENOENT") return null;
      throw error;
    });
    if (old !== null) {
      const state = JSON.parse(old) as FilmState;
      if (state.exportId !== exportId || JSON.stringify(state.input) !== JSON.stringify(input)) invalid("导出任务身份冲突");
      if (state.phase !== "complete") invalid("旧导出未完成，保留现场等待核查，不自动覆盖重做");
      const path = (await resolveWorkspacePath(directory, state.path)).path;
      if (hash(await readFile(path)) !== state.sha256) invalid("已完成成片指纹已变化");
      return state;
    }
    const settings = conf.get("settings", {});
    if ((settings.ffmpeg as { mode?: string } | undefined)?.mode !== "system") invalid("此流程须明确配置使用本机已有 FFmpeg");
    const ffmpeg = await createWorkspaceFfmpeg(directory);
    for (const source of sources) verifyVideo(await probe(ffmpeg, source), 8);
    const output = join(folder, "film.mp4");
    const partial = join(folder, "rendering.mp4");
    for (const path of [output, partial]) {
      const exists = await stat(path).then(() => true).catch((error: NodeJS.ErrnoException) => {
        if (error.code === "ENOENT") return false;
        throw error;
      });
      if (exists) invalid("输出文件已存在但没有完成清单，暂停核查");
    }
    const state: FilmState = { exportId, taskId: input.taskId, input, phase: "rendering", path: `${relativeFolder}/film.mp4` };
    await writeAtomic(manifest, JSON.stringify(state, null, 2));
    try {
      const filters = sources.map((_, index) => `[${index}:v]fps=30,setsar=1,setpts=PTS-STARTPTS[v${index}]`);
      filters.push(`${sources.map((_, index) => `[v${index}]`).join("")}concat=n=${sources.length}:v=1:a=0[outv]`);
      await new Promise<void>((resolve, reject) => {
        const command = ffmpeg();
        for (const source of sources) command.input(source);
        command.complexFilter(filters, "outv").videoCodec("libx264").noAudio()
          .outputOptions(["-crf 18", "-preset medium", "-pix_fmt yuv420p", "-movflags +faststart"])
          .on("error", reject).on("end", () => resolve()).save(partial);
      });
      const meta = await probe(ffmpeg, partial);
      verifyVideo(meta, sources.length * 8, true);
      const bytes = await readFile(partial);
      // 输入在编码前后均校验，避免生成期间其他进程改动素材。
      for (let index = 0; index < sources.length; index++) if (hash(await readFile(sources[index]!)) !== input.shots[index]!.sha256) invalid("编码期间镜头文件发生变化");
      await rename(partial, output);
      Object.assign(state, { phase: "complete", sha256: hash(bytes), bytes: bytes.length, duration: Number(meta.format.duration) });
      await writeAtomic(manifest, JSON.stringify(state, null, 2));
      return state;
    } catch (error) {
      state.phase = "needs-inspection";
      state.error = error instanceof Error ? error.message : String(error);
      await writeAtomic(manifest, JSON.stringify(state, null, 2));
      throw error;
    }
  } finally { release(); }
}
