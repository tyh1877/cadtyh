# RobotCAD Try-4
# Semantic Macro-Part Reconstruction with Quality-Gated Selective Repair

请启动 RobotCAD Try-4 方法探索实验。

Try-3 已暂停继续做补丁式修复。
不要继续完善 Try-3 的整机多 Agent pipeline，也不要试图在本实验中重新完成 Try-3。

Try-4 的目标是：

> 先把机械臂的各个语义 Macro-Part 独立重建好，再考虑后续装配。

核心研究问题从：

Whole Robot Generation

收敛为：

Semantic Macro-Part Reconstruction

即：

GT STEP
-> Semantic Macro-Part decomposition
-> colored / isolated visual reference
-> semantic label + local URDF context
-> Codex CLI Agent + shared Skills
-> Mechanical Feature Graph
-> Executable CAD IR
-> FreeCAD
-> Structured GT-grounded Review
-> Quality Gate
-> Selective Local Repair / Replan

本实验不生成完整机械臂装配体。

--------------------------------------------------
0. 核心原则
--------------------------------------------------

本实验必须遵守以下原则：

1. 使用 Codex CLI 作为当前实验阶段的主 Agent。
   不需要自行搭建 LLM API 调用框架。

2. 使用 FreeCAD 作为 CAD 执行环境。

3. Agent 负责：
   - 视觉理解
   - 机械语义理解
   - Feature planning
   - CAD planning
   - repair decision execution

4. FreeCAD backend 负责：
   - deterministic native CAD execution
   - FCStd
   - STEP
   - STL
   - feature/object state
   - recompute
   - export

5. 过去计划中的多个 Agent 暂时优先实现为共享 Skill：
   - Visual Skill
   - Semantic/Mechanical Skill
   - Detail Skill
   - CAD Planning Skill
   - Review Skill
   - Repair Skill

6. 本实验不能采用固定线性：

Generate
-> Review
-> Repair
-> Review
-> Repair

所有 Part 都无条件运行相同轮数。

必须采用：

Evaluate
-> Quality Gate
-> Selective Repair

已经达到设计要求的 Part 或 Feature 必须冻结，不再进入修改。

7. 不允许 silent fallback。

8. 不允许 case-specific Python CAD generator。

9. GT STEP/B-Rep 不直接输入 Codex。
   GT STEP 仅用于：
   - 构造 Semantic Macro-Part reference
   - 生成 reference renders
   - evaluation
   - offline annotations

10. Try-4 是方法开发实验，不是最终 benchmark。

--------------------------------------------------
1. 实验名称与核心假设
--------------------------------------------------

实验名称：

Try-4:
Semantic Macro-Part Reconstruction
with Quality-Gated Selective Repair

核心假设：

H1:
把整台机械臂分解为具有明确机械语义的 Macro-Part 后，
AI 对局部机械结构和 CAD feature 的理解会明显好于整机一次性生成。

H2:
明确的 RobotPart-LOD modeling standard
可以减少“box/cylinder 粗略占位即可”的生成行为。

H3:
Global context + isolated part views + semantic labels
可以提高 Mechanical Feature Grounding。

H4:
结构化、GT-grounded 的 Review
比自由文本式“看起来不像，请修改”更能产生可执行且有效的修改。

H5:
Quality-Gated Selective Repair
可以减少不必要修改和 regression，
并把更多计算预算分配给真正困难的 Part。

--------------------------------------------------
2. 数据规模：只使用 3 台机器人
--------------------------------------------------

Try-4 方法探索阶段只使用 3 台机器人。

不要扩展到 5 / 15 / 40+。

建议划分：

Robot A:
Development Robot
Easy / Medium

Robot B:
Development Robot
Hard
应包含明显复杂的：
- shoulder
- elbow
- wrist
- curved housing
- lofted/tapered regions

Robot C:
Frozen Transfer Robot

要求：

Robot A / B：
允许用于方法开发、调 Skill、调阈值。

Robot C：
在 Try-4 方法、Skill、Quality Gate threshold 基本冻结以后才正式运行。

不要在 Robot C 上反复观察结果后继续调方法，
否则它不再作为 transfer diagnostic。

生成：

try4/
  robots/
    try4_robot_split.csv
    robot_selection.md

明确记录：

- robot_id
- role: DEV_A / DEV_B / TRANSFER
- DOF
- number_of_macro_parts
- geometry difficulty
- surface complexity
- why_selected

--------------------------------------------------
3. Semantic Macro-Part 定义
--------------------------------------------------

不要强行把目标对象叫 manufacturing part。

Try-4 的重建单位定义为：

