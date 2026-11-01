# 微信群聊 → 日报长图

把微信群某一天的消息，变成一张研究报告式长图。

![示例](docs/example.png)

## 一行命令

### 让本地 AI Agent 部署（推荐）

把仓库链接丢给你的 Agent（WorkBuddy / Claude Code / Cursor），加一句：

> 按仓库里的 `AGENTS.md` 部署并生成报告，不要让我手动敲命令。

`https://github.com/l18028092047-crypto/wechat-daily-report`

### 自己装（Windows PowerShell）

```powershell
irm https://raw.githubusercontent.com/l18028092047-crypto/wechat-daily-report/main/install.ps1 | iex
```

装完双击 **`生成报告.bat`**，输入群名和日期即可。

## 它做什么

| 输入 | 输出 |
|---|---|
| 群名 + 日期 | 一张 PNG 长图 |

一张图包含：核心议题、数据、双栏对比、编号批注、群友发言（真实头像）、原话引用、行动清单。

## 前提

Windows 10/11 · 微信 4.x 已登录 · Python 3.12。

## 更多

- [详细使用说明](docs/使用说明.md)
- [给 AI Agent 的部署指令](AGENTS.md)

## 隐私

聊天、快照、头像、密钥全部留在本地，已在 `.gitignore` 中排除。

## License

MIT
