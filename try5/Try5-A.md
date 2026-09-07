# RobotCAD Try-5A
# URDF-Guided Top-Down Coarse Robot Reconstruction
# Interface-First Link-Wise Modeling + Assembly/Kinematic Verification

请启动 RobotCAD Try-5A 开发实验。

Try-4 系列已停止继续做补丁式修复。
Try-5A 是新的架构验证实验。

--------------------------------------------------
0. Try-5A 的核心目标
--------------------------------------------------

Try-5A 不追求高保真机械细节。

本轮只回答：

> 利用输入 URDF 作为运动学骨架，
> 是否可以先从整机顶层规划机械臂，
> 再按 URDF Link 分别进行 interface-first 粗建模，
> 最后重新装配成一台结构连通、接口合理、运动学一致的机械臂？

核心原则：

Mechanical correctness first,
geometric fidelity second.

本轮优先保证：

- link 不悬空；
- joint/interface 对齐；
- URDF kinematic chain 正确；
- link 大结构和整体比例合理；
- 能执行 FK / joint sweep；
- 可装配、可重开、可验证。

本轮不要求：

- 高保真曲面；
- 完整孔槽；
- 复杂 gripper internal details；
- cosmetic details；
- Try-4 的完整 Link internal graph；
- 多轮 detail repair；
- Robot B transfer。

--------------------------------------------------
1. 实验规模
--------------------------------------------------

Try-5A 开发阶段只使用：

1 台 Robot A

Robot A 应是当前已有样本中：

- link 数量适中；
- URDF 完整；
- 具有典型 revolute joints；
- 有 base / arm / wrist / end-side structure；
- 不选择最极端复杂 gripper 作为第一开发对象。

记录：

experiments/try5A/protocol/robot_A_selection.md

内容包括：

- robot_id
- DOF
- link_count
- joint_count
- geometry difficulty
- why selected

不要运行 Robot B。
不要运行 frozen transfer set。

--------------------------------------------------
2. 正式输入
--------------------------------------------------

Generator 只能使用：

1. 多视图机械臂图像
2. Engineering Text
3. Sanitized URDF

Sanitized URDF 可以包含：

- link IDs
- parent-child
- joint IDs
- joint type
- joint origin
- joint axis
- joint limits

禁止输入：

- URDF visual mesh
- collision mesh
- GT STEP
- GT B-Rep
- GT per-link mesh
- GT feature tree
- GT interface geometry
- GT CAD dimensions

GT 仅用于 evaluator。

--------------------------------------------------
3. 正式输出
--------------------------------------------------

Try-5A 输出两个层次。

A. Link-level artifacts

每个 URDF Link：

- coarse .FCStd
- .step
- .stl
- LinkCoarseSpec.json
- InterfaceRefs.json
- CAD IR
- execution log
- parameter manifest

B. Robot-level artifacts

- assembled_robot.FCStd
- assembled_robot.step
- assembled_robot.stl
- robot_assembly_plan.json
- joint_interface_graph.json
- link_mapping.json
- kinematic_validation.json
- interface_validation.json
- assembly_validation.json
- simulation_validation.json

--------------------------------------------------
4. Try-5A 的核心架构
--------------------------------------------------

建立共享：

# Robot Design Blackboard

至少包含：

L0 Kinematic Skeleton
L1 Robot Assembly Plan
L2 Joint Interface Graph
L3 Link Coarse Design State
L4 Robot Assembly / Verification State

不要采用：

link1 generate
-> link2 generate
-> link3 generate
-> finally assemble

这种孤立流水线。

所有 Link 的设计都必须受：

- 全局 Robot Plan
- URDF skeleton
- shared Joint Interface Graph

约束。

--------------------------------------------------
5. L0 — Kinematic Skeleton
--------------------------------------------------

从 URDF 确定性解析：

- links
- joints
- parent-child graph
- joint type
- joint origin
- joint axis
- joint limits

计算：

- canonical pose
- world transform of every link frame
- world transform of every joint frame
- parent-child relative transforms
- FK chain

输出：

kinematic_skeleton.json

要求：

这层来自 URDF，
不允许 Agent 随意修改。

如果视觉和 URDF 冲突：

URDF 作为 kinematic authority。

视觉只影响 geometry appearance，
不改 joint topology / axis / origin。

--------------------------------------------------
6. Robot Kinematics Skill
--------------------------------------------------

建立：

skills/robot_kinematics/SKILL.md

实现/规范：

- homogeneous transform
- rotation representation
- frame composition
- relative pose
- FK
- joint-axis world transform
- canonical pose reconstruction
- joint-limit sampling
- simple workspace sampling
- optional simple IK diagnostic

