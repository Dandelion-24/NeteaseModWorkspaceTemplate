# 工具入口索引

| 任务 | 入口 | 结果边界 |
| --- | --- | --- |
| 确认后初始化 | `bootstrap_workspace.ps1` | 资源、依赖与服务枚举分别报告；接入步骤见 OFFICIAL_SETUP |
| 只读资源状态 | `prepare_workspace.py --status --task all` | 不下载、不导入、不修复 |
| 按任务增补 | `prepare_workspace.py --task <任务> --fetch --fetch-docs` | 工具固定哈希，文档当前官网正文；完整资源复用 |
| 刷新官方正文 | `sync_netease_docs_from_web.py --fetch` | 三个家族正文，无图片，完成暂存后更新 |
| 导入已有文档/ModPC | `prepare_workspace.py --docs-source <目录或ZIP>` / `--tool-source modpc=<来源>` | 指定本地来源，不扫描个人目录 |
| 正式文档版本检查 | `sync_netease_docs_from_web.py --check-updates` | 正式导航、模板基线和官方文件元数据分别检查，未知需查证 |
| 组件/跨组件体检 | `.agents/skills/core/netease-workspace-audit/audit_workspace.py` | 静态证据 |
| MCP 握手 | `check_local_tools.py --tools tracy modpc` | 初始化与枚举，不调用游戏工具 |
| 投稿源码预检 | `check_pylint_errors.py <behavior-pack-dir>` | 不自动投稿，不保证平台审核结果 |

参数见 [README.md](README.md)，官方入口与本机使用依据见 [OFFICIAL_SETUP.md](OFFICIAL_SETUP.md)。