# Semantic Macro-Part

定义：

> 一个具有相对独立机械功能、可独立观察和建模、
> 并且适合作为后续装配单元的机械功能区域。

一个 Semantic Macro-Part：

- 可以对应一个实体；
- 可以包含多个实体；
- 可以对应原始 CAD 中的子装配；
- 不要求与 BOM 最细粒度 manufacturing part 一一对应。

目标是形成适合 AI 理解和重建的机械粒度。

--------------------------------------------------
4. Semantic Macro-Part 分割
--------------------------------------------------

使用 GT STEP 进行离线 semantic decomposition。

参考 CV 中 instance/semantic segmentation 的思想：

整机 STEP 被划分为若干 Semantic Macro-Parts。

每个 Macro-Part：

- 使用唯一 part_id；
- 使用稳定、唯一的颜色；
- 分配 role_class；
- 分配 open-vocabulary semantic_label。

例如：

part_id:
R01_P03

role_class:
joint_module

semantic_label:
"elbow housing module"

description:
"Mechanical module surrounding the elbow revolute joint
and connecting upper arm with forearm."

proximal_joint:
J2

distal_joint:
J3

不要硬编码所有机器人必须具有：

base
shoulder
upper_arm
elbow
forearm
wrist
flange

role_class 可以冻结一个小的通用集合，例如：

- base_module
- link_module
- joint_module
- wrist_module
- end_interface
- support_structure
- accessory
- other

semantic_label 保持开放词汇。

这样遇到特殊机器人结构时，
允许使用新的 semantic label。

--------------------------------------------------
5. Macro-Part annotation 文件
--------------------------------------------------

每台机器人建立：

semantic_parts.json

例如：

{
  "robot_id": "R01",
  "parts": [
    {
      "part_id": "R01_P00",
      "role_class": "base_module",
      "semantic_label": "base mounting and first-axis housing",
      "color_rgb": [220, 60, 60],
      "proximal_joint": null,
      "distal_joint": "J1",
      "description": "...",
      "critical_regions": [],
      "interfaces": []
    }
  ]
}

必须保留：

- part_id
- semantic role
- color
- description
- related joints
- interface regions
- source STEP component/body mapping

--------------------------------------------------
6. 彩色 Reference Views
--------------------------------------------------

对于每台机器人，至少生成两类视觉参考。

A. Global Colored Context Views

整台机械臂保留所有 Macro-Part，
不同 Macro-Part 使用不同颜色。

至少：

- front
- rear
- left
- right
- top
- isometric

目的：

让 Agent 理解：

- 当前 Part 在整机中的位置；
- 邻接关系；
- 大致尺度；
- 哪些区域属于目标 Part。

--------------------------------------------------

B. Isolated Macro-Part Views

每个 Macro-Part 单独显示。

至少：

- front
- side
- top
- isometric

必要时允许：

- proximal joint crop
- distal joint crop
- feature-level crop

但禁止直接提供：

- STEP
- B-Rep faces
- exact GT sketches
- GT feature tree

正式 Agent 输入是：

rendered visual evidence

而不是：

GT CAD geometry object。

--------------------------------------------------
7. Semantic Part Input Packet
--------------------------------------------------

每个 Part 的输入包至少包含：

PartInputPacket =

1. global colored context views
2. isolated part views
3. semantic label
4. role class
5. textual description
6. related proximal/distal joint context
7. sanitized local URDF information
8. global scale anchors
9. RobotPart-LOD standard
10. allowed modeling skills

例如：

{
  "part_id": "R01_P03",
  "semantic_label": "elbow housing module",
  "role_class": "joint_module",
  "proximal_joint": {...},
  "distal_joint": {...},
  "scale_context": {...},
  "reference_images": [...]
}

--------------------------------------------------
8. 冻结 RobotPart-LOD v1
--------------------------------------------------

Try-4 必须首先定义：

skills/
  robot_part_modeling_standard/
    SKILL.md

该 Skill 明确：

> 一个 Macro-Part 建到什么细粒度才算完成。

名称：

# RobotPart-LOD v1
Engineering Exterior Reconstruction

--------------------------------------------------
9. RobotPart-LOD v1：必须建模内容
--------------------------------------------------

输入证据支持时，以下内容原则上必须建模：

A. Primary Shape

- overall envelope
- major dimensions/proportions
- principal section family
- dominant taper
- major curvature
- primary structural body

B. Joint-related Geometry

- proximal joint housing
- distal joint housing
- joint neck
- rotary bulge
- joint-centered transition

C. Functional Exterior Features

