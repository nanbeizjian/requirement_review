## Purpose

定义审核人员从本地目录批量提交 Markdown 需求、查看 AI 评审点、逐条完成人工审核并最终确认文档的前端行为；所有服务端交互依赖仓库根 `public-contracts` 及其同名 change。

## ADDED Requirements

### Requirement: Select a requirement directory

前端 SHALL 允许审核人员选择本地目录，并 SHALL 仅将 `.md` 或 `.markdown` 文件纳入待评审列表。提交前 SHALL 显示文件名、相对路径、大小及状态，且 SHALL NOT 将绝对本地路径发送到服务端。

#### Scenario: Directory contains mixed files

- **WHEN** 审核人员选择同时包含 Markdown 和其他文件的目录
- **THEN** 前端仅将 Markdown 文件列为可提交文件
- **AND** 显示被忽略文件的数量

#### Scenario: Directory selection is unsupported

- **WHEN** 浏览器不支持目录选择
- **THEN** 前端提供多文件选择回退入口
- **AND** 应用相同的 Markdown 过滤规则

### Requirement: Start one review per document

前端 SHALL 为每个有效 Markdown 文件创建独立评审任务，并 SHALL 按根公共契约携带项目身份、数据策略、正文和安全的文档显示名称。单个文件失败 MUST NOT 阻止其他文件继续。

#### Scenario: Submit several documents

- **WHEN** 审核人员提交三份有效 Markdown 文件
- **THEN** 前端创建三个独立评审任务
- **AND** 分别显示每个文件的提交与评审状态

#### Scenario: One document fails

- **WHEN** 一个文件读取、提交或评审失败
- **THEN** 其他文件继续处理
- **AND** 失败文件显示安全错误及单独重试操作

### Requirement: Present each AI finding as a review record

前端 SHALL 将每个 AI finding 呈现为独立评审记录，并 SHALL 显示来源文档、需求定位、维度、严重程度、问题、影响、建议、置信度、证据及最新人工决策。

#### Scenario: One document has multiple findings

- **WHEN** 一份文档产生多个 findings
- **THEN** 前端为每个 finding 显示一条可独立审核的记录
- **AND** 每条记录保留到原始文档位置和引用文本的关联

#### Scenario: Restore server state

- **WHEN** 审核人员刷新页面或重新打开工作台
- **THEN** 前端从服务端重新加载项目评审、findings 和最新决策
- **AND** 已完成的人工决策保持可见

### Requirement: Decide findings independently

reviewer 或 admin SHALL 能对单条记录执行 `accept`、`reject` 或 `re-review` 并填写意见。前端 SHALL 防止重复提交，并 SHALL 在服务端确认后刷新记录状态。

#### Scenario: Reviewer accepts a finding

- **WHEN** reviewer 接受一条记录并提交意见
- **THEN** 前端按根公共契约提交具有唯一幂等键的决策
- **AND** 成功后显示接受状态和意见

#### Scenario: Viewer opens the workbench

- **WHEN** viewer 查看评审记录
- **THEN** 前端允许读取记录和决策状态
- **AND** 不提供变更决策或最终确认操作

### Requirement: Finalize a reviewed document

只有所有 findings 均存在当前决策且不存在 `re-review` 时，前端 SHALL 启用整份文档最终确认。确认成功后 SHALL 提供最终报告入口；无 findings 的成功评审 SHALL 允许确认。

#### Scenario: Findings remain undecided

- **WHEN** 文档仍有未决 finding
- **THEN** 最终确认保持禁用
- **AND** 页面显示剩余待审核数量

#### Scenario: All findings are resolved

- **WHEN** 所有 findings 已接受或拒绝
- **THEN** reviewer 或 admin 可以确认整份文档
- **AND** 成功后可以查看最终报告

### Requirement: Communicate progress and errors

前端 SHALL 区分文件读取、提交、AI 评审、等待人工审核、完成和失败状态，并 SHALL 按根公共错误契约显示安全信息。轮询 SHALL 在终态、离开页面或达到退避停止条件时结束。

#### Scenario: Review is running

- **WHEN** 服务端返回非终态评审状态
- **THEN** 前端使用有上限的退避间隔继续查询
- **AND** 页面保持可用并显示当前状态

#### Scenario: API returns a compatible error

- **WHEN** API 返回公开错误码、安全消息和关联标识
- **THEN** 前端显示安全消息和关联标识
- **AND** 保留适用的重试上下文

### Requirement: Provide accessible review controls

工作台 SHALL 使用语义化控件、可见标签、键盘可操作焦点顺序和不依赖颜色的状态文本。异步状态变化 SHALL 以辅助技术可感知的方式呈现。

#### Scenario: Keyboard-only review

- **WHEN** 审核人员仅使用键盘浏览并处理记录
- **THEN** 其可以选择文件、定位记录、填写意见并提交允许的操作
- **AND** 焦点不会丢失到不可见元素

#### Scenario: Status changes asynchronously

- **WHEN** 文件或评审状态在后台更新
- **THEN** 页面显示文字状态
- **AND** 关键完成或失败变化可由辅助技术感知
