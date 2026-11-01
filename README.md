# 群聊日报 → 研究报告长图

把某个微信群**某一天的全部消息**，生成一张竖版研究报告式长图：标题、核心议题、数据、双栏对比、编号批注、群友发言（真实头像）、原话引用、行动清单，一次输出 PNG。

适合做团队复盘、社群日报、内容选题会材料，或者只是把一天的热闹沉淀成一份能看的记录。

---

## 它长什么样

![示例长图](docs/example.png)

从上到下固定六段：

1. 标题 + 副标题 + 关键词胶囊
2. 深绿引言卡 + `01 核心议题` + 四个数据
3. `02 已有优势与待确认`：左米色 / 右深绿双栏
4. `03 讨论聚焦`：带圆点竖线的编号批注
5. `04 群友发言`：两列白卡 + 真实微信头像
6. `05 话语拾零`：引用卡网格（部分深绿）+ `06 行动清单`（复选框）+ 结语 + 页脚

模板在 `report/template.html`，配色是墨绿 `#1C3A2A` + 米白 `#F4F1E8` + 陶土橙 `#B65C34`，正文宋体、标题黑体，走“研究报告”而不是“营销卡片”的路子。

---

## 原理

```
本机微信 4.x 数据库
      │  yichen-wechat-local-vault（只读快照 + 解密）
      ▼
导出某群某天的 Markdown
      │  prompts/extract.md（大模型提炼）
      ▼
结构化 report.json
      │  report/template.html（Jinja2 渲染）
      ▼
HTML → Playwright 截图 → PNG
```

全程本地：快照、聊天、头像都不离开你的电脑。只有“提炼”这一步会把**导出文本**发给你配置的模型接口（也可以不配，手动交给任意 AI）。

---

## 前提

- **Windows**（采集层 `yichen-wechat-local-vault` 目前只实测 Windows）
- **微信 4.x 已登录并保持运行**（密钥从运行中的进程内存读取）
- **Python 3.10+**，推荐 3.12
- 磁盘预留 2GB 以上（每次快照约 600MB 明文）

> 微信大版本升级后，内存结构变化可能导致密钥读取失效，属于正常现象，等上游 skill 更新。

---

## 快速开始

```powershell
git clone <你的仓库地址>
cd wechat-daily-report

# 1. 安装（创建 .venv、装依赖、装 Chromium、拉取采集 skill）
powershell -ExecutionPolicy Bypass -File setup.ps1

# 2. 初始化（自动找微信数据目录、探测账号、写 config.json）
.\.venv\Scripts\python.exe run.py init

# 3. 填模型配置（可选，不填则手动提炼）
#    编辑 config.json 的 llm.base_url / api_key / model
#    支持任意 OpenAI 兼容接口（DeepSeek、OpenAI、通义、Moonshot…）

# 4. 生成
.\.venv\Scripts\python.exe run.py build --group "你的群名" --date 2026-10-31
```

产物：

- `out/<群名>_<日期>.json`：提炼后的结构化数据
- `out/<群名>_<日期>.html`：可编辑的源文件
- `out/<群名>_<日期>.png`：最终长图

### 不配置模型也能用

`build` 会先导出聊天，然后停下来提示你：

```
未配置 llm.api_key，已停在导出这一步。
聊天记录：exports/xxx.md
把这份记录和 prompts/extract.md 一起交给任意 AI，让它输出 JSON，
保存为 out/xxx.json，再运行：
  python report/build.py --data "out/xxx.json"
```

把 `prompts/extract.md` 和导出文件一起丢给 WorkBuddy / Claude / ChatGPT，让它按结构输出 JSON，再跑 `report/build.py` 即可。

---

## 命令

| 命令 | 作用 |
|---|---|
| `python run.py init` | 找数据目录、探测账号、生成 `config.json` |
| `python run.py refresh` | 采集最新快照（微信需运行） |
| `python run.py chats 关键词` | 列出会话，支持模糊匹配 |
| `python run.py build --group "群名" --date 2026-10-31` | 一条龙：采集 → 导出 → 提炼 → 出图 |
| `python run.py build ... --no-refresh` | 跳过重新采集，直接用现有快照 |
| `python report/build.py --data out/x.json` | 只做渲染与截图 |
| `python wx.py read "群名" --limit 100` | 直接读聊天 |
| `python wx.py search "关键词" --chat "群名"` | 群内搜索 |
| `python wx.py export "群名" --start 2026-10-01` | 导出 Markdown |
| `python wx.py clean --keep 2 --yes` | 清理旧快照（每次约 600MB） |

---

## 自定义

### 改内容结构

编辑 `report/example.json` 或你生成的 `out/*.json`，字段说明见 `prompts/extract.md`。

### 改提炼规则

编辑 `prompts/extract.md`。想让模型更狠、更短、更口语，都改这里。

### 改视觉

编辑 `report/template.html` 顶部的 CSS 变量：

```css
:root{
  --bg:#F4F1E8;      /* 米白底 */
  --green:#1C3A2A;   /* 墨绿 */
  --clay:#B65C34;    /* 陶土橙 */
}
```

### 换头像

`report/assets/` 放图片，JSON 里 `people[].avatar` 写文件名即可。`build` 会自动转 base64 内嵌，单文件不会掉图。

`build` 也会在提炼后**自动**按群显示名匹配发言人、下载微信头像。重名时取当天发言最多的那个。

---

## 隐私与安全

这个项目会接触非常敏感的数据，务必注意：

- `config.json`、`exports/`、`out/`、`report/assets/`、`vendor/` 全部在 `.gitignore` 里，**不要提交**。
- `%LOCALAPPDATA%\YichenWeChatVault` 下是**解密后的明文快照**（每次约 600MB），不要同步网盘、不要上传、不要复制进仓库。
- **群友头像属于他人个人信息**。自己复盘可以；公开发布前请征得本人同意，或做模糊/占位处理。
- 导出文本发给模型接口时，等于把聊天内容交给了该服务商，请自行判断是否合规。
- 本工具只读本机数据库，不修改微信、不发送消息。

---

## 常见问题

**Q：`init` 找不到 `xwechat_files`？**
在微信「设置 → 文件管理」里看实际路径，手动把 `config.json` 的 `db_root` 指到 `<xwechat_files>/<账号>/db_storage`。

**Q：`refresh` 报 “Verified keys unavailable”？**
微信版本可能超出上游支持范围，或采集时微信未运行。先确认微信登录，再重试；仍失败就等 `yichen-wechat-local-vault` 更新。

**Q：朋友圈、收藏能导出吗？**
当前实测只能稳定拿到聊天记录。`--all` 全库采集可能因个别库密钥不匹配整体失败，不建议依赖。

**Q：模型输出的 JSON 解析失败？**
换更强的模型，或把 `prompts/extract.md` 里的“输出纯 JSON”再强调一遍。也可以让模型分两步：先列提纲，再填 JSON。

**Q：群友头像没出来？**
说明该发言人没有匹配到 `contact` 表里的头像地址，或当天没发言。留空时会自动显示名字首字。

---

## 依赖与致谢

- 采集层：[yichen-wechat-local-vault](https://github.com/mcncarl/yichen-skills)（MIT）
- 渲染：Jinja2
- 截图：Playwright + Chromium

本项目只做上层封装：按会话名查询、按天导出、结构化提炼、模板渲染。

---

## License

MIT