- flange
- mounting face
- boss
- visible holes
- hole pattern
- external recess
- slot
- cutout
- local opening
- visible mounting structure

D. Structural Exterior Features

- shell-like geometry
- rib
- web
- cover region
- strengthening bulge
- lightening cut
- cavity visible from outside

E. Surface Geometry

- rounded section
- tapered transition
- lofted transition
- revolved housing
- sweep-like geometry
- major fillet group
- major chamfer group
- blended curved transition

--------------------------------------------------
10. RobotPart-LOD v1：允许简化内容
--------------------------------------------------

允许简化：

- thread teeth
- logo
- text engraving
- extremely small chamfer
- exact screw-head geometry
- invisible internal fasteners
- invisible motor
- invisible reducer
- invisible bearing
- internal cable details
- hidden manufacturing geometry unsupported by input

原则：

不要从外观图猜不可见内部结构。

Try-4 重点是：

Engineering Exterior Detail

不是：

complete manufacturing CAD recovery。

--------------------------------------------------
11. 特征纳入标准
--------------------------------------------------

冻结一个通用规则：

Critical Functional Features：

不受尺度阈值限制，
只要 semantic / joint / interface context 明确要求，
必须建模。

普通视觉细节：

只有在：

- 至少一个高质量视图清晰可见，
  preferably multiple views；
- 对整体 silhouette / local geometry 有明显贡献；
- 超过冻结相对尺度阈值；

时才要求建模。

相对尺度阈值在 Robot A/B 开发阶段确定后冻结。

Robot C 不允许重新调整。

--------------------------------------------------
12. Codex CLI 工作方式
--------------------------------------------------

Try-4 Agent 使用 Codex CLI。

不搭建额外模型 API pipeline。

建议：

一个 Semantic Macro-Part
=
一个独立 Codex working context/session。

同一个 Part 的：

generation
-> review
-> repair

保持在同一上下文中。

不同 Part：

原则上使用独立上下文，
避免跨 Part 状态污染。

--------------------------------------------------
13. 不实现复杂多 Agent，优先改成 Shared Skills
--------------------------------------------------

Try-4 暂时采用：

One Main Codex Agent
+
Specialized Shared Skills

不要重新搭建 Try-3 的多个独立 Agent。

建议至少实现：

skills/

  robot_part_modeling_standard/
    SKILL.md

  visual_grounding/
    SKILL.md

  semantic_mechanical_reasoning/
    SKILL.md

  mechanical_detail_planning/
    SKILL.md

  freecad_part_modeling/
    SKILL.md

  structured_part_review/
    SKILL.md

  structured_part_repair/
    SKILL.md

--------------------------------------------------
14. Visual Grounding Skill
--------------------------------------------------

Visual Skill 负责规范 Codex：

如何使用：

- global colored views
- isolated views
- local crops
- semantic color
- joint context

输出结构化 Visual Evidence。

例如：

{
  "part_id": "...",
  "observed_regions": [
    {
      "region": "distal_joint",
      "shape": "large rounded housing",
      "views": ["iso", "right"],
      "confidence": 0.91
    }
  ]
}

禁止输出长自由推理文本。

--------------------------------------------------
15. Semantic Mechanical Reasoning Skill
--------------------------------------------------

根据：

- semantic label
- role class
- URDF joint context
- visual evidence

生成：

Mechanical Part Interpretation

回答：

- 这个 Part 的机械功能是什么；
- proximal/distal 区域分别承担什么；
- 哪些区域是 joint housing；
- 哪些是 link body；
- 哪些是 interface；
- 哪些视觉结构是功能性；
- 哪些只是外形细节。

不能虚构不可观察内部结构。

--------------------------------------------------
16. Mechanical Feature Graph
--------------------------------------------------

正式建立：

Mechanical Feature Graph v1

每个 Part 至少包括：

Primary Features
Functional Features
Structural Features
Surface Features
Interface Features

例如：

{
  "part_id": "R01_P03",

  "features": [
    {
      "feature_id": "F01",
      "feature_type": "main_link_body",
      "priority": "primary",
      "evidence": [...]
    },
    {
      "feature_id": "F02",
      "feature_type": "distal_joint_housing",
      "priority": "critical",
      "evidence": [...]
    }
  ]
}

每个 Feature 至少记录：

- feature_id
- semantic feature type
- role
- evidence
- reference region/frame
- estimated dimensions
- shape family
- intended CAD strategy
- dependencies
- critical / non-critical
- confidence

--------------------------------------------------
17. Feature Graph -> Executable CAD IR
--------------------------------------------------

禁止：

