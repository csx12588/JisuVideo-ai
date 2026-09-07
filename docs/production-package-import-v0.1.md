# 短剧生产包导入契约 v0.1

> 状态：阶段 1 最小契约（Issue #95）
> 适用主线：外部处理 → Markdown 生产包导入 → 项目圣经 → 全局资产 → 短剧生产
> 本版目标：冻结“已分集 Markdown 生产包”的解析预览与确认写入边界，不包含运行时实现。

## 1. 范围与非目标

本契约定义外部工具已经完成去噪、校对、初步分集并经过人工确认后的 Markdown 生产包。平台负责读取、校验、预览、让用户确认，再把确认结果写入一个新项目。

本版明确不做：

- 平台内再次去噪、改写、润色、自动分集或调用任何 AI/付费模型；
- 解析阶段创建项目、剧集、人物、场景、版本或任何其他正式数据；
- 通过名称相似度静默合并已有项目/资产；
- ZIP/JSON 导入、增量导入、已有项目合并和导出；这些属于后续版本；
- 复用 #74/#75 的“AI 整理原文”入口、任务状态机或质量门。

解析必须是只读、确定性的。同一组规范化文件必须得到相同的 `package_fingerprint`、诊断结果和 DTO（时间戳、数据库 ID 等运行时字段除外）。

## 2. 输入来源关系与本版实现范围

产品保留四类内容来源，但只有最后一类进入本版解析器：

| `source_kind` | 用户意图 | v0.1 行为 |
|---|---|---|
| `short_text` | 短文本创作 | 只定义入口关系，不走本契约解析器 |
| `prepared_long_form` | 外部已整理长文 | 只定义入口关系；后续可增加单文件导入 |
| `episodic_content` | 外部已分集正文 | 只定义入口关系；本版通过生产包表达 |
| `markdown_episode_package` | 已分集 Markdown 短剧生产包 | **本版唯一实现目标** |

本版确认目标固定为新建项目。解析可以返回 `target_mode=existing_project` 的阻断诊断，但不得对已有项目执行写入或自动匹配。

## 3. 包布局与规范化

### 3.1 最小布局

目录名不参与语义，包根目录下的相对路径大小写敏感，必须使用 `/`：

```text
<package-root>/
├── drama-package.md       # 必填：项目元信息与全剧项目圣经摘要
├── characters.md          # 可选：人物圣经；没有人物时可省略
├── scenes.md              # 可选：场景圣经；没有场景时可省略
├── episodes/              # 必填：至少一个已确认分集正文
│   ├── 001.md
│   └── 002.md
└── source-manifest.md     # 必填：来源、处理、人工确认和内容指纹
```

`episodes/` 下的文件名必须匹配 `^[0-9]{3}\.md$`，从 `001.md` 连续编号，不允许跳号或重复集号。示例见 [`examples/production-package-v0.1/`](examples/production-package-v0.1/)。

### 3.2 文件编码与指纹

- 文件必须是 UTF-8；不接受 UTF-16、二进制文件或 BOM。
- 换行在计算指纹前统一为 LF；文件末尾统一保留一个换行。
- 相对路径采用 POSIX 形式并按字典序排序。
- `file_hash = SHA-256(规范化后的文件 UTF-8 字节)`。
- `package_fingerprint = SHA-256(逐行拼接除 `source-manifest.md` 外的 `path + NUL + file_hash + LF` 的 UTF-8 字节)`；排除 manifest 是为了避免 manifest 内声明的 fingerprint 与自身形成循环依赖。
- `source-manifest.md` 仍然必须单独生成 `file_hash` 并纳入预览文件清单；确认时会逐文件校验所有 hash，因此修改 manifest 仍会触发 `PACKAGE_HASH_MISMATCH`。
- 解析结果必须返回每个文件的 `path`、`file_hash`、`byte_length`；不得把本地绝对路径或密钥放入 DTO。

### 3.3 Markdown 元数据规则

机器字段使用文件首部 YAML front matter；正文使用 Markdown 标题和段落。所有日期使用 ISO-8601，所有 ID 使用 ASCII 字符。未识别的 front matter 字段保留在 `extensions` 并产生 warning，不得静默映射到数据库字段。

#### `drama-package.md`

必填字段：

| 字段 | 类型 | 约束 |
|---|---|---|
| `schema` | string | 固定为 `jisu-production-package` |
| `schema_version` | string | 固定为 `0.1` |
| `package_id` | string | `^[a-z0-9][a-z0-9._-]{2,63}$`，包的稳定外部 ID |
| `package_version` | integer | 从 1 开始递增 |
| `title` | string | 非空，1–200 字符 |
| `target_episode_count` | integer | 大于 0，必须等于实际 `episodes/*.md` 数量 |

