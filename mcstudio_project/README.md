# mcstudio_project

每个版本使用独立工程目录，catalog 指向当前版本，目录名带版本：`<ProjectName>_v<major>.<minor>.<patch>/`。

## 工程结构

```text
<ProjectName>_v<version>/
├── behavior_packs/<BP>/
├── resource_packs/<RP>/
├── tools/                 打包、静态校验、回归脚本
├── validation/            运行证据、接口核对、发布状态
├── deliverables/          两种 ZIP
├── README.md              版本、目标档位、入口、交付物
├── MANUAL_TESTS.md        人工测试清单
└── ISSUE_HISTORY.md       已关闭问题与修复边界
```

组件级文档 `COMPONENT.md` 放在 `components/<type>/<component>/`，不在工程根目录下。工程里的 `README.md` 只写这个版本自己的信息。

## 版本策略

- 升版时从当前工程复制出新目录，不就地覆盖。旧版按明确的保留策略维护，未经授权不删除。
- 清理旧工程前保存必要的结论、证据和回归源，检查现行工具是否依赖它，再更新当前指针。
- 已删除的工程路径不得继续出现在 catalog、README、技能或交接文档里；引用历史时注明"当时路径"。
- 同一世界不要同时启用同一组件的两个版本；不同测试世界应记录各自的构建与包版本。

## 工程内必备文档

| 文件 | 内容 |
| --- | --- |
| `README.md` | 当前版本、目标 ModSDK 与 Bedrock 档位、入口、交付物清单、版本沿革表 |
| `MANUAL_TESTS.md` | 只能人工判断的项：观感、对齐、触控、跨端 |
| `ISSUE_HISTORY.md` | 每个已关闭问题的证据、根因、修复边界 |
| `validation/runtime_record.md` | 运行证据：日期、构建号、覆盖范围、结论 |
| `validation/PUBLICATION_STATUS.json` | 投稿 / 审核 / 上架状态，与运行状态分开 |

## 交付包

统一放 `deliverables/`，文件名带版本：

- `..._MCStudio.zip`：根为 `behavior_packs/` + `resource_packs/`
- `..._Addon.zip`：根直接是两个附加包目录

打包脚本要校验 CRC、重复条目、字节一致性与缓存文件排除。见 `AGENTS.md` 的交付要求。
