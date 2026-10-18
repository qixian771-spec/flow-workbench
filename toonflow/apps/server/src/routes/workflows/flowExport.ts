import { Router } from "express";
import { z } from "zod";
import { validateFields } from "@/lib/middleware";
import { success } from "@/lib/responseFormat";
import u from "@/utils";
import { exportFilm } from "@/utils/flow/exportFilm";

// Flow job IDs use a deterministic digest formatted as a UUID, not a random UUID version.
const taskId = z.string().regex(/^[a-f0-9]{8}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{4}-[a-f0-9]{12}$/);
const inputSchema = z.strictObject({
  directory: z.string().min(1).max(4096),
  taskId,
  workflow: z.literal(true).optional(),
  canvas: z.string().min(1).max(2048),
  shots: z.array(z.strictObject({ nodeId: z.string().min(1), jobId: taskId, sha256: z.string().regex(/^[a-f0-9]{64}$/), qualityAccepted: z.literal(true) })).min(2).max(40),
});
export default Router().post("/", validateFields(inputSchema.shape), async (req, res) => {
  u.mcpControl.assertAppRequest(req);
  const { directory, ...input } = inputSchema.parse(req.body);
  const cwd = await u.workspace.resolveWorkspace(req, directory);
  const result = await exportFilm(cwd, input);
  res.json(success(result));
});