这些操作应尽量确定性实现，
不要依赖 VLM 猜。

--------------------------------------------------
7. L1 — Robot Assembly Plan
--------------------------------------------------

在生成任何 Link CAD 前，
先生成整机：

robot_assembly_plan.json

每个 Link 至少记录：

- link_id
- parent_joint
- child_joint(s)
- inferred mechanical role
- coarse envelope
- principal direction
- approximate length / width / height
- proximal region
- distal region
- expected body family
- neighboring links
- critical assembly constraints

例如：

{
  "link_id": "L2",
  "role": "upper_arm_link",
  "parent_joint": "J2",
  "child_joint": "J3",
  "principal_axis": "...",
  "coarse_family": "elongated_link_body",
  "proximal_region": "rotary_housing",
  "distal_region": "fork_or_joint_housing"
}

注意：

这里只规划大结构。

不要进入：

- detailed hole pattern
- small recess
- fillet
- internal gripper mechanism

--------------------------------------------------
8. Robot Plan 必须结合 URDF + Visual Evidence
--------------------------------------------------

URDF 提供：

- topology
- joint placement
- axis
- relative length constraints implied by joint origins

视觉提供：

- link envelope
- thickness
- cross-section family
- broad housing shape
- overall morphology

不要只根据 URDF 生成圆柱/杆。

也不要只根据图像忽略 URDF frame。

--------------------------------------------------
9. L2 — Joint Interface Graph
--------------------------------------------------

这是 Try-5A 的核心。

每一个 URDF joint 必须建立一个：

# Shared Joint Interface Contract

不能让 parent Link 和 child Link
各自独立设计自己的接口。

一个 Joint Interface 属于：

joint

而不是属于单个 link。

输出：

joint_interface_graph.json

--------------------------------------------------
10. Joint Interface Contract Schema
--------------------------------------------------

每个 joint 至少：

{
  "joint_id": "J3",
  "parent_link": "L2",
  "child_link": "L3",

  "joint_type": "revolute",
  "origin": {...},
  "axis": {...},

  "interface_family": "...",

  "shared_reference_frame": {...},

  "parent_port": {...},
  "child_port": {...},

  "required_relations": [
    "coaxial",
    "connected",
    "rotation_clearance"
  ],

  "interface_envelope": {...},

  "protected_region_parent": {...},
  "protected_region_child": {...},

  "target_gap": ...,
  "clearance_rule": ...
}

--------------------------------------------------
11. Interface Family
--------------------------------------------------

Try-5A 只需要少量通用 interface family。

建议：

- coaxial_rotary_interface
- fork_pin_interface
- flange_interface
- nested_housing_interface
- planar_mount_interface
- end_tool_interface

不要扩展成很大模板库。

如果视觉证据不支持精确结构：

优先使用简单但机械合理的接口。

不要猜：

- exact bearing
- exact reducer
- exact motor
- hidden internal shaft design

--------------------------------------------------
12. Interface-first 建模原则
--------------------------------------------------

每个 Link 的建模顺序必须是：

1. proximal interface
2. distal interface
3. main body connecting interfaces
4. coarse housing / envelope

即：

Interface A
→ Body
→ Interface B

禁止：

先完整画 body
→ 最后想办法把接口贴上去。

--------------------------------------------------
13. Link Coarse Spec
--------------------------------------------------

每个 Link 建立：

LinkCoarseSpec.json

至少：

- link_id
- role
- proximal interface reference
- distal interface reference
- principal frame
- body family
- coarse dimensions
- envelope
- structural path
- protected interface geometry

允许粗 shape family：

- central_web
- straight_beam
- tapered_beam
- dual_side_plate
- coarse_shell
- rotary_housing
- fork_body
- wrist_block
- base_housing

本轮不要加入复杂 detail vocabulary。

--------------------------------------------------
14. Link Coarse CAD
--------------------------------------------------

本轮每个 Link 只需实现：

A. interfaces

B. main structural body

C. major joint housing

D. obvious large opening/fork if structurally necessary

E. basic transition

不要求：

- small holes
- decorative bosses
- minor fillets
- exact shell details
- complex surface styling
- gripper internal linkage details

--------------------------------------------------
15. CAD 建模要求
--------------------------------------------------

继续使用：

Codex CLI
+
shared Skills
+
FreeCAD backend

禁止：

每个 Link 生成完全独立的大型 case-specific Python script。

保持：

RobotCAD representation
→ CAD IR
→ FreeCAD backend

FreeCAD 要求：

