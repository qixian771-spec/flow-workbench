// ACT: Web 与独立服务共用应用元数据，不依赖桌面端生成的开发套件。
export default {
  name: "toonflow",
  identifier: "local.toonflow.desktop",
  version: process.env.appVersion ?? "2.0.0",
  urlSchemes: ["toonflow"],
};
