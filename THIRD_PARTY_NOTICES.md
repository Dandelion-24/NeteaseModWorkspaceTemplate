# 外部资源与许可边界

公开模板包含原创规则、维护脚本、配置与来源元数据，不分发官方正文、第三方源码、程序或上游图片。根 MIT 只覆盖模板原创部分。

| 本机可准备的资源 | 固定来源与许可 |
| --- | --- |
| Blockbench | `resources.json` 固定 5.2.1；GPL-3.0，安装时一并取得许可文本 |
| Tracy MCP | 固定提交，上游 MIT；所含原生 CLI 另按 BSD-3-Clause，准备脚本补齐相应许可文本 |
| 两个 Blockbench 插件 | 分别固定提交，Apache-2.0 |
| PixelArtConverter | 固定提交，MIT；本模板只随附原创调用适配器 |
| ModPC MCP | 固定提交，按上游明确安装步骤自动获取到本机；未核实明确开放源码/再分发许可，不随模板分发 |
| 网易官方文档 | 分享版仅保留索引与原创获取脚本；初始化保存公开官网正文供本机参考，不下载配图，不宣称整库再分发权利 |

工具逐项 URL、哈希、许可链接和自动获取状态统一见 `dev_tools/manifests/resources.json`；文档 URL 见 `docs/SOURCES.json`。本地取得的内容适用其原有条款，下载或导入不会增加权利，也不代表原作者背书。

官方入口、离线包版本核验与 ModPC 开发包/桥接区别见 [OFFICIAL_SETUP.md](dev_tools/OFFICIAL_SETUP.md)。访问受限或需要协议/登录时由使用者走官方流程。