可选字段：`genre`、`style`、`aspect_ratio`、`logline`、`audience`、`language`。正文至少包含 `## Drama Bible`，用于保存全剧大纲、世界观、主线冲突、结局承诺和跨集关系；正文是项目圣经候选内容，不是可执行提示词。

#### `characters.md`

每个角色使用一个 `## character: <external_id>` 区块。`external_id` 在包内唯一；`name` 必填，`role`、`description`、`appearance`、`personality`、`styling` 可选。不得包含 `image_url`、本地绝对路径或待执行的生成指令。

#### `scenes.md`

每个场景使用一个 `## scene: <external_id>` 区块。`external_id` 在包内唯一；`location` 和 `time` 必填，`prompt`、`lighting`、`description` 可选。场景是全剧基准设定，不携带单集数据库 ID。

#### `episodes/NNN.md`

首部字段：

| 字段 | 类型 | 约束 |
|---|---|---|
| `schema_version` | string | 固定为 `0.1` |
| `episode_id` | string | 包内稳定 ID，推荐 `E001` 格式，唯一 |
| `episode_number` | integer | 必须与文件名数字一致 |
| `title` | string | 非空 |
| `status` | enum | 本版必须为 `confirmed` |

正文必须包含 `## Content` 且非空。`## Objective`、`## Hook`、`## Previous Bridge`、`## Next Bridge`、`## Character Refs`、`## Scene Refs` 为可选区块；引用必须使用 `characters.md`/`scenes.md` 中已声明的 `external_id`。`Content` 原文按字节保留，不得在导入时改写、去空白、自动分段或重新编号。

#### `source-manifest.md`

必填字段：`schema_version=0.1`、`source_id`、`source_kind`、`processed_at`、`processor`、`human_reviewed=true`、`package_fingerprint`。`source_kind` 必须是 `external_prepared` 或 `external_episodic`；`processor` 只记录工具名称和版本，不记录密钥。

可选字段：`original_name`、`original_uri`、`original_content_hash`、`processing_steps`、`reviewer_note`。`original_uri` 可以是脱敏后的普通 URL，不得要求平台访问它，也不得把它作为导入成功的前置条件。

## 4. 解析预览 DTO（只读）

解析接口的具体 HTTP 路径留给后续公共契约 PR；本节冻结返回语义和字段名。所有数组按文件/集号/外部 ID 的确定性顺序排序。

```json
{
  "contract_version": "0.1",
  "source_kind": "markdown_episode_package",
  "target_mode": "new_project",
  "status": "ready",
  "can_confirm": true,
  "package": {
    "package_id": "demo-night-market",
    "package_version": 1,
    "package_fingerprint": "sha256:...",
    "files": [
      { "path": "drama-package.md", "file_hash": "sha256:...", "byte_length": 1234 }
    ]
  },
  "project": {
    "title": "夜市回声",
    "genre": "悬疑",
    "style": "2d-cinematic",
    "aspect_ratio": "9:16",
    "target_episode_count": 2,
    "bible_summary": "..."
  },
  "characters": [
    { "external_id": "C001", "name": "林夏", "role": "protagonist", "episode_refs": ["E001"] }
  ],
  "scenes": [
    { "external_id": "S001", "location": "旧城夜市", "time": "night", "episode_refs": ["E001"] }
  ],
  "episodes": [
    {
      "external_id": "E001",
      "episode_number": 1,
      "title": "灯灭之前",
      "status": "confirmed",
      "content_char_count": 318,
      "content_hash": "sha256:...",
      "character_refs": ["C001"],
      "scene_refs": ["S001"]
    }
  ],
  "source": {
    "source_id": "night-market-source-20260907",
    "human_reviewed": true,
    "processor": "CodeBuddy 1.x"
  },
  "diagnostics": {
    "missing": [],
    "conflicts": [],
    "warnings": []
  },
  "write_plan": {
    "writes_on_parse": [],
    "writes_after_confirm": ["drama", "source_version", "episodes", "characters", "scenes", "episode_links"]
  }
}
```

解析阶段禁止返回数据库自增 ID 作为外部引用的替代品；预览中的实体只能用 `package_id`、`episode_id`、`external_id` 和内容指纹互相引用。`status` 取 `ready` 或 `blocked`；存在任意 error 级诊断时必须为 `blocked` 且 `can_confirm=false`。

## 5. 确认写入边界、幂等和冲突

### 5.1 两个阶段

