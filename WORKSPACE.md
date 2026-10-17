# 工作区结构与技能说明

本工作区用于维护 Minecraft 中国版 / MCStudio / 网易 Python ModSDK 组件。当前 ModSDK、对应引擎与格式约定见 [PLATFORM_BASELINE.json](docs/PLATFORM_BASELINE.json)。确认新正式版后按根规则同步默认目标与相关约定；已有组件按兼容声明迁移。

模板不附带任何组件工程。`components/catalog.json` 是空的，`mcstudio_project/` 与 `source_structures/` 只有约定说明；第一个组件按 `AGENTS.md` 的"新增组件流程"创建。

## 当前结构（带注释）

```text
NeteaseModWorkspaceTemplate/
├── README.md                       # 分享版首页和首次接手流程
├── AGENTS.md                       # 稳定规则、自动准备与证据边界
├── WORKSPACE.md                    # 目录与九个技能的详细分工
├── LICENSE                        # 原创部分 MIT
├── THIRD_PARTY_NOTICES.md          # 外部来源与本地获取边界
├── .gitignore                     # 排除本机文本、工具、环境和缓存
├── .agents/skills/core/            # 九个通用技能，无组件专属技能
│   ├── netease-mod-direction-planner/   # 选题、需求、竞品和可行性
│   ├── netease-component-architecture/  # 目录、登记和组件边界
│   ├── netease-modsdk-core/             # 严格核对 ModSDK 与数据流
│   │   └── references/api-contract-checklist.md  # 接口合同核对表
│   ├── netease-visual-assets/           # 模型、纹理、图标和 UI
│   │   └── references/ui-ux-quality.md  # 风格可选、质量与双端硬约束
│   ├── netease-hud-launcher-button/     # PC/手机入口输入与生命周期
│   ├── netease-project-validator/       # 单个工程的静态检查
│   ├── netease-workspace-audit/         # 跨工程只读体检与回归脚本
│   ├── netease-mcstudio-delivery/       # MCStudio/Add-on 两种包
│   └── netease-log-review/              # 运行日志与证据覆盖复盘
├── components/                    # 空 catalog、字段说明；按任务建组件
├── mcstudio_project/README.md     # 版本化运行工程约定
├── source_structures/README.md    # 原始结构与源地图只读归档约定
├── docs/                          # 随附索引和原创方法，正文仅在本机准备
│   ├── README.md                  # 官网正文获取、本地导入与正式版更新
│   ├── SOURCES.json               # 官方来源、预期路径和获取边界
│   ├── PLATFORM_BASELINE.json     # 当前默认版本、核对日期及正式版来源
│   ├── SYNC_STATE.md              # 初始未安装状态与核对口径
│   ├── UPSTREAM_SOURCES.md        # 正式、beta、历史和权利边界
│   ├── PLATFORM_LESSONS.md        # 通用平台核对方法
│   └── PROBE_METHOD.md            # 最小探针和证据分层
├── dev_tools/                     # 随附原创脚本，不进入游戏交付包
│   ├── README.md / TOOL_INDEX.md  # 准备步骤和任务路由
│   ├── bootstrap_workspace.ps1    # 用户确认后补齐资源、依赖与服务枚举
│   ├── OFFICIAL_SETUP.md          # 官方入口、获取依据和接入步骤
│   ├── prepare_workspace.py       # 状态、资源获取与本地导入入口
│   ├── resource_manager.py        # 固定哈希、安全安装与资料清单
│   ├── verify_local_environment.py  # 原件、工作区、完整资源与任务检查
│   ├── export_template.py          # 仅导出公开核心，排除本地资源
│   ├── sync_netease_docs_from_web.py # 官网正文刷新、导航检查与本地导入
│   ├── official_docs.py           # 限速获取官方正文；不下载图片
│   ├── setup_python.ps1           # 本机 Python 依赖环境
│   ├── requirements-tools.txt     # 宿主依赖；不含引擎运行依赖
│   ├── resolve_python.ps1         # 启动器解释器与资源检查
│   ├── start_modpc_mcp.ps1        # ModPC 本机 HTTP 入口
│   ├── start_tracy_mcp.ps1        # Tracy STDIO 入口
│   ├── start_blockbench.ps1       # 独立本机配置的建模入口
│   ├── check_local_tools.py       # MCP 初始化和枚举，不调用游戏工具
│   ├── check_pylint_errors.py     # 行为包错误级辅助预检
│   ├── pylint_repro_min.py        # 通用 pylint 诊断例子
│   ├── config/                   # 无个人路径的连接示例
│   ├── manifests/                # 核心文件清单与固定上游来源
│   ├── reports/RELEASE_CHECK.json # 随仓库保留的公开核验摘要
│   ├── tests/                    # 获取、导入、故障和就绪回归
│   └── pixel_art_converter/      # 原创图片转换适配器和依赖说明
├── logs/README.md                 # 日志保存与隐私边界
└── tmp/README.md                  # 临时文件与清理约定
```