- FCStd valid
- reopen
- recompute
- STEP export
- STL export
- no silent fallback

--------------------------------------------------
16. 整机组装
--------------------------------------------------

所有 coarse Link 建完后：

必须按 URDF frame 重新组装整机。

Assembly placement 以 URDF 为准。

禁止：

为了视觉上“接上”
而自由移动 Link。

如果接口不匹配：

必须修 Interface / Link geometry。

不能：

Move component until it looks connected.

--------------------------------------------------
17. Try-5A 三个实验条件
--------------------------------------------------

只做：

A0
A1
A2

--------------------------------------------------
A0 — Independent Link Baseline
--------------------------------------------------

流程：

Image + Text + URDF
→ 每个 Link 独立生成 coarse CAD
→ 按 URDF placement 装配

不使用：

- Robot Assembly Plan
- Shared Joint Interface Graph

每个 Link 只知道自身 URDF context。

作用：

验证“各 Link 各自为阵”的问题。

--------------------------------------------------
A1 — + Robot-Level Planning
--------------------------------------------------

流程：

URDF + Images
→ Robot Assembly Plan
→ Link Coarse Specs
→ each Link coarse CAD
→ URDF assembly

新增：

全局 Robot Plan

但暂时不使用 Shared Interface Contract。

作用：

验证：

顶层整机规划是否改善：

- link尺度协调
- overall structure
- link role consistency
- assembly morphology

--------------------------------------------------
A2 — + Interface-First Shared Joint Design
--------------------------------------------------

流程：

URDF
+ Images
→ Robot Assembly Plan
→ Joint Interface Graph
→ Shared Interface Contracts
→ per-Link Interface-first CAD
→ Body completion
→ Whole Robot Assembly
→ Kinematic / Interface Verification

A2 是 Try-5A 主方法。

--------------------------------------------------
18. 三组公平性
--------------------------------------------------

A0/A1/A2 必须：

- same Robot A
- same images
- same engineering text
- same sanitized URDF
- same Codex model
- same FreeCAD backend
- same evaluator
- same export settings
- same canonical pose

不要求 LLM calls 完全相同。

记录：

- calls
- tokens
- latency
- CAD operations
- build time

--------------------------------------------------
19. Coarse Assembly Gate
--------------------------------------------------

A0/A1/A2 都要统一评价。

不要用 VLM 作为主判定器。

Gate 以确定性指标为主。

--------------------------------------------------
20. Assembly Metrics
--------------------------------------------------

至少计算：

1. Connected Joint Rate

多少 parent-child joint
在生成几何中形成有效连接。

2. Floating Link Rate

是否有完全不接触任何邻接 Link 的刚体。

3. Interface Gap Error

对每个 joint 的 parent/child interface
计算真实几何 gap。

4. Interface Penetration

是否存在不合理过度穿透。

5. Adjacent Link Contact Validity

相邻 Link 是否在预期接口区域接触，
而不是别的位置意外碰撞。

6. Assembly Connected Component Count

整台机器人应形成预期刚体连接结构。

--------------------------------------------------
21. Joint / Interface Metrics
--------------------------------------------------

至少：

- Joint Axis Angular Error
- Joint Axis Offset Error
- Joint Origin / Interface Center Error
- Coaxiality Error
- Interface Orientation Error
- Gap/Clearance Satisfaction

这些指标从：

URDF frame
vs
generated CAD interface geometry

确定性计算。

--------------------------------------------------
22. Kinematic Metrics
--------------------------------------------------

使用输入 URDF 作为 authority。

对 generated link geometry：

1. canonical FK reconstruction
2. sampled joint configurations
3. end-effector pose
4. joint sweep success
5. workspace sampling
6. self-collision
7. adjacent unintended interference

至少报告：

- EE position error
- EE orientation error
- workspace overlap / coverage
- collision-free joint sample rate
- joint-limit traversal success

如果当前实现某个指标困难：

可以阶段性简化，
但不能使用 VLM 替代数值验证。

--------------------------------------------------
23. Coarse Geometry Metrics
--------------------------------------------------

粗阶段仍报告：

- per-link IoU
- per-link Chamfer
- per-link HD95
- whole robot IoU
- whole robot Chamfer
- silhouette IoU
- overall reach error
- overall bbox error

但 Try-5A 不要求 geometry 是主指标。

优先级：

Kinematics / Interface / Assembly
>
Coarse Geometry

--------------------------------------------------
24. VLM 在 Try-5A 的职责
--------------------------------------------------

VLM 可以做：