1. **Parse / Preview**：读取上传内容、规范化、校验和生成 DTO。不得写项目、版本、剧集、人物、场景，不得调用模型。
2. **Confirm / Commit**：用户明确确认预览结果后才写入。所有业务写入必须在一个可回滚的事务中完成；失败时不得留下半个项目、孤儿剧集或孤儿资产。

确认请求至少携带 `package_fingerprint`、`target_mode=new_project` 和 `confirm_idempotency_key`。提交时必须再次校验指纹，不能信任客户端只传的预览结果。

### 5.2 幂等键

- `confirm_idempotency_key` 是调用方生成的稳定不透明字符串，长度 16–128 个 ASCII 字符。
- 相同 `confirm_idempotency_key + package_fingerprint` 重复确认必须返回第一次确认的同一结果，不得创建第二个项目。
- 同一 key 绑定不同 `package_fingerprint` 必须阻断并返回 `IDEMPOTENCY_KEY_REUSED`。
- 不同 key 可以有意创建另一个新项目；平台不得仅凭 `package_id` 静默复用旧项目。
- 后续实现必须把 key 与目标 `drama_id`、package fingerprint 和确认结果绑定；不能把“同包”误当成“同一次确认”。

### 5.3 v0.1 新项目写入顺序

确认通过后，建议按以下顺序在同一事务中写入现有表；本 Issue 不授权新增表或迁移：

1. `dramas`：写入 `title`、`genre`、`style`、`aspect_ratio`、`total_episodes`、`description`。`metadata` 可保存脱敏的 package/source 摘要、版本和指纹。
2. `source_versions`：写入一条 `base_kind=source` 的不可变版本，`content` 使用**按集号拼接的已确认正文**（集间使用两个 LF）；`content_hash/base_hash` 使用该内容 hash，`stats` 标记 `origin=production_package` 和 package fingerprint。若未来包提供独立 `source.md`，才可用其内容替代拼接正文。
3. `episodes`：按 `episode_number` 写入 `title`、`content`、`status=draft`；不写 `script_content`、视频 URL 或生成任务。
4. `characters`、`scenes`：只写 Markdown 中的文本字段，生成新的数据库 ID；不导入图片、不调用提取 Agent。再用 `episode_characters`、`episode_scenes` 建立关系。
5. 将 `dramas.current_source_version_id` 指向本次新建 source 版本，并保存确认结果/版本来源摘要。

`dramas.description` 是旧链路兼容落点：v0.1 对已分集包使用与 `source_versions.content` 相同的按集拼接正文，不能写成大纲摘要，也不能覆盖包中任何单集正文。后续 UI 若展示来源，必须标注该正文是 `package-derived`，原始外部来源以 `source-manifest.md` 和指纹为准。

### 5.4 冲突和人工选择

- v0.1 只支持新建项目，因此不会自动合并已有角色/场景。
- 包内重复 `external_id`、同集号不同正文、未知角色/场景引用、目标集数与文件数不一致，均为阻断冲突。
- 后续已有项目导入必须先展示 name/ID/内容差异，由用户逐项选择“复用、创建副本或跳过”；禁止按名称相似度静默更新。
- 解析预览显示的缺失项和冲突项必须保留 `path`、`field`、`code`、`message`，以便前端定位到具体文件和区块。

## 6. 兼容映射

| 生产包字段 | 现有数据落点 | v0.1 规则 |
|---|---|---|
| `drama-package.md` 元信息 | `dramas.title/genre/style/aspect_ratio/total_episodes` | 仅确认后写入；未知扩展保存在来源摘要，不擅自新增列 |
| `drama-package.md` Drama Bible | `dramas.metadata` 的 package 摘要；后续项目圣经字段 | 不写入 `description`；不得当作原文正文 |
| `episodes/*.md` Content | `episodes.content` | 原文保留；按集号唯一；不自动重写 |
| `source-manifest.md` 与指纹 | `source_versions.stats` + `dramas.metadata` 来源摘要 | 记录工具、版本、人工确认和 hash；不访问原始 URL |
| 按集拼接正文 | `dramas.description`、`source_versions.content` | 仅作为旧项目/旧接口兼容正文，标记 `package-derived` |
| `characters.md` | `characters` + `episode_characters` | 只创建文本实体和显式引用关系 |
| `scenes.md` | `scenes` + `episode_scenes` | 只创建文本实体和显式引用关系 |
| 外部 `episode_id/character_id/scene_id` | DTO 内部引用映射 | 不直接写入数据库 ID；确认时生成 mapping 并可追溯 |

以下现有字段不由 v0.1 包填充：`script_content`、`video_url`、`thumbnail`、`image_url`、`final_prompt`、生成任务及供应商配置。