每个技能都有 `SKILL.md`，其中五个附带 `agents/openai.yaml` 界面元数据。审计技能附带只读脚本与回归；其他技能以流程和参考合同为主。两份共用详细要求是[接口核对表](.agents/skills/core/netease-modsdk-core/references/api-contract-checklist.md)与[界面质量合同](.agents/skills/core/netease-visual-assets/references/ui-ux-quality.md)，其他技能引用它们。

初始化后本机可能新增 `docs/mcdocs/`、`docs/mcguide/`、`docs/mconline/`、`docs/LOCAL_MANIFEST.json`、`dev_tools/external/`、`dev_tools/python_env/` 和 `dev_tools/local_state/`；它们不在上述公开结构中，也不得进入公开 ZIP。完整性通过、资源就绪、接口核对与实机验收分别记录。

## 文件与职责边界

| 要维护的内容 | 归属 | 说明 |
| --- | --- | --- |
| 所有组件都适用的稳定工作规则 | 根 `AGENTS.md` | 不放具体组件的版本清单与调试流水 |
| 一类组件的额外规则 | `components/<type>/AGENTS.md` | 真正需要该类型时再创建 |
| 单个组件的边界、入口和证据导航 | `components/<type>/<component-id>/COMPONENT.md` | 与 catalog 的组件身份和运行工程一致 |
| 当前版本的 BP/RP 和 Python 逻辑 | `mcstudio_project/<ProjectName>_v<version>/` | 按版本隔离，当前指针由 catalog 管理 |
| 工程专用校验、打包与回归脚本 | 该工程的 `tools/` | 具体工程建立后按需编写，模板没有预制实现 |
| 运行证据、接口核对和发布记录 | 该工程的 `validation/` | 保留版本、构建、端侧、场景与证据范围 |
| 已关闭问题及修复边界 | 该工程的 `ISSUE_HISTORY.md` | 先在这里完成问题闭环，再提炼通用方法 |
| 服务于多个工程的宿主维护工具 | `dev_tools/` | 不被组件运行代码引用，也不打进游戏包 |
| 官方依据与通用查证方法 | `docs/` | 官方来源与本地导入、自写方法、项目实测结果分开 |
| AI 遇到某类任务时的工作流程 | `.agents/skills/` | 流程会指导 AI 查文档、改代码或跑工具，本身不等于这些工具已存在 |

上表中的 `<type>`、`<component-id>`、`<ProjectName>` 和工程内部目录是后续创建位置的约定，不表示模板已带有这些组件。当前目录无需预建更多类型。

## 九个技能的职责

以下名称与实际 `SKILL.md` 一一对应。按当前任务选择相关技能，不要求每次把九个技能全部执行一遍。

### 1. 选题与可行性：netease-mod-direction-planner

[技能入口](.agents/skills/core/netease-mod-direction-planner/SKILL.md)。解决“下一步做什么、玩家需要什么、现有供给多不多、网易平台能否支持”的问题。

- **使用时机**：规划新模组、寻找创意、比较候选、调查市场与差异化。
- **主要工作**：完整市场研究检索网易资源中心及国内外论坛、资源与视频；区分玩家反馈、作者宣传与可见热度；核对中国版直接竞品、官方活动和文档更新；把决定卖点的能力拆为可查证的平台操作。轻量创意与已有方案细化按用户要求缩小范围。
- **产出**：在对话中给出候选列表或表格，说明核心循环、需求依据、差异、首发范围、投入和可行性。需要保留时另存带日期和来源的调研记录。
- **边界**：不自动立项、创建工程、报名或投稿；未能访问的数据明确留缺口，不推测销量或将国际热度直接当成中国版市场结果。视觉、装饰与内容题材可以靠制作质量形成价值，存在竞品也不自动否决用户选择。

