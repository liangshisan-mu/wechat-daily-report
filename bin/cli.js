#!/usr/bin/env node
/**
 * npx 启动器：把仓库复制到用户目录，装依赖，连接微信，可选直接出图。
 *
 *   npx --yes git+https://github.com/liangshisan-mu/wechat-daily-report.git
 *   npx --yes git+https://github.com/liangshisan-mu/wechat-daily-report.git --group "群名" --date 2026-10-31
 */
const fs = require("fs");
const path = require("path");
const os = require("os");
const { spawnSync } = require("child_process");

const args = process.argv.slice(2);
const has = (k) => args.includes(k);
const get = (k) => {
  const i = args.indexOf(k);
  return i >= 0 ? args[i + 1] : null;
};

if (has("-h") || has("--help")) {
  console.log(`
微信群聊 → 日报长图

用法:
  npx --yes git+https://github.com/liangshisan-mu/wechat-daily-report.git
      安装到 ~/wechat-daily-report 并连接微信

  npx --yes git+https://github.com/liangshisan-mu/wechat-daily-report.git --group "群名" --date 2026-10-31
      安装后直接生成指定群、指定日期的长图

前提:
  Windows 10/11，微信 4.x 已登录，Python 3.10+

说明:
  安装目录 ~/wechat-daily-report，之后可双击「生成报告.bat」重复使用。
`);
  process.exit(0);
}

if (process.platform !== "win32") {
  console.error("[x] 目前只支持 Windows（采集层依赖 Windows 微信）。");
  process.exit(1);
}

const src = path.resolve(__dirname, "..");
const dest = path.join(os.homedir(), "wechat-daily-report");
const SKIP = new Set(["node_modules", ".git", ".venv", "venv", "out", "exports", "vendor", ".cache", "__pycache__"]);

function copyDir(from, to) {
  fs.mkdirSync(to, { recursive: true });
  for (const entry of fs.readdirSync(from, { withFileTypes: true })) {
    if (SKIP.has(entry.name)) continue;
    const s = path.join(from, entry.name);
    const d = path.join(to, entry.name);
    if (entry.isDirectory()) copyDir(s, d);
    else fs.copyFileSync(s, d);
  }
}

console.log("");
console.log("== 微信群聊日报 ==");
console.log("安装位置:", dest);
console.log("");

console.log("正在同步项目文件...");
copyDir(src, dest);

console.log("");
console.log("[1/2] 安装依赖（3-5 分钟，含 Chromium）...");
let r = spawnSync(
  "powershell",
  ["-ExecutionPolicy", "Bypass", "-File", path.join(dest, "setup.ps1")],
  { stdio: "inherit" }
);
if (r.status !== 0) {
  console.error("[x] 依赖安装失败，请检查上面的报错。");
  process.exit(r.status || 1);
}

console.log("");
console.log("[2/2] 连接微信（请保持微信登录）...");
const py = path.join(dest, ".venv", "Scripts", "python.exe");
r = spawnSync(py, [path.join(dest, "run.py"), "init", "--auto"], {
  stdio: "inherit",
  cwd: dest,
});
if (r.status !== 0) {
  console.error("[x] 初始化失败。确认微信已登录后，进入目录手动运行：");
  console.error("    .\\.venv\\Scripts\\python.exe run.py init");
  process.exit(r.status || 1);
}

const group = get("--group");
const date = get("--date");
if (group && date) {
  console.log("");
  console.log("正在生成报告...");
  r = spawnSync(
    py,
    [path.join(dest, "run.py"), "build", "--group", group, "--date", date],
    { stdio: "inherit", cwd: dest }
  );
  if (r.status !== 0) process.exit(r.status || 1);
  console.log("");
  console.log("完成。图片在:", path.join(dest, "out"));
} else {
  console.log("");
  console.log("安装完成。下一步：");
  console.log("  双击", path.join(dest, "生成报告.bat"));
  console.log("  或运行 npx --yes git+https://github.com/liangshisan-mu/wechat-daily-report.git --group \"群名\" --date 2026-10-31");
}