## 7. 错误码与前端语义

| code | 阶段 | 等级 | 前端行为 |
|---|---|---|---|
| `PACKAGE_EMPTY` | parse | error | 提示上传包，不显示确认按钮 |
| `PACKAGE_SCHEMA_UNSUPPORTED` | parse | error | 显示支持的 `0.1` 版本，要求外部工具重新导出 |
| `PACKAGE_FILE_MISSING` | parse | error | 定位缺失路径；阻止确认 |
| `PACKAGE_FILE_UNEXPECTED` | parse | warning/error | 未知文件先 warning；二进制、越界或路径穿越为 error |
| `PACKAGE_ENCODING_INVALID` | parse | error | 提示转换为 UTF-8/Markdown |
| `PACKAGE_MANIFEST_INVALID` | parse | error | 定位 manifest 字段并阻止确认 |
| `PACKAGE_FRONTMATTER_INVALID` | parse | error | 定位文件和字段；阻止确认 |
| `PACKAGE_DUPLICATE_ID` | parse | error | 展示重复的 external ID 和路径 |
| `PACKAGE_EPISODE_INVALID` | parse | error | 展示文件名、集号或状态错误 |
| `PACKAGE_REFERENCE_UNKNOWN` | parse | error | 展示缺失的角色/场景 external ID |
| `PACKAGE_HASH_MISMATCH` | parse/confirm | error | 提示包在预览后发生变化，要求重新解析 |
| `PACKAGE_TARGET_UNSUPPORTED` | parse/confirm | error | v0.1 只允许新建项目 |
| `IDEMPOTENCY_KEY_REUSED` | confirm | error | 提示确认 key 已绑定另一个包 |
| `PACKAGE_CONFLICT` | confirm | error | 展示冲突详情，要求用户重新确认 |
| `PACKAGE_WRITE_FAILED` | confirm | error | 展示可重试错误；事务必须回滚且不得自动重试写入 |

所有错误都应包含 `code`、`severity`、`path`（若适用）、`field`（若适用）和面向用户的 `message`。解析失败不得返回 200/ready，也不得以 warning 伪装阻断错误。

## 8. 测试矩阵

| 场景 | 输入/操作 | 预期 |
|---|---|---|
| T01 合法最小包 | 使用 `examples/production-package-v0.1` 解析 | `ready=true`，两集、人物/场景引用完整，无写库 |
| T02 可选文件缺失 | 删除 `characters.md` 或 `scenes.md` | 仍可解析；对应数组为空，不产生 error |
| T03 缺必填文件 | 删除 `drama-package.md`/`source-manifest.md`/`episodes/001.md` | `PACKAGE_FILE_MISSING`，`can_confirm=false` |
| T04 集号错误 | 将 `episodes/001.md` 改名为 `002.md` 或跳号 | `PACKAGE_EPISODE_INVALID` |
| T05 重复实体 | 添加重复的 `C001` 或 `S001` 区块 | `PACKAGE_DUPLICATE_ID` |
| T06 未知引用 | episode 引用不存在的角色/场景 ID | `PACKAGE_REFERENCE_UNKNOWN` |
| T07 内容变化 | 预览后修改任一文件再确认 | `PACKAGE_HASH_MISMATCH`，不写库 |
| T08 重复确认 | 相同 key 和 fingerprint 确认两次 | 返回同一结果，不新增项目 |
| T09 key 复用 | 相同 key 换另一 fingerprint 确认 | `IDEMPOTENCY_KEY_REUSED` |
| T10 解析只读 | 在 parse 期间检查 drama/source/episode/asset 表 | 行数和内容均不改变 |
| T11 事务回滚 | 确认写入中途注入失败 | 无半成品项目/剧集/资产；返回 `PACKAGE_WRITE_FAILED` |
| T12 禁止副作用 | 解析合法包并观察模型/任务调用 | 不调用 AI、供应商、生成任务或旧 clean 入口 |

实现 PR 必须把 T01–T12 映射到自动测试或可复现的验收脚本；本契约 PR 只冻结矩阵，不添加运行时代码。

## 9. 版本与后续扩展

- `0.x` 版本允许增加可选字段，但不得改变已有字段含义；未知可选字段只能进入 `extensions` + warning。
- 需要改变必填字段、指纹算法、写入边界或外部 ID 语义时，必须升级契约版本并提供迁移说明。
- ZIP/JSON、已有项目合并、全局资产版本、项目圣经独立表和导出能力另开契约/Issue；不得在实现 PR 中隐式扩大 v0.1 范围。
