<template>
  <el-button text @click="open">自动成片</el-button>
  <el-dialog v-model="visible" title="剧本自动成片" width="min(850px, 94vw)" appendToBody>
    <div class="autoFilm">
      <p>静音短片 · 图片 Nano Banana 2.1 · 视频 Omni（每镜 8 秒）· 本机剪辑</p>
      <el-form labelPosition="top">
        <el-form-item label="文字与画面审核模型">
          <el-select v-model="selectedModel" aria-label="文字与画面审核模型" style="width:100%">
            <el-option v-for="model in models" :key="modelKey(model)" :value="modelKey(model)" :label="`${model.providerLabel} / ${model.label}`" />
          </el-select>
          <span>供应商、接口和凭据在原生「设置 → 模型」中配置。新配置只影响新任务。</span>
        </el-form-item>
        <el-form-item label="剧本"><el-input v-model="script" type="textarea" :rows="5" aria-label="自动成片剧本" /></el-form-item>
        <el-form-item label="镜头数量"><el-input-number v-model="shotCount" :min="2" :max="8" aria-label="镜头数量" /></el-form-item>
        <el-button type="primary" :disabled="!selectedModel || !script.trim()" :loading="submitting" @click="start">开始自动任务</el-button>
      </el-form>
      <p v-if="error" role="alert">{{ error }}</p>
      <el-divider />
      <el-select v-model="selectedTask" aria-label="查看已有任务" @change="showTask" style="width:100%">
        <el-option v-for="item in tasks" :key="item.taskId" :value="item.taskId" :label="`${phaseLabel(item)} · ${item.input.script.slice(0,50)}`" />
      </el-select>
      <section v-if="task">
        <p><strong>{{ phaseLabel(task) }}</strong> · {{ task.taskId }}</p>
        <p>文字 {{ task.textModel.modelId }} → 回执 {{ task.textModel.responseModel }}</p>
        <p v-if="task.error" role="alert">{{ task.error }}</p>
        <ol><li v-for="(shot, index) in task.shots" :key="index">{{ shot.summary }} — {{ shot.error || (shot.video ? '视频已审核并回填' : shot.image ? '图片已审核并回填' : '生成中') }}</li></ol>
        <p>已完成 {{ Object.values(task.stages).filter(stage => stage.phase === 'complete').length }} 个步骤；画布：{{ task.canvas }}</p>
        <el-button v-if="!task.active && task.phase !== 'complete'" @click="resume">核查原回执并继续</el-button>
        <video v-if="videoUrl" :src="videoUrl" controls aria-label="自动任务成片" style="width:100%;max-height:360px" />
        <p v-if="task.film">本机成片：{{ task.film.path }}</p>
      </section>
    </div>
  </el-dialog>
</template>
<script setup lang="ts">
import { ref, onUnmounted, watch } from "vue";
import axios from "axios";
import { useWorkspaceStore } from "@/stores/workspace";
import useWorkspaceFiles from "@/lib/workspaceFiles";
type Model = { providerId: string; modelId: string; label: string; providerLabel: string; protocol: string };
type Task = { createdAt: string; taskId: string; phase: string; active?: boolean; input: { script: string }; textModel: { modelId: string; responseModel: string }; canvas: string; error?: string;
  shots: { summary: string; image?: unknown; video?: unknown; error?: string }[]; stages: Record<string, { phase: string }>; film?: { path: string } };
const store = useWorkspaceStore();
const files = useWorkspaceFiles();
const client = axios.create({ baseURL: "/api/workflows", headers: { "x-toonflow-workspace": "1" } });
const visible = ref(false), script = ref(""), shotCount = ref(2), selectedModel = ref(""), selectedTask = ref(""), submitting = ref(false), error = ref("");
const models = ref<Model[]>([]), tasks = ref<Task[]>([]), task = ref<Task>(), videoUrl = ref("");
let timer: ReturnType<typeof setTimeout> | undefined;
let media: ReturnType<typeof files.acquireUrl> | undefined;
let pendingId: string | undefined;
let mediaPath = "";
function modelKey(model: Model) { return JSON.stringify([model.providerId, model.modelId]); }
function phaseLabel(item: Task) { return item.phase === "complete" ? "成片已完成" : item.phase === "paused" ? "已暂停" : item.active ? "正在执行" : "待核查恢复"; }
function message(value: unknown) { return axios.isAxiosError(value) ? String(value.response?.data?.message || value.message) : value instanceof Error ? value.message : String(value); }
async function post(name: string, body: object) {
  const { data } = await client.post(`/${name}`, { directory: store.project?.directory, ...body });
  return data.data;
}
async function showTask() {
  task.value = tasks.value.find(item => item.taskId === selectedTask.value);
  const path = task.value?.film?.path ?? "";
  if (path === mediaPath) return;
  mediaPath = path; media?.release(); media = undefined; videoUrl.value = "";
  if (!path) return;
  const next = files.acquireUrl(path, "video/mp4");
  media = next;
  const url = await next.url;
  if (media === next) videoUrl.value = url;
}
async function refresh() {
  try {
    tasks.value = (await post("flowStatus", {})).sort((a: Task, b: Task) => b.createdAt.localeCompare(a.createdAt));
    if (!selectedTask.value && tasks.value.length) selectedTask.value = tasks.value[0]!.taskId;
    await showTask();
  } catch (value) { error.value = message(value); }
}
async function poll() { await refresh(); if (visible.value) timer = setTimeout(poll, 3000); }
async function open() {
  visible.value = true; error.value = "";
  try { models.value = (await axios.get("/api/ai/models")).data.data.filter((model: Model) => model.protocol === "openai-completions"); }
  catch (value) { error.value = message(value); }
  clearTimeout(timer); await poll();
}
async function start() {
  submitting.value = true; error.value = "";
  pendingId ??= crypto.randomUUID();
  try {
    const [providerId, modelId] = JSON.parse(selectedModel.value);
    const result = await post("flowStart", { taskId: pendingId, script: script.value, providerId, modelId, shotCount: shotCount.value });
    selectedTask.value = result.taskId; pendingId = undefined; await refresh();
  } catch (value) { error.value = message(value); }
  finally { submitting.value = false; }
}
async function resume() { try { await post("flowResume", { taskId: selectedTask.value }); await refresh(); } catch (value) { error.value = message(value); } }
watch(selectedTask, () => { void showTask().catch(value => { error.value = message(value); }); });
watch(visible, value => { if (!value) clearTimeout(timer); });
onUnmounted(() => { clearTimeout(timer); media?.release(); });
</script>
<style scoped lang="scss">
.autoFilm { p { margin: 12px 0; } li { margin: 10px 0; } }
</style>