Agent
-> 一大段 case-specific FreeCAD Python

必须：

Mechanical Feature Graph
        ↓
Executable CAD IR
        ↓
FreeCAD backend

CAD IR 必须足够具体，可以执行：

- sketch/profile
- reference frame
- dimensions
- axis
- operation type
- operation mode
- dependencies
- feature relationships

复杂操作不能只写：

"make a loft"

而必须给出足够的可执行参数。

--------------------------------------------------
18. FreeCAD 操作要求
--------------------------------------------------

尽量真实使用：

- Pad / Extrude
- Pocket
- Revolve
- Loft
- Sweep / Pipe
- Thickness / Shell
- Boolean Fuse
- Boolean Cut
- Fillet
- Chamfer
- Pattern
- Mirror

禁止：

Loft fail
-> Box

Revolve fail
-> Cylinder

Shell fail
-> keep solid

并仍标 success。

所有 fallback 必须显式记录，
Try-4 正式结果中：

silent fallback = 0

--------------------------------------------------
19. Try-4 不生成完整机器人
--------------------------------------------------

本实验到 Macro-Part 为止。

不要：

- assemble full robot
- create full joint chain
- compute workspace
- compute EE trajectory
- evaluate whole-arm collision
- solve full interface gap

但每个 Part 必须保留：

- proximal joint frame
- distal joint frame
- proximal interface region
- distal interface region
- semantic interface type

用于未来 Try-5。

--------------------------------------------------
20. 系统架构：禁止固定线性 repair pipeline
--------------------------------------------------

Try-4 必须实现：

# Blackboard + Quality-Gated Scheduler

而不是：

for every part:
  Generate
  Repair
  Repair
  Repair

建立共享：

PartState Blackboard

每个 Part 维护：

- current state
- current FCStd
- Feature Graph
- CAD IR
- feature status
- geometry metrics
- feature metrics
- repair history
- repair round
- frozen features
- failed features

--------------------------------------------------
21. Part State Machine
--------------------------------------------------

每个 Part 采用以下状态：

NEW
↓
EVIDENCE_READY
↓
PLAN_READY
↓
BUILT
↓
EVALUATED

EVALUATED 后只能进入：

PASS
LOCAL_REPAIR
REPLAN

PASS:
-> FROZEN

LOCAL_REPAIR:
-> REPAIRED
-> EVALUATED

REPLAN:
-> PLAN_READY
-> rebuild
-> EVALUATED

不要无条件进入 repair。

--------------------------------------------------
22. 三个 Quality Gates
--------------------------------------------------

# Gate A — Plan Gate

发生在：

Feature Graph
-> CAD IR

检查：

- semantic label 是否被消费；
- critical feature 是否存在；
- RobotPart-LOD 是否满足；
- CAD IR 是否完整；
- required native operations 是否有完整参数。

如果不满足：

PLAN_INCOMPLETE

不要浪费时间调用 FreeCAD。

--------------------------------------------------

# Gate B — Initial Build Quality Gate

首次生成 Part 后执行。

检查：

1. CAD validity
2. geometry
3. visible mechanical features
4. semantic role
5. RobotPart-LOD compliance
6. local surface quality
7. editability

输出：

PASS
LOCAL_REPAIR
REPLAN

--------------------------------------------------

# Gate C — Post-Repair Gate

每次 repair 后立即执行。

若满足全部 requirements：

PASS
-> FROZEN

不要再进入下一轮 repair。

若仍有局部错误：

LOCAL_REPAIR

若发现 Feature Graph / geometry family 根本错误：

REPLAN

--------------------------------------------------
23. Multi-Criteria Quality Gate
--------------------------------------------------

禁止用单一总分：

score > 0.8

决定 PASS。

建议 PASS 同时满足：

CAD_VALID = true

Geometry:
IoU >= tau_iou

Normalized Chamfer <= tau_cd

Normalized HD95 <= tau_hd95

Mechanical Features:
MFR >= tau_mfr

Critical Feature Recall = 100%

Editability:
FCStd reopen = PASS
recompute = PASS
native feature validity = PASS

阈值：

tau_iou
tau_cd
tau_hd95
tau_mfr

只能在 Robot A/B development set 上调。

冻结以后：

Robot C 直接使用相同 threshold。

不要针对 Part 单独调整 threshold。

--------------------------------------------------
24. 尺度归一化
--------------------------------------------------

Chamfer / HD95 等跨不同 Part 使用时：

建议以：

GT bbox diagonal

或冻结统一规则做 normalization。

避免：

大型 base
与
小型 wrist

使用完全不可比较的绝对距离阈值。

