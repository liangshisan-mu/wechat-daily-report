# AGENTS.md

给本地 AI Agent 的部署与使用指令。用户把仓库链接发给你时，按这里执行，**不要让用户手动敲命令**。

仓库：`https://github.com/l18028092047-crypto/wechat-daily-report`

---

## 目标

在本机完成部署，并把用户指定群、指定日期的聊天，生成一张研究报告式长图。

## 一、前置检查

按顺序确认，任何一项不满足就停下来告诉用户怎么解决：

1. 系统是 **Windows**（采集层只支持 Windows）
2. **微信 4.x 已登录并保持运行**（密钥从进程内存读取）
3. Python **3.10+**，推荐 3.12
4. 磁盘剩余 **2GB** 以上

检查命令：

```powershell
python --version
Get-Process | Where-Object {$_.ProcessName -match 'Weixin|WeChat'}
```

## 二、部署

```powershell
# 1. 获取代码（二选一）
git clone https://github.com/l18028092047-crypto/wechat-daily-report.git
# 或下载 ZIP 解压

# 2. 进入目录
cd wechat-daily-report

# 3. 安装依赖（创建 .venv、装 Chromium、拉取采集 skill）
powershell -ExecutionPolicy Bypass -File setup.ps1

# 4. 初始化（自动选第一个数据目录与账号）
.\.venv\Scripts\python.exe run.py init --auto
```

**验收标准：**

- `.venv\Scripts\python.exe` 存在
- `config.json` 存在
- `config.json` 里 `source_id` 和 `db_root` 非空

如果 `init --auto` 失败，改用交互模式 `.\.venv\Scripts\python.exe run.py init`，把选项读给用户听，让他选。

## 三、生成

先问用户两个问题：

1. 群名是什么（不用全名）
2. 要哪一天（格式 `YYYY-MM-DD`）

然后：

```powershell
.\.venv\Scripts\python.exe run.py build --group "群名" --date 2026-10-31
```

### 如果用户没有配置 LLM key

`build` 会停在导出这一步，并打印 `.md` 路径。此时**你自己来完成提炼**：

1. 读 `exports\*.md`
2. 读 `prompts/extract.md` 的结构要求
3. 按结构生成 JSON
4. 写入 `out\<群名>_<日期>.json`
5. 运行：

```powershell
.\.venv\Scripts\python.exe report/build.py --data "out\<群名>_<日期>.json"
```

### 验收标准

- `out\<群名>_<日期>.png` 存在
- 图片宽度 1800px 左右，高度按内容自适应
- 用 `present_files` 把 PNG 给用户看

## 四、出错处理

| 现象 | 处理 |
|---|---|
| `python 不是内部或外部命令` | 让用户重装 Python，勾选 `Add python.exe to PATH` |
| `禁止运行脚本` | 用完整命令 `powershell -ExecutionPolicy Bypass -File setup.ps1` |
| `没找到 xwechat_files` | 让用户打开微信 → 设置 → 文件管理 → 打开文件夹，把路径填进 `config.json` 的 `db_root`（指向 `<账号>/db_storage`） |
| `Verified keys unavailable` | 确认微信登录且运行中；仍失败则是版本不支持，告知用户等上游更新 |
| `找不到 snapshot_reader` | 重跑 `setup.ps1`，检查 `vendor/yichen-wechat-local-vault/scripts/vault_cli.py` 是否存在 |
| 模型输出非 JSON | 换更强模型，或你自己按 `prompts/extract.md` 直接生成 JSON |
| 头像缺失 | 正常，会显示名字首字；说明该发言人当天未发言或 contact 表无头像地址 |

## 五、隐私红线

- 不要把 `config.json`、`exports/`、`out/`、`report/assets/`、`vendor/` 提交到任何仓库
- 不要把快照目录（`%LOCALAPPDATA%\YichenWeChatVault`）上传、同步或复制进项目
- 群友头像属于他人个人信息，公开发布前提醒用户征得同意或做模糊处理

## 六、给用户的最终回复

只报三件事：

1. 图在哪（绝对路径）
2. 用了多少条消息、多少人发言
3. 有没有没搞定的（比如头像缺失、模型提炼失败）