### 2. 目录与组件边界：netease-component-architecture

[技能入口](.agents/skills/core/netease-component-architecture/SKILL.md)。解决“这个组件放在哪里、怎么登记、与其他组件怎样隔离”的问题。

- **使用时机**：正式新增组件、增加类型、调整目录、拆分共享内容、升版或清理历史工程。
- **主要工作**：确定类型和稳定 `component_id`；维护 catalog、`COMPONENT.md` 与运行项目指针；划分客户端、服务端、公共协议和私有数据；将规则放在全局、类型或组件的正确层级。
- **产出**：可解释的目录分层、组件登记、边界说明、相关技能和资产映射。清理任务还包括证据保留与引用/工具依赖检查。
- **边界**：不提前创建空分类；设计阶段可登记 `design`，不强迫先造运行工程或过度拆模块；不让组件读取兄弟组件私有状态；升版不自动删除旧工程，历史证据保持原义。

### 3. ModSDK 实现：netease-modsdk-core

[技能入口](.agents/skills/core/netease-modsdk-core/SKILL.md)。解决“怎样用网易 Python ModSDK 正确实现与诊断功能”的问题。

- **使用时机**：编写或修改 Python 系统、引擎事件、自定义通信、目标识别、持久化与世界操作。
- **主要工作**：实际打开本地正式正文，逐接口核对所属端、宿主、签名、事件字段、返回形状和空值/失败语义；维护 Python 2.7 兼容；闭合请求、服务端重验、调用、读回、响应与展示。区分原生返回和项目包装合同，检查导入、成员、取消对象、持久化、部分成功与恢复路径。
- **产出**：实现代码、可信数据流说明、接口依据、静态/宿主测试结果和实机待测项。
- **边界**：不默认套用国际版 JavaScript API；候选参数经服务端重新验证才能使用；不能猜字段、把单值误当二元返回或用异常吞掉缺失实现。未知结果先对账，非幂等写操作不盲目重发；宿主测试不能替代引擎证据。

### 4. 模型与美术资产：netease-visual-assets

[技能入口](.agents/skills/core/netease-visual-assets/SKILL.md)。解决“需要什么视觉资产、怎样制作并正确接入资源包”的问题。

- **使用时机**：新增或修改模型、贴图、物品图标、UI 面板/框体，或统一视觉方向。
- **主要工作**：区分几何、纹理、图标和 JSON 布局；确定用途、透明度、像素密度和实际显示尺度；统一资产家族的轮廓、材质、留白与反馈；核对模型原点、UV、面向、图集和资源路径；按共用质量要求检查菜单结构、可读性、双端输入与状态。
- **产出**：视觉简报、模型/图片/资源配置、来源说明和引用检查结果，以及游戏内观感与拼缝验收步骤。
- **边界**：原生风格为未指定时的默认建议，其他风格可用，不锁死配色、尺寸、色数、页数或图像模型。图片不能替代模型或 JSON 文字/交互；插件预览不能证明手机和游戏内渲染通过。

### 5. 常驻入口交互：netease-hud-launcher-button

[技能入口](.agents/skills/core/netease-hud-launcher-button/SKILL.md)。专门解决“屏幕上常驻的菜单按钮怎样可靠点击、拖动并跨端工作”的问题。

- **使用时机**：新增 HUD 入口，修复入口点不到、拖不动、出屏、重进后失效或 PC/手机表现不同。
- **主要工作**：依组件约定区分点击、适用的拖动、隐藏与关闭；核对 PC 指针与触屏输入路径；检查吞输入、子控件命中、层级、锚点、单位转换、边界夹取和节点生命周期；按实际时间识别适用手势。
- **产出**：入口按钮的 UI/输入/状态修改，以及 PC GUI Scale 3/4/5、手机横竖屏的交互回归步骤。
- **边界**：只在需要 HUD 入口时使用，负责入口链路；阈值、尺寸、按键与是否可拖服从组件约定并经实测。不把每帧重建或禁用全部子控件当成通用修复。