同时保留 absolute dimension error。

--------------------------------------------------
25. Progressive Feature Freezing
--------------------------------------------------

这是 Try-4 的核心机制之一。

Part 未通过，不等于所有 Feature 都可以重做。

例如：

F01 proximal housing = PASS
F02 main body        = PASS
F03 distal housing   = FAIL
F04 side recess      = FAIL

下一轮 Repair：

F01 / F02
必须：

FROZEN / PROTECTED

只能修改：

F03 / F04

建立：

feature_status:

PASS_FROZEN
FAIL_REPAIR
FAIL_REPLAN
UNASSESSED

--------------------------------------------------
26. Structured GT-Grounded Review
--------------------------------------------------

Review 不能只是：

“GT 看起来更圆，你的模型不像，请改。”

Review 输入必须包括：

1. GT part reference renders
2. generated part renders
3. semantic label
4. role class
5. RobotPart-LOD requirements
6. Mechanical Feature Graph
7. current FreeCAD feature tree
8. deterministic geometry metrics
9. per-region discrepancy
10. previous repair history

Reviewer 必须输出：

# Structured Repair Contract

不能只输出自由文本。

--------------------------------------------------
27. Reviewer 的职责边界
--------------------------------------------------

VLM / Codex Visual Reasoning：

负责判断：

- missing feature
- wrong shape family
- wrong region semantics
- missing recess
- missing flange
- wrong taper
- wrong transition
- surface family mismatch

Deterministic Comparator：

负责提供：

- bbox dimension difference
- centroid difference
- silhouette mismatch
- local width/height
- IoU
- Chamfer
- HD95
- local surface discrepancy
- joint-region extent difference

原则：

VLM 负责：

WHAT is wrong

deterministic comparator 负责：

HOW MUCH is wrong

--------------------------------------------------
28. Repair Contract Schema
--------------------------------------------------

至少：

{
  "part_id": "...",
  "status": "LOCAL_REPAIR",

  "failed_gates": [],

  "violations": [
    {
      "region": "distal_joint_housing",
      "feature_id": "F03",
      "type": "missing_feature",
      "severity": "high",
      "requirement": "...",
      "evidence_views": [...]
    }
  ],

  "repair_actions": [
    {
      "priority": 1,
      "action": "ADD_FEATURE",
      "feature_type": "rotary_joint_housing",
      "target_region": "distal",
      "cad_strategy": "REVOLVE",
      "reference_frame": "J3"
    }
  ],

  "protected_features": [
    "F01",
    "F02"
  ],

  "do_not_change": [
    "overall_link_length",
    "proximal_interface"
  ]
}

--------------------------------------------------
29. Repair action 类型
--------------------------------------------------

建议限制为有限集合：

ADD_FEATURE
REMOVE_FEATURE
MODIFY_PARAMETER
REPLACE_FEATURE
CHANGE_SHAPE_FAMILY
CHANGE_CAD_STRATEGY
LOCAL_REPLAN
FULL_PART_REPLAN

尽量不要让 Repair Agent自由发明修改动作。

--------------------------------------------------
30. Local Repair vs Replan
--------------------------------------------------

# LOCAL_REPAIR

适用于：

- dimension slightly wrong
- radius wrong
- recess depth wrong
- fillet missing
- boss undersized
- flange thickness wrong
- local taper inaccurate

只修改对应 Feature。

--------------------------------------------------

# REPLAN

适用于：

- main shape family wrong
- critical housing missing
- box used where lofted shell is required
- semantic role misunderstood
- Feature Graph misses major structure
- multiple related features structurally wrong

REPLAN 时：

允许回到：

Mechanical Feature Graph
或
CAD strategy

不要继续在错误 Feature Tree 上打补丁。

--------------------------------------------------
31. Repair 最大轮数
--------------------------------------------------

每个 Part：

Initial Generation = Round 0

最多：

3 repair rounds

即：

Round 0 initial
Round 1 repair
Round 2 repair
Round 3 final repair

如果提前 PASS：

立即 FROZEN。

不要强行跑满 3 轮。

--------------------------------------------------
32. Stagnation Gate
--------------------------------------------------

如果连续 repair 后：

geometry improvement < epsilon

或：

Feature Recall 无改善

或：

修改后 regression 明显增加

则不要继续同一种 LOCAL_REPAIR。

状态：

LOCAL_REPAIR
-> REPLAN

如果 REPLAN 后仍失败：

标记：

UNRESOLVED

不要无限循环。

--------------------------------------------------
33. Regression Protection
--------------------------------------------------

每次 repair 后检查：

