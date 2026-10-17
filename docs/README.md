# 网易文档获取与核对

公开模板保留来源索引和原创核对方法，不附带网易官方正文或配图。`SOURCES.json` 记录官方入口、正式导航与关键页面；`SYNC_STATE.md` 记录准备口径，不充当已安装凭证。

## 自动取得当前正文

用户确认初始化后，`bootstrap_workspace.ps1` 会自动准备当前官网的三个文档家族正文；独立补齐可用 `prepare_workspace.py --task api --fetch-docs`，完整本地库直接复用。获取过程遵守官网 robots.txt，仅访问指定 HTTPS 官网，最多三个并发且请求启动间隔至少 0.35 秒；不携带登录 Cookie、不绕过访问限制。

保留正文表格、代码、链接与原文来源，不下载图片、视频或附件，也不将图片嵌入正文。缺失配图可能影响理解，依赖配图的步骤应回官网核对。全部暂存通过后才更新本地库；失败保留原库，不能将失败说成“无更新”。

官网离线文件先核对实际版本，不能由下载入口存在推定它适合当前目标。默认参考当前正式在线正文，获取依据见 [OFFICIAL_SETUP.md](../dev_tools/OFFICIAL_SETUP.md)。

## 导入已有资料

把用户已有且可在本地使用的文档目录或 ZIP 作为来源。目录可直接包含 `mcdocs/`、`mcguide/`、`mconline/`，也可包含一层 `docs/`；ZIP 允许这些目录外有唯一的共同前缀。执行：

```text
python -B dev_tools/prepare_workspace.py --task api --docs-source "本地目录或ZIP"
```

也可设置 `NETEASE_DOCS_SOURCE`，AI 在执行任务准备时自动导入；只读 `--status` 不会触发导入。重复来源可复用，更新前会核对已有受维护文件，检测到本地修改时不会静默覆盖。

仅导入 UTF-8 编码的 `.md`、`.txt`、`.html`、`.htm`、`.rst` 正文；不导入图片、工具、账号配置、原始世界或其他组件内容。其他格式或编码先按对应阅读工具核对并明确转为文本。目录链接、ZIP 路径越界、重复路径及符号链接会被拒绝。

导入后生成本机 `docs/LOCAL_MANIFEST.json`，记录真实文件与哈希。三个资料家族均有文本、正式 `mcdocs/1-ModAPI/` 存在且哈希一致时为 `READY_LOCAL`；缺家族为 `PARTIAL`，缺文件或改动为 `CORRUPT`。`READY_LOCAL` 只表示导入范围可检索，不保证整库完整、当前最新或任一 API 已核对。逐接口仍须实际读正文。

## 接口与界面资料入口

以下路径在导入对应资料后存在，公开模板不将它们作为已分发文件；对应官网 URL 统一见 `SOURCES.json`：

| 用途 | 本地路径 |
| --- | --- |
| UI 布局、文字、裁剪与图片属性 | `mcguide/18-界面与交互/30-UI说明文档.md` |
| 图片缩放与九宫切图 | `mcguide/18-界面与交互/11-图片缩放适配与九宫切图.md` |
| UI 控件方法与回调 | `mcdocs/1-ModAPI/接口/自定义UI/UI控件.md` |
| 通用事件与身份来源 | `mcdocs/1-ModAPI/接口/通用/事件.md` |
| 打包与投稿要求 | `SOURCES.json` 中的上架和打包页面 |

按 `mcdocs` → `mcguide` → `mconline` → 同档位已运行代码查证。缺少所需页面时先补齐该资料，不能凭记忆补接口、字段或返回形状。方法见 [PLATFORM_LESSONS.md](PLATFORM_LESSONS.md)、[PROBE_METHOD.md](PROBE_METHOD.md)及[接口核对表](../.agents/skills/core/netease-modsdk-core/references/api-contract-checklist.md)。

## 正式文档与平台版本更新

[PLATFORM_BASELINE.json](PLATFORM_BASELINE.json) 是唯一默认版本记录，保存当前已核对的 ModSDK、对应引擎与格式；后续跟进已确认的新正式版。

首次初始化、开始新组件、维护模板和交付前检查：

```text
python -B dev_tools/sync_netease_docs_from_web.py --check-updates
```

结果分别报告正式导航、本地文档版本、模板基线和官方离线文件的实际地址/元数据。`NEW_FORMAL_VERSION_REQUIRES_SYNC` 要求核对新正式更新说明及对应开发包，随后同步默认基线、正文、受影响规则、工具兼容约定和校验器；维护公开核心后同步哈希清单再导出。未知状态需继续查证，不能写成“无更新”；相同元数据也不证明正文未变。

官方正式正文或正式离线文件更新后，按来源刷新文本：

```text
python -B dev_tools/sync_netease_docs_from_web.py --fetch
python -B dev_tools/sync_netease_docs_from_web.py --source "已取得的正式文本目录或ZIP"
```

显式官网刷新不采用旧的 `NETEASE_DOCS_SOURCE`。本地来源与官网刷新分别选择；明确较旧的正式来源不能覆盖现有高版本正文。更新保留未被新来源提供的页面与替换前备份；这种保留不证明所有页面都已适配新版本，关键 API 仍须实际核对。

beta 不覆盖正式目标；既有组件按兼容声明单独迁移并更新 Manifest/依赖、catalog、说明与测试资料。模板默认目标和文档更新不等于已有组件已迁移或新版本游戏通过。正文仅作本机参考，需要账号/协议时走官方流程。

## 公开前

`mcdocs/`、`mcguide/`、`mconline/`、`LOCAL_MANIFEST.json` 均属于本地资料并已被 Git 忽略。手工打分享 ZIP 时同样排除这些内容；普通压缩工具不会自动读取 `.gitignore`。

连接超时和少量服务端临时错误最多重试三次；登录/拒绝/限流不重试。初始化失败后可重跑，六小时内按 URL 与哈希复用未完成批次的正文缓存；显式 `--fetch` / `--refresh-docs` 会重新请求正文。缓存仍是本机中间文件，不代表文档库已经更新。