### 6. 单工程静态校验：netease-project-validator

[技能入口](.agents/skills/core/netease-project-validator/SKILL.md)。解决“当前这个组件的源码、协议、资源和工程配置是否相互一致”的问题。

- **使用时机**：功能修改完成、版本更新、回归或打包前，需要集中检查一个目标工程。
- **主要工作**：按目标解释器检查 Python/JSON、导入和成员，按接口合同检查回调、请求字段、原生/包装返回和失败消费；检查版本依赖、UI 状态、资源链与打包排除。针对重复/部分成功/未知结果补必要样例，结构放置专项只在适用时执行。
- **产出**：带文件与依据的 `PASS`、`WARNING`、`FAIL` 和 `RUNTIME TEST REQUIRED`；已有工程校验脚本按需执行，没有时按任务范围编写。
- **边界**：模板没有覆盖所有未来组件的万能校验器；Python 3 解析拒绝不能直接证明 Python 2 语法错误，虚构的模拟返回不能证明接口正确。设计和局部修改按实际风险检查，不凭静态结果声称游戏通过。

### 7. 全工作区审计：netease-workspace-audit

[技能入口](.agents/skills/core/netease-workspace-audit/SKILL.md)。解决“整个工作区是否一致、不同组件是否发生冲突、当前引用是否仍可达”的问题。

- **使用时机**：检查整个工作区、整理历史版本、组件拆分、发现文档版本漂移，或发布前做跨工程复核。
- **主要工作**：运行只读 `audit_workspace.py`，扫描交付 ZIP、Manifest/UUID、Python 2 语法风险、部分 UI 风险、物品链、包内噪声、catalog 引用、可匹配的结构哈希和跨组件资源路径；再人工对照文档的版本、状态和证据口径。
- **产出**：按失败、警告、通过分类的全区结果，说明跨组件冲突、悬空指针、人工核对项及实机盲区；修改审计器时运行其自带回归测试。
- **边界**：脚本本身只读，不覆盖完整 catalog schema、所有 UI 继承变量、全部机审规则或文档语义；扫描命中须核对实际依据。仅审计时不修改；用户同时授权修复时，处理已确认问题。

### 8. 打包与交付：netease-mcstudio-delivery

[技能入口](.agents/skills/core/netease-mcstudio-delivery/SKILL.md)。解决“要交付什么包、目录应是什么形状、包内是否完整”的问题。

- **使用时机**：制作 MCStudio 导入包、开发者平台 Add-on 投稿包、准备版本交付或诊断导入/包挂载问题。
- **主要工作**：从任务确认目的地；检查 Manifest、版本和依赖；调用或编写工程打包工具；分别检查两种根布局、CRC、重复项、源文件字节、缓存和无关内容排除；按本地上架规则核对机审事项并执行 pylint 辅助预检。
- **产出**：工程 `deliverables/` 下用途明确的 ZIP、包结构与完整性结果、版本说明和剩余手测项。
- **边界**：模板没有预制的工程打包器；准备好包不等于已上传、通过平台审核或在世界启用 BP/RP；发布和上传需有相应任务授权。

### 9. 运行日志复盘：netease-log-review

[技能入口](.agents/skills/core/netease-log-review/SKILL.md)。解决“这一轮真实日志能证明什么、问题出现在哪段、还有什么没看到”的问题。

- **使用时机**：用户提供测试日志，希望检查错误、拒绝、超时、重试、关闭/提交窗口或改动覆盖情况。
- **主要工作**：确认组件、构建和场景；统计时间范围、错误与关键码；合并重复日志；关联请求、动作和结果；检查不带组件前缀的引擎异常；确认目标改动是否真的触发。
- **产出**：分别列出日志直接证明、只能推断和未覆盖的事项，附具体窗口、计数与下一轮取证建议。
- **边界**：日志零报错不能证明功能通过，未触发分支保持未覆盖；合理拒绝不必为零。仅复盘时只读；用户已要求修复则在定位后按对应开发技能处理，不重复询问已有授权。

## 技能怎么配合

