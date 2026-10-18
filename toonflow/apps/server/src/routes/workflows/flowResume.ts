import { Router } from "express";
import { z } from "zod";
import { validateFields } from "@/lib/middleware";
import { success } from "@/lib/responseFormat";
import u from "@/utils";
import { resumeTask } from "@/utils/flow/autoTask";
const inputSchema = z.strictObject({ directory: z.string().min(1).max(4096), taskId: z.uuid() });
export default Router().post("/", validateFields(inputSchema.shape), async (req, res) => {
  u.mcpControl.assertAppRequest(req);
  const { directory, ...input } = inputSchema.parse(req.body);
  const cwd = await u.workspace.resolveWorkspace(req, directory);
  res.json(success(await resumeTask(cwd, input.taskId)));
});
