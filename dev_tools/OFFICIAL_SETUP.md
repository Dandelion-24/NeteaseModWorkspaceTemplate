# 官方来源、使用范围与接入

## 获取范围

初始化从上游向使用者的电脑获取资源，保留许可与来源，不将下载内容放回 Git 或分享 ZIP。本机查阅、按作者说明安装与再分发分别判断；根 MIT 仅覆盖模板原创内容。遇到登录、协议、验证码、拒绝或限流时说明缺口，不绕过限制、不代替用户同意协议。

## 网易文档

[开发者官网](https://mc.163.com/dev/)及[文档概述](https://mc.163.com/dev/mcmanual/mc-dev/mcdocs/0-%E6%A6%82%E8%BF%B0/0-%E6%A6%82%E8%BF%B0.html)提供在线正文和离线课程入口。下载按钮的[官方地址页](https://mc.163.com/developer_cn/secondary/apidocs/20211011/36201_977711.html)、文件观测信息见 `../docs/SOURCES.json`。

默认取得当前正式导航的正文，保留表格、代码和原文链接，不请求图片资源、不保存内嵌图像、视频或附件。遵守 robots.txt，限定 HTTPS 官网来源，最多三个并发且请求启动间隔至少 0.35 秒，不使用登录 Cookie。全部暂存通过后才更新文档库，错误时保留原库。

旧离线文件不能作为当前 API 的依据；更新时核对文件的实际版本和正式更新说明。当前平台版本见 `../docs/PLATFORM_BASELINE.json`，新正式版的同步规则见[文档与版本更新](../docs/README.md#正式文档与平台版本更新)。导航遗漏和依赖配图的步骤需回官网补查，正文存在不表示接口合同已经核对。

## ModPC

- **游戏开发包**：从官网[开发工作台入口](https://adl.netease.com/d/g/mc/c/dev)安装 MCStudio，完成登录/协议并选择匹配的正式版本；已安装环境可复用。[官方 ModPC 介绍](https://mc.163.com/dev/mcmanual/mc-dev/mcguide/30-%E6%B5%8B%E8%AF%95/00-ModPC%E5%BC%80%E5%8F%91%E5%8C%85%E4%BB%8B%E7%BB%8D.html)说明通过编辑器运行、开发测试或工具箱打开开发包。
- **AI 桥接**：按上游 [ModPC-MCP-Tool 安装说明](https://github.com/MCNeteaseDevs/ModPC-MCP-Tool)取得固定提交并校验，仅作本机使用。上游未附明确开放源码许可证，不能宣称它适用模板 MIT 或允许随模板再分发。
- **连接**：进入测试存档后，开发包提供 `127.0.0.1:14520`。启动 `start_modpc_mcp.ps1`，在 AI 客户端连接本机 `http://127.0.0.1:3002/mcp/`。调用游戏操作前先读取 `get_doc`，操作范围以当前任务授权为准。

桥接文件和服务枚举不证明游戏端已运行或实际操作成功。

## 建模、性能与图片转换

固定来源、许可和哈希见 `manifests/resources.json`。

- Blockbench：官方便携程序与 GPL 文本保存到 `external/Blockbench/`，启动器使用独立配置。
- 两个建模插件：下载源码和许可后，在 Blockbench“从文件加载”对应 `.js`；核对界面、格式和实际导出结果。
- Tracy：取得 MCP、原生采样/导出 CLI 及许可。函数采样需游戏协议兼容；FPS/jank 分支另需 MCDK。
- 像素转换：取得 PixelArtConverter 核心与依赖，处理已有授权图片，结果仍需审阅。

## 错误处理

连接超时及少量服务端临时错误最多重试三次，登录/拒绝/限流不重试。初始化可重跑，六小时内按 URL 与哈希复用未完成批次缓存；显式刷新会重新请求正文。缓存不表示文档库已经更新。资源、依赖、服务、客户端、GUI 和游戏状态分别查看本机 `local_state/FIRST_USE_REPORT.json`。