| 当前任务 | 主要技能 | 按需要配合 | 对应的结果 |
| --- | --- | --- | --- |
| 还没决定做什么 | 方向规划 | ModSDK 核心用于可行性核对 | 候选与证据，不自动建立组件 |
| 方案确定，开始立项 | 组件架构 | ModSDK 核心 | 组件目录、登记、边界与工程 |
| 实现玩法或平台逻辑 | ModSDK 核心 | 美术资产；有入口按钮时加 HUD 技能 | 代码、资源、接口依据与待测项 |
| 检查当前工程 | 项目校验 | 交付技能核对包；全区审计查关联影响 | 单工程检查与回归清单 |
| 检查全局一致性或整理历史 | 工作区审计 | 组件架构；目标工程的项目校验 | 跨工程问题、引用与文档核对 |
| 制作交付包 | MCStudio 交付 | 项目校验、工作区审计 | 用途清楚、逐包核验的 ZIP |
| 测试后检查日志 | 日志复盘 | 需要修复时再进入 ModSDK/相关技能 | 本轮证据结论与补测范围 |

最容易混淆的三项分别负责：**项目校验看一个工程内部；工作区审计看整个工作区及组件之间；交付检查实际要发出的包。** 日志复盘补充已发生的运行证据，不能由前三项的静态结果代替。


## 状态登记口径

`components/catalog.json` 的 `version` 与 `status` 描述当前版本，实测结论不自动跨版本继承。三个合法状态：

| status | 含义 | 必填 | 不得声称 |
| --- | --- | --- | --- |
| `design` | 只有设计基线，没有运行工程 | `design_documents`；`version` 与 `runtime_project` 记 `null` | 功能已实现、已实测 |
| `in_development` | 已有正式运行工程，静态或宿主仿真有结论，游戏内零证据或只覆盖部分用例 | `runtime_scope`、`runtime_evidence` | 整体游戏验收通过；局部证据须按用例注明 |
| `runtime_tested` | 有真实运行证据 | `last_runtime_tested_version`、`runtime_evidence`（日期、类型、范围、路径） | 未附证据的逐项通过 |

`runtime_evidence` 要写清证据类型（用户口头确认 / 日志 / 截图 / 录制）与覆盖范围。整体确认可以登记 `runtime_tested`，但必须注明确认来源与未提供的逐项证据，不能自动勾选手测矩阵。发布状态（未投稿 / 审核中 / 已上架）单独记录，不与运行状态混写。

## 交付约定

- MCStudio 导入 ZIP 根目录必须为 `behavior_packs/` 与 `resource_packs/`。
- 开发者平台 Add-on 投稿 ZIP 根目录必须直接为具体 BP/RP 目录。
- 交付 ZIP 统一存放在组件工程内的 `deliverables/` 目录，不放工程根目录。
- 交付包文件名带版本号，扩展名按用途区分：MCStudio 工程导入包用 `_MCStudio.zip`，开发者平台 Addon 投稿包用 `_Addon.zip`。
- 每份 ZIP 均需核验 Manifest、BP/RP 依赖、CRC、重复条目和缓存/临时文件排除。
- 静态检查、平台源码审核与 MCStudio 实机结果必须分开记录；没有游戏证据时标记为 `RUNTIME TEST REQUIRED`。

## 版本与证据保留

- catalog 指向当前版本。升版从当前工程复制出独立目录；旧版按明确保留策略维护，删除须有授权。清理前保存必要证据与回归源，并核对工具依赖和当前文档指针。
- 已删除的工程、包与素材不得被当作当前可用资源，也不得留下悬空的当前指针；历史材料可保留当时路径并标明已删除。恢复或重建须有明确任务与来源。
- `source_structures/` 只读；运行工程与组件 `source_assets/` 只使用副本。

## 模板自身的维护

- 根 `AGENTS.md` 与 `.agents/skills/core/` 是稳定契约，不随单次调试改动。
- 问题先写进组件 `ISSUE_HISTORY.md`；闭环后只把可复用的核对方法与适用边界归并到 `docs/PLATFORM_LESSONS.md`，不携带私人项目记录。
- 改变资源准备脚本时运行 `dev_tools/tests/`；改变审计器时运行其自带回归。只改规则文字时复核语义、适用范围和引用。
