# 开发工具与资源准备

## 初始化

先由 AI 只读检查并简要说明准备范围；用户确认后执行。用户直接运行入口或明确要求初始化，也表示授权本次准备。

需要 Python 3.10+、联网和允许运行本地脚本的 Windows PowerShell 环境；不自动更改执行策略、接受协议或覆盖全局配置。

```powershell
./dev_tools/bootstrap_workspace.ps1
# 可选：指定解释器，或只准备资源文件
./dev_tools/bootstrap_workspace.ps1 -Python "Python解释器完整路径"
./dev_tools/bootstrap_workspace.ps1 -ResourcesOnly
```

入口检查工作区核心和官方版本、补齐全部资源、建立 `python_env/` 并初始化/枚举 MCP 服务。重复运行复用完整文件；报告在 `local_state/FIRST_USE_REPORT.json`，包含本次时间、结果、失败阶段和原因。`ATTENTION_REQUIRED` 表示资源缺口、更新线索或未知状态需要处理，不能直接宣布全部就绪。

| 资源 | 本机位置与用途 |
| --- | --- |
| Blockbench | `external/Blockbench/`，建模便携程序及许可 |
| 网易建模与 attachable 插件 | `external/blockbench-netease-modeling/`、`external/blockbench-bedrock-attachable/` |
| Tracy | `external/mcdk-mcp-tracy/`，性能采样 MCP、原生 CLI 和许可 |
| 像素转换核心 | `external/PixelArtConverter/`，配合原创适配器处理已有授权图片 |
| ModPC MCP | `external/ModPC-MCP-Tool/`，连接游戏的桥接服务 |
| 网易文档 | `../docs/mcdocs/`、`../docs/mcguide/`、`../docs/mconline/`，仅正文 |
| Python 依赖 | `python_env/`，MCP、pylint、Tracy 与图片转换依赖 |

MCStudio 登录/开发包选版、插件 GUI 加载与 AI 客户端 MCP 接入分别完成，入口见 [OFFICIAL_SETUP.md](OFFICIAL_SETUP.md)。文件和服务枚举就绪不代表这些界面操作或游戏验收通过。

## 检查与按需补充

```text
python -B dev_tools/prepare_workspace.py --status --task all
python -B dev_tools/verify_local_environment.py --profile workspace
python -B dev_tools/prepare_workspace.py --task model --fetch --fetch-docs
```

`--status` 严格只读；配合 `--task all` 可列出全部资源缺口。未选择任务时，`required_tools_missing` 为空不表示工具齐全，仍需查看各资源状态。

任务支持 `api`（文档）、`model`（Blockbench 与两个插件）、`profile`（Tracy）、`pixel`（转换核心）、`debug`（ModPC MCP）及 `all`。`--tools <ID> --fetch` 只准备指定工具。`--fetch-docs` 复用完整文档库；需要官网新正文时加 `--refresh-docs`，显式刷新不会被旧来源环境变量覆盖。

本地来源也可使用：

```text
python -B dev_tools/prepare_workspace.py --task api --docs-source "已有文档目录或ZIP"
python -B dev_tools/prepare_workspace.py --tools modpc --tool-source "modpc=已有工具目录或ZIP"
```

环境变量 `NETEASE_DOCS_SOURCE`、`NETEASE_MODPC_SOURCE` 可指定来源，不扫描个人目录。工具必须匹配固定清单；文档来源若明确比已安装正式版本旧，拒绝覆盖。

`manifests/resources.json` 固定工具版本/提交、URL、哈希与使用依据。先暂存并验证，成功后更新；失败保留旧资源。已有工具哈希变化先定位原因，重装可加 `--repair`，旧副本保存在 `local_state/backups/`。正文的本地修改也不静默覆盖。

## Python 与启动入口

初始化会安装独立依赖；单独准备时使用：

```powershell
./dev_tools/setup_python.ps1
./dev_tools/setup_python.ps1 -WithTracy -WithPixelTools
```

需先准备对应资源，可用 `-Python <完整路径>`。启动器采用 `NETEASE_TOOLS_PYTHON` 或本目录 `python_env/Scripts/python.exe`。EXE 与 PowerShell 入口面向 Windows。

- ModPC：`start_modpc_mcp.ps1`，游戏端默认 `127.0.0.1:14520`，桥接 HTTP 默认 `127.0.0.1:3002/mcp/`；用户需进入测试存档。
- Tracy：`start_tracy_mcp.ps1`，STDIO；采样取决于游戏协议兼容，FPS/jank 分支另需 MCDK。
- Blockbench：`start_blockbench.ps1 -Python <可用解释器>`，独立本机配置。插件在对应源码目录的 `plugins/` 中，从 GUI 加载 `.js`。
- 图片转换：[pixel_art_converter/README.md](pixel_art_converter/README.md)。
- MCP 客户端配置：[config/mcp_endpoints.example.json](config/mcp_endpoints.example.json)。

```text
python -B dev_tools/check_local_tools.py --tools tracy modpc
python -B dev_tools/check_pylint_errors.py <behavior-pack-dir>
```

MCP 自检只初始化和枚举，不调用游戏工具。pylint 是本地投稿辅助检查，结论不能替代平台审核。

## 校验与分享范围

- `--profile source`：严格核对公开核心原件，允许本机资源尚未安装。
- `--profile workspace`：日常开发检查；列出规则、文档、组件登记与基线的正常编辑，仍校验脚本、元数据及已安装资源。
- `--profile full` / `--full`：严格核对公开核心，并要求全部工具和文档存在；不代表依赖、客户端或游戏通过。
- `--task <任务>`：额外要求该任务的资源，避免无关可选工具阻塞工作。

退出码 `0` 为所选范围通过，`1` 为入口/校验错误，`2` 为资源未齐、准备未成功或版本检查需关注；具体看结果与原因。pylint 使用其专用退出码。

GitHub 与直接分享 ZIP 保持同一套公开核心。`external/`、`python_env/`、`local_state/`、正文、图片转换依赖和本机报告均不分发；唯一公开报告为 `reports/RELEASE_CHECK.json`。用 `export_template.py --out <输出ZIP>` 导出，已有输出需明确替换时加 `--overwrite`。维护核心后审阅并同步 `manifests/distribution_manifest.json`，再运行原件校验与导出，不能关闭哈希检查来代替发布维护。
