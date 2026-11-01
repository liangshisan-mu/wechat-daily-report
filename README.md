# 把微信群一天的消息，变成一张能看的报告图

![示例长图](docs/example.png)

你只需要告诉它**群名**和**日期**，它就会把这个群当天所有消息读完，生成上面这样一张竖版长图：标题、核心议题、数据、双栏对比、编号批注、群友发言、原话引用、行动清单。

不用服务器，不用数据库，不用写代码。数据全程留在你自己的电脑里。

---

## 它能做什么，不能做什么

**能做：**

- 读某个群某一天的全部消息
- 自动统计：多少条、多少人发言、聊了哪些话题
- 提炼成一份结构化的报告
- 生成 PNG 长图，直接发群、发朋友圈、做复盘材料
- 群友发言卡片自动配上本人微信头像

**不能做：**

- 不能读朋友圈、收藏（当前只稳定支持聊天记录）
- 不能修改微信、不能替你发消息
- 不能在 Mac 上跑（采集工具目前只支持 Windows）
- 不能保证每个微信版本都能用（升级后可能要等工具更新）

---

## 你需要准备什么

| 东西 | 要求 |
|---|---|
| 电脑 | Windows 10 / 11 |
| 微信 | 电脑版 4.x，**已登录并保持打开** |
| Python | 3.12（下面教你装） |
| 磁盘 | 至少 2GB 空闲（每次采集约 600MB） |
| AI 模型 | 可选。不配也能用，只是需要手动把聊天交给 AI |

---

## 第一步：装 Python（约 5 分钟）

1. 打开 <https://www.python.org/downloads/>
2. 点黄色按钮下载 **Python 3.12**
3. 双击安装包
4. **最重要的一步**：安装界面最下面有一个勾选框
   `Add python.exe to PATH`
   **一定要勾上**，然后点 `Install Now`
5. 装完后验证：
   - 按 `Win + R`，输入 `cmd`，回车
   - 输入 `python --version`，回车
   - 看到 `Python 3.12.x` 就成功了

> 如果提示“python 不是内部或外部命令”，说明第 4 步没勾。重新运行安装包，选 Modify，把 Add to PATH 勾上。

---

## 第二步：把项目下载到电脑

### 方法 A：下载 ZIP（不会用 Git 就选这个）

1. 打开仓库页面
2. 点绿色的 `Code` 按钮 → `Download ZIP`
3. 解压到一个简单路径，比如 `D:\wechat-daily-report`

> 路径里尽量不要有空格和特殊符号，后面命令不容易出错。

### 方法 B：会用 Git 的话

```powershell
git clone https://github.com/<你的账号>/wechat-daily-report.git
cd wechat-daily-report
```

---

## 第三步：一键安装（约 3-5 分钟）

1. 打开项目文件夹
2. 在文件夹**空白处**按住 `Shift` + 鼠标右键
3. 选 **“在此处打开 PowerShell 窗口”**
4. 复制下面这行，粘贴进去，回车：

```powershell
powershell -ExecutionPolicy Bypass -File setup.ps1
```

5. 它会自动做四件事：
   - 创建 Python 虚拟环境
   - 安装依赖
   - 下载截图用的浏览器（Chromium，约 150MB）
   - 下载微信采集工具到 `vendor` 文件夹

6. 看到 `== 5/5 完成 ==` 就好了。

> **报错“因为在此系统上禁止运行脚本”？**
> 说明命令没复制完整。必须带上开头的 `powershell -ExecutionPolicy Bypass -File`。

---

## 第四步：初始化（连接你的微信）

**先确认微信电脑版已经登录，并且窗口开着。**

在同一个 PowerShell 窗口输入：

```powershell
.\.venv\Scripts\python.exe run.py init
```

接下来它会：

1. 自动扫描电脑，找到微信的数据文件夹，列出来让你选
   ```
   找到这些微信数据根目录：
     1. E:\微信记录\xwechat_files
   ```
   输入序号，回车。

2. 列出这个数据目录下的账号，让你选
   ```
     1. wxid_xxxxxxxx
   ```
   输入序号，回车。

3. 探测微信进程，读取数据库
4. 最后显示：
   ```
   已写入 ...\config.json
   ```

**如果找不到数据目录：**

打开微信 → 左下角三条横线 → 设置 → 文件管理 → 点“打开文件夹”。
看到 `xwechat_files` 这个文件夹后，把它的完整路径记下来。
然后手动编辑项目里的 `config.json`，把 `db_root` 改成：

```
<刚才的路径>\<账号文件夹>\db_storage
```

---

## 第五步：先看示例，再生成自己的

### 5.1 先跑示例（不会碰你的微信）

```powershell
.\.venv\Scripts\python.exe report/build.py --data report/example.json
```

打开 `out\example.png`，这就是最终效果。示例用的是虚构的读书会数据。

### 5.2 生成你自己群的

```powershell
.\.venv\Scripts\python.exe run.py build --group "你的群名" --date 2026-10-31
```

- `--group` 后面写群名，**不用写全**，能匹配到就行
- `--date` 写你要哪一天，格式 `年-月-日`
- 第一次会自动采集一次快照（约 20 秒），微信要保持打开

跑完会得到三个文件（在 `out` 文件夹）：

```
out\你的群名_2026-10-31.json    ← 提炼后的内容，可以改
out\你的群名_2026-10-31.html    ← 网页版，可以改样式
out\你的群名_2026-10-31.png     ← 最终长图
```

---

## 关于 AI 提炼：配不配 key 都能用