已经 PASS_FROZEN 的 Feature 是否恶化。

如果出现：

frozen feature regression

则：

当前 repair 判为 regression。

优先：

rollback

或重新生成仅失败局部。

必须统计：

Regression Rate

--------------------------------------------------
34. Adaptive Compute Allocation
--------------------------------------------------

Scheduler 每轮只处理：

LOCAL_REPAIR
REPLAN

状态的 Part。

例如：

P0 PASS
P1 REPAIR
P2 PASS
P3 REPLAN
P4 REPAIR

下一轮只能运行：

P1
P3
P4

P0/P2 不再调用 Codex。

目标：

让简单 Part 早停，
困难 Part 获得更多推理预算。

--------------------------------------------------
35. Try-4 主实验条件
--------------------------------------------------

建议只做三组：

# T0 — Direct Part Reconstruction

Semantic Part Input Packet
-> Codex
-> FreeCAD

一次生成。

不使用完整 Try-4 Skills。
不 repair。

作为 direct baseline。

--------------------------------------------------

# T1 — Skill-Guided Part Reconstruction

Input
-> Visual Skill
-> Semantic/Mechanical Skill
-> RobotPart-LOD Skill
-> Mechanical Feature Graph
-> CAD Planning Skill
-> FreeCAD

不进行 iterative repair。

用于验证：

Skill-guided engineering planning 是否提高初始生成质量。

--------------------------------------------------

# T2 — Quality-Gated Selective Repair

T1
+
Structured GT-grounded Review
+
Quality Gate
+
Progressive Feature Freezing
+
Selective Repair / Replan

最多 3 轮。

这是 Try-4 主方法。

--------------------------------------------------
36. Free-form Repair 小型消融
--------------------------------------------------

为了证明 Structured Repair 的价值：

只选择 Robot B 中若干最困难 Macro-Part 做额外小型 ablation。

比较：

A. Free-form VLM Repair

输入：
GT vs Generated

输出：
自由文字建议

vs

B. Structured Grounded Repair

使用：

semantic label
+
LOD
+
Feature Graph
+
FreeCAD feature tree
+
deterministic discrepancy
+
Repair Contract

不需要在全部 3 robots 上跑这个消融。

重点验证：

structured feedback
是否：

- repair success 更高；
- regression 更低；
- 修改更局部；
- 收敛更快。

--------------------------------------------------
37. Part-centric Geometry Metrics
--------------------------------------------------

至少：

- voxel IoU
- Chamfer
- normalized Chamfer
- HD95
- normalized HD95
- bbox dimension error
- centroid error
- silhouette IoU

如果实现稳定：

增加：

- high-curvature-region Chamfer
- normal error
- local surface error

--------------------------------------------------
38. Mechanical Detail Metrics
--------------------------------------------------

至少建立：

Mechanical Feature Recall (MFR)

Mechanical Feature Precision

并按类别统计：

- joint housing recall
- flange recall
- boss recall
- recess recall
- cutout recall
- visible hole recall
- pattern recall
- taper/transition recall
- shell-like geometry recall
- major fillet/chamfer recall

Critical Features 单独报告：

Critical Feature Recall

--------------------------------------------------
39. CAD Editability Metrics
--------------------------------------------------

每个 Part 至少检查：

- FCStd created
- FCStd reopen
- recompute
- native feature objects exist
- feature parameters readable
- STEP export
- STL export
- B-Rep valid

额外进行一个简单参数修改测试：

从可编辑参数中选择一个代表性参数，例如：

- housing radius
- link width
- flange thickness
- recess depth

执行：

±5%

然后检查：

- recompute
- valid solid
- intended region changes
- unrelated frozen regions remain valid

--------------------------------------------------
40. Repair Metrics
--------------------------------------------------

T2 至少统计：

- repair-trigger rate
- average repair rounds
- early-pass rate
- repair contract execution rate
- repair success rate
- replan rate
- regression rate
- frozen-feature preservation rate
- metric improvement per round
- unresolved rate
- Codex calls saved by early stopping

--------------------------------------------------
41. 每轮必须保存完整 Artifact
--------------------------------------------------

每个 Part 每一轮保存：

round_0/
  model.FCStd
  model.step
  model.stl
  renders/
  feature_graph.json
  cad_ir.json
  feature_tree.json
  metrics.json

round_1/
  review_contract.json
  repair_log.json
  ...

直到：

PASS/FROZEN
或
UNRESOLVED

--------------------------------------------------
42. Blackboard 数据结构
--------------------------------------------------

建议：

part_state.json

至少：