- 判断某 Link envelope 是否明显错误；
- 判断 base / upper arm / wrist role 是否合理；
- 对比 generated coarse assembly 与 reference image；
- 判断 major shape family 是否明显错误；
- 输出结构化 coarse repair suggestion。

VLM 不负责：

- 判断 joint axis 数值是否正确；
- 判断 FK 是否正确；
- 判断 gap 数值；
- 判断 penetration；
- 自由发明新的局部零件。

--------------------------------------------------
25. Structured Coarse Review
--------------------------------------------------

如果使用 VLM review，
必须输出结构化结果，例如：

{
  "level": "COARSE_STRUCTURE",
  "link_id": "L3",
  "issue": "main_body_orientation_mismatch",
  "evidence_views": ["front", "iso"],
  "recommended_action": "REPLAN_COARSE_BODY",
  "do_not_change": [
    "proximal_interface",
    "distal_interface"
  ]
}

禁止自由文本式：

“这个机械臂看起来不太对，请修改。”

--------------------------------------------------
26. Try-5A 的修复顺序
--------------------------------------------------

Try-5A 如果需要开发性 repair，
严格按：

1. KINEMATIC_FRAME
2. INTERFACE
3. COARSE_BODY
4. COARSE_APPEARANCE

禁止先修外观。

如果 Joint Frame / Interface 未通过：

不能因为 body 看起来像
就进入 PASS。

--------------------------------------------------
27. Scheduler / State
--------------------------------------------------

建议建立状态：

ROBOT_PLANNED
INTERFACES_PLANNED
LINKS_BUILT
ASSEMBLED
KINEMATIC_CHECKED
INTERFACE_CHECKED
COARSE_GEOMETRY_CHECKED

每个 Link / Joint 可有：

PASS
REPAIR
FROZEN

已经满足接口与 frame 要求的 Joint：

FROZEN

后续 coarse body 修改
不得破坏已冻结接口。

--------------------------------------------------
28. Try-5A 不做什么
--------------------------------------------------

明确禁止本轮加入：

- Try-5B Semantic Inventory
- detailed gripper decomposition
- detailed Link Internal Graph
- small feature vocabulary
- cosmetic detail
- multi-round detail repair
- full Appearance Detailing
- Robot B
- dynamics simulation
- torque/load
- FEA
- control
- grasp simulation

--------------------------------------------------
29. 仿真要求
--------------------------------------------------

如果已有仿真环境：

优先复用。

如果没有：

Try-5A 只需实现轻量：

URDF FK
+
generated geometry collision checking
+
joint sweep
+
workspace sampling

不要为了 Try-5A 搭建大型动力学仿真系统。

--------------------------------------------------
30. 可选 Robot Knowledge Base
--------------------------------------------------

允许建立小型：

knowledge/robotics/

例如：

- urdf_joint_semantics.md
- revolute_joint_interface.md
- robot_link_roles.md
- interface_design_rules.md
- kinematic_validation.md

但知识库只能提供：

- 通用机器人知识；
- 常见接口逻辑；
- 设计原则。

禁止写：

Robot A 每个 Link 的 GT 答案。

--------------------------------------------------
31. Try-5A 最关键的比较
--------------------------------------------------

A0 → A1

回答：

Robot-Level Planning
是否改善：

- link整体尺度
- link role
- morphology
- whole robot geometry

A1 → A2

回答：

Interface-First Shared Joint Design
是否改善：

- connected joint rate
- floating link rate
- interface gap
- joint axis alignment
- assembly validity
- kinematic validity

--------------------------------------------------
32. 成功标准
--------------------------------------------------

Try-5A 不要求 coarse robot 外形高保真。

如果 A2 相比 A0/A1：

- floating link 明显减少；
- connected joint rate 提高；
- interface gap 降低；
- axis/origin consistency 提高；
- FK / joint sweep 更稳定；
- workspace 更接近 reference/expected；
- overall robot morphology 不显著恶化；

则认为：

URDF-guided top-down
+
interface-first
+
link-wise coarse modeling

值得进入 Try-5B。

--------------------------------------------------
33. 失败诊断
--------------------------------------------------

如果 A2 失败：

明确区分：

A. URDF parsing / frame error
B. Robot-level planning error
C. Interface contract error
D. Interface geometry realization error
E. Link coarse body error
F. Assembly placement error
G. Kinematic evaluator error
H. FreeCAD execution error

不要把所有问题归类为：

“模型不像”。

--------------------------------------------------
34. 输出目录
--------------------------------------------------