### 方式一：配一个模型 key（推荐，全自动）

编辑项目里的 `config.json`，找到 `llm` 这一段：

```json
"llm": {
  "base_url": "https://api.deepseek.com/v1",
  "api_key": "在这里填你的 key",
  "model": "deepseek-chat"
}
```

DeepSeek 的 key 在 <https://platform.deepseek.com/> 申请，充 10 块钱能用很久。
也支持 OpenAI、通义、Moonshot 等任何“OpenAI 兼容”接口，改 `base_url` 和 `model` 就行。

填好后，`run.py build` 会自动：读聊天 → 调模型 → 生成 JSON → 出图。

### 方式二：不配 key，手动交给 AI（免费）

`run.py build` 跑到一半会停下来，提示你：

```
未配置 llm.api_key，已停在导出这一步。
聊天记录：exports\你的群名_2026-10-31.md
```

这时候：

1. 打开 `exports` 里的 `.md` 文件，全选复制
2. 打开 WorkBuddy / 豆包 / ChatGPT / Claude
3. 把 `prompts/extract.md` 的内容 + 聊天记录一起发给它
4. 让它按结构输出 JSON
5. 把 JSON 保存成 `out\你的群名_2026-10-31.json`
6. 再运行：

```powershell
.\.venv\Scripts\python.exe report/build.py --data "out\你的群名_2026-10-31.json"
```

---

## 常用命令速查

| 我想做什么 | 输入什么 |
|---|---|
| 看看有哪些群 | `.\.venv\Scripts\python.exe wx.py chats --group` |
| 读某个群最近 100 条 | `.\.venv\Scripts\python.exe wx.py read "群名" --limit 100` |
| 在群里搜一个词 | `.\.venv\Scripts\python.exe wx.py search "关键词" --chat "群名"` |
| 导出某天聊天 | `.\.venv\Scripts\python.exe wx.py export "群名" --start 2026-10-31` |
| 更新最新消息 | `.\.venv\Scripts\python.exe run.py refresh` |
| 清理旧快照 | `.\.venv\Scripts\python.exe wx.py clean --keep 2 --yes` |

> 提示：每次输入 `.\.venv\Scripts\python.exe` 很长。可以先执行一次
> `Set-ExecutionPolicy -Scope Process Bypass; .\.venv\Scripts\Activate.ps1`
> 之后直接输 `python run.py ...` 就行。

---

## 出错了怎么办

| 你看到的提示 | 原因 | 怎么解决 |
|---|---|---|
| `python 不是内部或外部命令` | 装 Python 时没勾 PATH | 重装，勾 `Add python.exe to PATH` |
| `因为在此系统上禁止运行脚本` | 命令没复制完整 | 完整复制 `powershell -ExecutionPolicy Bypass -File setup.ps1` |
| `没找到 xwechat_files` | 微信数据不在默认位置 | 微信设置 → 文件管理 → 打开文件夹，手动填 `db_root` |
| `Verified keys unavailable` | 微信版本太新，或采集时微信没开 | 确认微信登录并保持打开；还不行就等采集工具更新 |
| `找不到 snapshot_reader` | 采集工具没下载成功 | 重新跑 `setup.ps1`，看 `vendor` 文件夹里有没有东西 |
| 模型返回的不是 JSON | 模型太弱或指令没读全 | 换更强的模型，或分两步：先列提纲再填 JSON |
| 群友头像没显示 | 这个人当天没发言，或没匹配到头像 | 正常，会显示名字首字 |
| 图里内容不对 | 模型理解偏了 | 直接改 `out\xxx.json` 再跑 `report/build.py` |

---

## 关于隐私，必须说清楚

这个工具会碰到非常私密的数据，请务必做到：

1. **不要把手里的文件夹上传到网盘或 GitHub**
   - `config.json`、`exports`、`out`、`report\assets`、`vendor` 都已在 `.gitignore` 里
   - 但你自己手动复制时要注意

2. **快照是明文**
   - 采集后的数据在 `C:\Users\<你>\AppData\Local\YichenWeChatVault`
   - 每次约 600MB，含全部聊天原文
   - 不要同步、不要上传、不要发人

3. **群友头像属于别人的个人信息**
   - 自己复盘看，没问题
   - 要发到小红书 / 公众号 / 公开群，请先征得本人同意，或者把头像做模糊处理

4. **导出文本发给 AI 时**
   - 等于把聊天内容交给了那家模型服务商
   - 敏感群建议用本地模型，或手动删掉敏感内容再发

---

## 项目结构（想改代码再看）

```
wechat-daily-report/
├── run.py                 一条命令入口
├── wx.py                  快捷查询入口
├── wxread/                采集与读取
├── report/                模板与渲染
│   ├── template.html      长图模板（改颜色改这里）
│   ├── build.py           JSON → HTML → PNG
│   └── example.json       示例数据
├── prompts/extract.md     聊天 → JSON 的提炼指令
├── setup.ps1              一键安装
└── config.json            你的本机配置（不会上传）
```

想改视觉：编辑 `report/template.html` 最上面的 CSS 变量：

```css
:root{
  --bg:#F4F1E8;      /* 米白底 */
  --green:#1C3A2A;   /* 墨绿 */
  --clay:#B65C34;    /* 陶土橙 */
}
```

---

## 致谢

采集层基于开源项目 [yichen-wechat-local-vault](https://github.com/mcncarl/yichen-skills)，本项目只做上层的“按群按天导出 + 结构化提炼 + 模板渲染”。

## License

MIT