{
  "part_id": "...",
  "state": "LOCAL_REPAIR",
  "repair_round": 1,

  "quality_gates": {
    "geometry": "PASS",
    "critical_features": "FAIL",
    "cad_validity": "PASS",
    "editability": "PASS"
  },

  "feature_states": {
    "F01": "PASS_FROZEN",
    "F02": "PASS_FROZEN",
    "F03": "FAIL_REPAIR"
  },

  "current_artifact": "...",
  "previous_metrics": {},
  "repair_history": []
}

--------------------------------------------------
43. Scheduler
--------------------------------------------------

实现一个简单 scheduler。

不要把调度逻辑全部藏在 Codex prompt 中。

Scheduler 根据状态决定：

NEW
-> Generation

LOCAL_REPAIR
-> Repair Skill

REPLAN
-> Planning Skill

PASS
-> no action

UNRESOLVED
-> stop

这样以后可方便迁移成正式 Multi-Agent。

--------------------------------------------------
44. GT 泄漏规则
--------------------------------------------------

GT 可以用于：

- reference renders
- semantic segmentation annotation
- quality evaluation
- structured reviewer

GT 不允许用于：

- 直接读取 STEP feature dimensions 给 generator
- 直接复制 B-Rep
- 直接读取 feature tree
- 自动把 GT sketch/profile 交给 FreeCAD generator
- case-specific parameter extraction 后直接重建

Try-4 是：

reference-conditioned reconstruction

不是：

STEP copy/replay。

--------------------------------------------------
45. Dev / Transfer 阈值冻结
--------------------------------------------------

Robot A/B：

用于确定：

- LOD threshold
- quality gate threshold
- epsilon stagnation threshold
- max repair rounds
- Skill definitions

一旦冻结：

生成：

try4_frozen_protocol.json

然后才运行：

Robot C

Robot C 运行后：

不得再修改：

- threshold
- Skills
- LOD
- repair rule
- evaluator

如果修改：

Robot C 失去 transfer 资格。

--------------------------------------------------
46. 结果分析重点
--------------------------------------------------

不要只报告：

FreeCAD success = 100%

Try-4 真正要回答：

Q1.
Semantic Macro-Part decomposition
是否让单零件机械结构明显更容易恢复？

Q2.
Skill-guided modeling
是否让 T1 比 T0 更完整、更少 primitive？

Q3.
Structured Quality-Gated Repair
是否让 T2 在不破坏正确 Feature 的前提下继续提高质量？

Q4.
Selective Repair
是否减少不必要 Codex 调用？

Q5.
Progressive Feature Freezing
是否降低 regression？

Q6.
Robot C transfer
是否仍能获得类似方向的提升？

--------------------------------------------------
47. 成功标准
--------------------------------------------------

Try-4 不需要一个“全部指标都超过某个绝对值”的 Go/No-Go。

但至少应观察到：

T0 -> T1：

- Mechanical Feature Recall 提高；
- 复杂 Feature 使用增加；
- primitive proxy 减少；
- geometry 有方向性改善。

T1 -> T2：

- failed feature 数减少；
- geometry 继续改善；
- critical feature recall 提高；
- regression 较低；
- 多数已合格 Feature 保持冻结；
- 一部分 Part 能够 early stop。

并且：

Robot C 上仍存在相同方向趋势。

--------------------------------------------------
48. 如果 Try-4 成功，后续路线
--------------------------------------------------

Try-5：

Interface Pair Reconstruction

输入：

两个相邻 Macro-Part
+
shared joint/interface semantics

研究：

- matching interface
- Port/Mate
- joint-centered geometry
- gap
- coaxiality
- clearance

--------------------------------------------------

Try-6：

Whole Robot Assembly

使用：

Try-4 high-quality Macro-Parts
+
Try-5 interface mechanism

研究完整机械臂装配。

--------------------------------------------------
49. 结果目录建议
--------------------------------------------------

experiments/try4/

  protocol/
    try4_frozen_protocol.json
    robot_part_lod_v1.md

  robots/
    try4_robot_split.csv
    semantic_parts/

  skills/
    visual_grounding/
    semantic_mechanical_reasoning/
    robot_part_modeling_standard/
    mechanical_detail_planning/
    freecad_part_modeling/
    structured_part_review/
    structured_part_repair/

  schemas/
    semantic_part.schema.json
    visual_evidence.schema.json
    mechanical_feature_graph.schema.json
    executable_cad_ir.schema.json
    repair_contract.schema.json
    part_state.schema.json

  T0/
  T1/
  T2/

