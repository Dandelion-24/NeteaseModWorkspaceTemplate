# 网易我的世界组件开发工作区模板

面向 Minecraft 中国版、MCStudio、网易 Python ModSDK 与网易 JSON UI。提供组件目录约定、九个通用技能、接口核对方法，以及工具、文档准备和校验脚本。官方正文、第三方工具和本机环境在初始化时获取，不随模板分发。

## 交给 AI 使用

把文件夹交给 AI，发送：

> 请先读取 AGENTS.md，简要说明工作区用途并检查资源；经我确认后，补齐开发工具、网易文档和依赖，再报告可用状态与需要我完成的接入步骤。

AI 先做只读检查，简短说明：“这是网易组件开发模板，目前缺少工具和文档。是否现在从上游获取所需资源，并在本目录建立依赖环境？”你确认后，它应立即执行并跟进结果；直接要求“初始化这个工作区”也表示同意准备，无需再次确认。

自动准备范围：Blockbench、网易建模与 attachable 两个插件、Tracy、像素转换核心、ModPC MCP、网易正式文档正文，以及独立 Python 依赖。图片不保存；完整资源复用，中断可重跑，不创建模组或修改全局 AI 配置。需要联网和可用的 Python 3.10+。

在 Windows PowerShell 手动初始化可执行：

```powershell
./dev_tools/bootstrap_workspace.ps1
# Python 不在 PATH 时：
./dev_tools/bootstrap_workspace.ps1 -Python "Python解释器完整路径"
```

结果保存在本机 `dev_tools/local_state/FIRST_USE_REPORT.json`。MCStudio 安装/登录与开发包选版、Blockbench 插件加载、AI 客户端 MCP 接入按各自界面完成；文件准备、服务枚举和游戏测试分别记录。工作区名称可在初始化后按需修改，不是前置条件。

## 当前版本与后续更新

当前默认 ModSDK、对应 Bedrock 与格式版本以 [PLATFORM_BASELINE.json](docs/PLATFORM_BASELINE.json) 为准。首次初始化、开工和交付前检查官方正式版本；确认新正式版及对应开发包后，同步更新模板默认目标、文档、相关规则和校验约定。已有组件按兼容声明迁移，保留历史证据；更新文档不等于游戏验收通过。流程见 [文档与版本更新](docs/README.md#正式文档与平台版本更新)。

## 目录与入口

| 内容 | 入口 |
| --- | --- |
| AI 工作规则与首次引导 | [AGENTS.md](AGENTS.md) |
| 带注释的目录、九个技能职责与状态定义 | [WORKSPACE.md](WORKSPACE.md) |
| 组件登记及目录约定 | [components/README.md](components/README.md) |
| 工具准备、启动和 MCP 自检 | [dev_tools/README.md](dev_tools/README.md) |
| 官方获取依据与接入 | [OFFICIAL_SETUP.md](dev_tools/OFFICIAL_SETUP.md) |
| 文档来源与更新 | [docs/README.md](docs/README.md) |
| 接口与双端界面检查 | [接口核对表](.agents/skills/core/netease-modsdk-core/references/api-contract-checklist.md)、[界面质量合同](.agents/skills/core/netease-visual-assets/references/ui-ux-quality.md) |
| 公开核心校验摘要 | [RELEASE_CHECK.json](dev_tools/reports/RELEASE_CHECK.json) |

日常检查与补充资源：

```text
python -B dev_tools/prepare_workspace.py --status
python -B dev_tools/verify_local_environment.py --profile workspace
python -B dev_tools/prepare_workspace.py --task model --fetch --fetch-docs
```

## 开发与分享

- 实际开发时再创建组件类型、登记和版本工程。服务端验证、平台正确性、电脑/手机双端可用与证据真实性是硬约束；视觉风格和页面形式按任务确定。
- GitHub 与直接分享使用同一套公开核心。运行 `python -B dev_tools/export_template.py --out <输出ZIP>` 导出，排除后来取得的工具、正文、环境和状态。维护公开核心后先审阅并同步 `distribution_manifest.json`，再执行源码校验和导出。
- 原创部分适用 [MIT License](LICENSE)；外部资源按[上游使用边界](THIRD_PARTY_NOTICES.md)处理。本机获取不增加再分发权利。
