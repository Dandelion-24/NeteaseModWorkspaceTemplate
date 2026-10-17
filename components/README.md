# 组件目录

`catalog.json` 是工作区的组件总目录，只登记已经存在的组件。顶层 `workspace` 可在正式使用时改成自己的名称；保留模板名不影响初始化。设计阶段的条目允许存在，但要满足下面的状态口径。

完整的开发流程见 `AGENTS.md` 的"新增组件流程"七步；本节只写登记相关的动作。

## 目录约定

```text
components/
├── catalog.json
├── <type>/
│   ├── AGENTS.md                 类型层规则（按需创建）
│   └── <component-id>/
│       └── COMPONENT.md          组件边界、入口、数据范围、验证资料
```

- `<type>` 是组件类型，例如一键生成、收纳管理、自动化生产。不要在还没开工时铺一堆空分类。
- `<component-id>` 与 catalog 里的 `component_id` 一致，建议使用小写英文字母、数字与下划线；目录可沿用同一 ID，Python 包名不能包含连字符。不要把资源标识符、Python 包名与玩家可见名称混为一谈。
- 类型专属的维护技能放 `.agents/skills/<type>/`，不要塞进 `core`。

## catalog 字段

| 字段 | 必填 | 说明 |
| --- | --- | --- |
| `component_id` | 是 | 唯一标识，事件前缀、日志前缀、ExtraData 根键都由它派生 |
| `component_type` | 是 | 与 `components/<type>/` 目录同名 |
| `display_name` | 是 | 面向玩家的名称 |
| `version` | 是（`design` 记 `null`） | 当前版本 |
| `status` | 是 | `design` / `in_development` / `runtime_tested` |
| `runtime_project` | 是（`design` 记 `null`） | 当前运行工程路径 |
| `last_runtime_tested_version` | `runtime_tested` 必填 | 最近一次有运行证据的版本 |
| `runtime_evidence` | `in_development` / `runtime_tested` | 证据类型、日期、覆盖范围、记录路径 |
| `runtime_scope` | `in_development` | 已经落地到开发顺序的哪一步 |
| `publication_evidence` | 否 | 投稿、审核、上架状态，与运行状态分开 |
| `component_document` | 是 | `COMPONENT.md` 路径 |
| `source_assets` | 否 | 资产路径列表，使用工作区相对路径 |
| `skills` | 否 | 适用技能的 `SKILL.md` 路径列表 |
| `deliverables` | 否 | 交付包路径列表 |
| `design_documents` | `design` 必填 | 设计文档路径列表 |

## 三种状态

- **`design`**：只有设计基线，没有运行工程。可以核对文档一致性，不能写"已实现"。
- **`in_development`**：已有正式工程，静态检查或宿主仿真有结论，游戏内零证据或只覆盖部分用例。必须写明进展与证据，局部结果按用例记录，不得声称整体验收通过。
- **`runtime_tested`**：有真实运行证据。整体口头确认可以登记，但要写明确认来源与未提供的逐项证据，不自动勾选手测清单。

## 新增一个组件

1. 定 `component_id` 与类型，建 `components/<type>/<component-id>/COMPONENT.md`。
2. 设计阶段先在 `catalog.json` 登记，`status: design`，`version` 与 `runtime_project` 记 `null`，设计文档写进 `design_documents`。
3. 定稿开工时在 `mcstudio_project/` 下建当前版本的工程目录，再把 `status` 改为 `in_development` 并补 `runtime_project`。
4. 需要类型规则时创建 `components/<type>/AGENTS.md`；需要类型技能时创建 `.agents/skills/<type>/`。
5. 跑一次体检，确认现有 catalog 指针可达；字段类型、唯一 ID、状态口径与完整 schema 仍需组件校验器核对，工作区审计不覆盖全部登记规则。