results/try4/

  geometry_metrics.csv
  mechanical_feature_metrics.csv
  editability_metrics.csv
  repair_metrics.csv
  resource_metrics.csv

  per_robot/
  per_part/
  per_round/

  contact_sheets/

  try4_report.md

--------------------------------------------------
50. 最终报告必须明确回答
--------------------------------------------------

完成 Try-4 后必须汇报：

1. 三台机器人分别是什么角色：
   DEV_A / DEV_B / TRANSFER？

2. 每台被分成多少 Semantic Macro-Part？

3. Semantic Macro-Part 粒度是否合理？

4. 最终 RobotPart-LOD v1 是什么？

5. T0/T1/T2 分别多少 Part 成功？

6. T0 -> T1：
   MFR / IoU / CD / HD95 如何变化？

7. T1 -> T2：
   指标如何继续变化？

8. 哪些 Feature 最容易恢复？

9. 哪些 Feature 最难恢复？

10. joint housing 是否稳定出现？

11. loft / sweep / shell / fillet 是否真正用于有需要的区域？

12. 当前生成是否仍主要由 box/cylinder 构成？

13. Quality Gate 的冻结阈值是什么？

14. 有多少 Part Round 0 就 PASS？

15. 有多少经过 Round 1 / 2 / 3 才 PASS？

16. 有多少进入 REPLAN？

17. Progressive Feature Freezing 是否工作？

18. Regression Rate 是多少？

19. Structured Repair 是否优于 free-form repair？

20. structured feedback 最常见的错误类型是什么？

21. Reviewer 是否能明确指出：
    what to change
    where to change
    how to change
    what not to change？

22. deterministic comparator 是否真正提供了数值修改依据？

23. Robot C 上的提升是否仍存在？

24. 参数修改后 FCStd 是否仍可 recompute？

25. Try-4 的当前最大瓶颈是什么：
    - semantic decomposition
    - visual grounding
    - mechanical feature grounding
    - CAD parameter estimation
    - FreeCAD operation planning
    - structured review
    - repair execution

26. 是否值得进入 Try-5 Interface Pair Reconstruction？

--------------------------------------------------
51. 最重要的 Try-4 方法表达
--------------------------------------------------

不要把 Try-4 描述成：

“把机械臂拆开一个个生成，然后多修几次。”

更准确的表达是：

Semantic Macro-Part Grounding
        ↓
Skill-Guided Engineering Reconstruction
        ↓
Structured GT-Grounded Evaluation
        ↓
Multi-Criteria Quality Gate
        ↓
Feature-Level Progressive Freezing
        ↓
Selective Repair / Replan
        ↓
Editable Parametric Macro-Part CAD

核心区别：

不是：

Generate
-> VLM looks at image
-> regenerate everything

而是：

Generate
-> determine exactly which requirements fail
-> freeze everything already correct
-> issue an executable structured repair contract
-> modify only failed features
-> stop immediately once quality requirements are met

--------------------------------------------------
52. 当前实验阶段的优先级
--------------------------------------------------

不要一次把所有内容全部实现。

推荐严格按以下顺序推进：

Phase 1
Semantic Macro-Part annotation + colored reference generation

Phase 2
RobotPart-LOD v1

Phase 3
T0 direct single-part reconstruction

Phase 4
Shared Skills + T1

Phase 5
deterministic evaluator + Quality Gate

Phase 6
Structured Review Contract

Phase 7
Selective Repair + Progressive Feature Freezing

Phase 8
T2 full run on Robot A/B

Phase 9
freeze protocol

Phase 10
run Robot C transfer

每完成一个 Phase：

先汇报当前结果。

不要为了“Try-4 完成”一次性写大量未经验证的代码。

--------------------------------------------------
53. 第一阶段执行要求
--------------------------------------------------

请现在先开始：

Phase 1 + Phase 2

即：

1. 冻结 3 robot split；
2. 将 GT STEP 划分为 Semantic Macro-Part；
3. 为每个 Macro-Part 建立 semantic label；
4. 为每个 Macro-Part 分配稳定颜色；
5. 生成 global colored context views；
6. 生成 isolated part views；
7. 建立 semantic_parts.json；
8. 编写 RobotPart-LOD v1 SKILL.md；
9. 给出每个 Macro-Part 的 expected visible/critical feature checklist；
10. 做泄漏审计。

完成 Phase 1 + 2 后先停止。

不要立即执行 T0/T1/T2。

先向我汇报：

- 三台机器人；
- Macro-Part 划分；
- 颜色；
- semantic labels；
- LOD；
- feature checklist；
- 泄漏风险。

我确认后再继续 Phase 3。