experiments/try5A/

  protocol/
    try5A_protocol.md
    robot_A_selection.md

  inputs/
    images/
    engineering_text/
    sanitized_urdf/

  knowledge/
    robotics/

  skills/
    robot_kinematics/
    robot_assembly_planning/
    joint_interface_design/
    link_coarse_modeling/
    coarse_robot_review/

  A0/
  A1/
  A2/

  robot_plan/
  interface_graph/
  link_specs/
  link_cad/
  assemblies/
  simulation/

results/try5A/

  assembly_metrics.csv
  interface_metrics.csv
  kinematic_metrics.csv
  coarse_geometry_metrics.csv
  resource_metrics.csv

  per_joint/
  per_link/
  contact_sheets/

  try5A_report.md

--------------------------------------------------
35. 最终报告必须回答
--------------------------------------------------

1. Robot A 是哪一个样本？
2. URDF link / joint 数量是多少？
3. L0 Kinematic Skeleton 是否正确解析？
4. A0/A1/A2 各有多少 Link 成功生成？
5. 三个条件是否都能完成整机装配？
6. Connected Joint Rate 如何变化？
7. Floating Link Rate 如何变化？
8. Interface Gap 如何变化？
9. Joint Axis Error 如何变化？
10. Joint Origin / Center Error 如何变化？
11. Coaxiality 是否改善？
12. Adjacent penetration 是否改善？
13. canonical pose 是否正确？
14. sampled FK 是否稳定？
15. EE pose error 如何变化？
16. workspace 如何变化？
17. joint sweep 是否发生自碰撞？
18. A1 是否说明 Robot-Level Planning 有价值？
19. A2 是否说明 Interface-First 有价值？
20. 有没有出现：
    “单 Link 看起来合理，但整机装不上”的情况？
21. 有没有出现：
    “接口能接，但 body geometry 很差”的情况？
22. 哪些 Joint 最难设计接口？
23. 哪些 Link 最难做 coarse body？
24. FreeCAD 是否仍不是主要瓶颈？
25. 当前最大瓶颈位于：
    - robot planning
    - interface design
    - interface realization
    - coarse geometry
    - kinematic verification
26. 是否建议进入 Try-5B Semantic Link Detailing？

--------------------------------------------------
36. 执行顺序
--------------------------------------------------

严格按以下 Phase 开发。

Phase 1
选择 Robot A
+
解析 URDF
+
建立 Kinematic Skeleton

完成后先验证：
FK / frames 是否正确。

Phase 2
建立 Robot Assembly Plan

Phase 3
建立 Joint Interface Graph / Contract

Phase 4
实现 A0

Phase 5
实现 A1

Phase 6
实现 A2

Phase 7
Whole-Robot Assembly

Phase 8
Deterministic Assembly / Interface / Kinematic Evaluation

Phase 9
统一结果分析

Phase 10
输出 Try-5A report

--------------------------------------------------
37. 开发原则
--------------------------------------------------

不要一次性写完所有代码再统一测试。

每个 Phase 完成后：

- 运行 smoke test；
- 保存中间结果；
- 检查实际数据流是否真的消费了该层输出。

特别防止 Try-3 曾经的问题：

“生成了 Robot Plan / Interface Graph，
但后端实际上没有使用它。”

必须做 dataflow audit：

A1：
Robot Assembly Plan
必须真实影响 Link Coarse Spec / CAD。

A2：
Joint Interface Contract
必须真实影响 parent / child interface geometry。

否则不能声称方法组件生效。

--------------------------------------------------
38. Try-5A 最重要的原则
--------------------------------------------------

不要问：

“这一台粗机械臂看起来够不够漂亮？”

Try-5A 真正的问题是：

> 这是不是一台结构完整、接口对齐、
> 运动学一致、可以继续精细化的机械臂骨架？

如果答案是 YES，

才进入 Try-5B：

Semantic-Inventory-Guided Link Detailing。

--------------------------------------------------
39. 当前执行要求
--------------------------------------------------

请现在开始 Try-5A 开发。

优先完成：

Phase 1
+
Phase 2
+
Phase 3

即：

1. 选 Robot A；
2. 解析 sanitized URDF；
3. 建 Kinematic Skeleton；
4. 验证 FK / frame；
5. 建 Robot Assembly Plan；
6. 建 Joint Interface Graph；
7. 生成每个 Joint 的 Shared Interface Contract；
8. 做 dataflow / leakage audit。

完成 Phase 1–3 后先停止。

不要立即跑 A0/A1/A2。

先汇报：

- Robot A；
- URDF skeleton；
- link roles；
- joint/interface contracts；
- coarse link plan；
- FK 验证；
- 是否存在接口设计歧义；
- 是否发现 GT 泄漏风险。

我确认后再继续 Phase 4。