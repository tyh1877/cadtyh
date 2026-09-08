# RobotCAD Try-5A.3
# Knowledge-Guided Interface Planning
# + Hierarchical Repair Scope Arbitration

请继续直接修改现有 Try-5 代码。

IMPORTANT:
- 不要新建一套 Try-5A.3 pipeline；
- 不要复制 try5 scripts/backend/evaluator；
- 直接修改当前 try5 主代码；
- 使用 Git commit 保存关键节点；
- 历史实验结果可以单独保存，但代码保持 single evolving codebase。

--------------------------------------------------
0. 背景
--------------------------------------------------

Try-5A / A.1 / A.2 已经得到：

1. URDF skeleton / frame / FK 基本稳定；
2. shared interface 的方向是有效的；
3. exact collision evaluator 已建立；
4. FreeCAD 不是主要瓶颈；
5. 当前暴露两个新的核心问题：

问题 A：
AI 仍然不知道应该采用什么机械接口。

URDF 只提供：

joint type
origin
axis
parent
child
limit

但没有提供：

fork-pin
coaxial housing
nested housing
flange
rail-slider
等真实机械接口形式。

当前 Interface Planner 很大程度仍在猜。

问题 B：
repair 容易为了满足指标生成没有机械意义的 CAD patch。

例如：

gap 存在
→ 直接填一个小方块
→ BICR / gap 变好

但该方块没有明确 mechanical role。

因此 Try-5A.3 不继续单纯优化碰撞指标，
而是加入：

1. Robot Interface Knowledge Base
2. Mechanical Meaningfulness Gate
3. Hierarchical Repair Scope Arbiter
4. Design-level repair instead of direct CAD patching

--------------------------------------------------
1. 核心研究问题
--------------------------------------------------

RQ1:

机器人领域接口知识是否能让 Agent
比自由推断更稳定地选择合理 interface family？

RQ2:

当 coarse model 出现问题时，
系统能否判断应该：

- 只改参数；
- 修改局部 feature；
- 重规划局部 body；
- 重规划整个 Link；
- 甚至重新设计 shared interface？

RQ3:

Mechanical Meaningfulness Gate
能否减少为了通过指标而生成的
meaningless geometry / metric-gaming geometry？

--------------------------------------------------
2. 本轮实验对象
--------------------------------------------------

仍然只使用 Robot A。

不要：
- Robot B
- transfer robot
- Try-5B fine detailing
- 扩大数据集

本轮仍是开发实验。

--------------------------------------------------
3. 不要推翻已经稳定的部分
--------------------------------------------------

原则上冻结：

- sanitized URDF authority
- Kinematic Skeleton
- FK implementation
- exact collision evaluator
- FreeCAD backend
- physical/virtual link classification

Interface Contract 本轮允许在需要时重新规划，
因为本轮专门研究 interface design。

--------------------------------------------------
PART I
Try-5A.3-I
Knowledge-Guided Interface Planning
--------------------------------------------------

4. 建立 Robot Interface Knowledge Base
--------------------------------------------------

建立一个小型机械臂接口知识库。

建议直接放在现有：

try5/knowledge/robot_interfaces/

不要做大型 RAG 系统。

优先使用 Markdown / JSON。

第一版只覆盖少量通用 family：

- coaxial_rotary_interface
- fork_pin_interface
- nested_rotary_housing
- flange_interface
- planar_mount_interface
- rail_slider_interface
- end_tool_interface

每种 family 必须包含：

1. applicability
2. required mechanical substructures
3. required geometric relations
4. allowed clearance/contact
5. typical parent/child layout
6. CAD realization strategy
7. forbidden configurations
8. verification rules
9. uncertainty notes

--------------------------------------------------
5. Knowledge Entry 示例
--------------------------------------------------

例如：

interface_family:
fork_pin_interface

applicable_when:
- joint_type = revolute
- one side visually bifurcates
- opposite side is central boss / housing

required_substructures:
- left_fork_arm
- right_fork_arm
- central_mating_member
- coaxial bore/pin region

required_relations:
- fork arms symmetric
- joint axis crosses both fork arms
- central member lies between fork arms
- rotational clearance preserved

forbidden:
- solid bridge across rotational clearance
- arbitrary connector block across joint
- parent and child fused into one rigid solid

typical_CAD_strategy:
- fork body
- boss/housing
- coaxial holes
- local clearance region

--------------------------------------------------
6. Knowledge Base 不是 CAD 模板库
--------------------------------------------------

禁止：

- Robot-A-specific interface template
- R01_J03_template
- exact GT geometry
- exact GT dimensions
- stored STEP/B-Rep
- robot model specific answers

知识库必须描述：

“怎样设计这一类接口”

而不是：

“这个机器人接口长这样”。

--------------------------------------------------
7. Interface Retrieval / Selection
--------------------------------------------------

Interface Planner 输入：

- URDF joint type
- axis / origin
- parent/child Link role
- visual evidence
- neighboring coarse geometry
- knowledge base candidates

输出：

Interface Candidate Ranking

至少包含：

{
  "joint_id": "...",
  "candidate_interfaces": [
    {
      "family": "...",
      "evidence": [...],
      "knowledge_match": "...",
      "confidence": ...
    }
  ],
  "selected_family": "...",
  "selection_reason": "...",
  "uncertainty": ...
}

如果没有合适 family：

允许：

CUSTOM_INTERFACE

但必须说明为什么知识库现有类型不适用。

--------------------------------------------------
8. K0 / K1 对比
--------------------------------------------------

做一个小型接口实验：

K0:
当前 Interface Planner
不使用 knowledge base。

K1:
相同输入
+ Robot Interface Knowledge Base。

其他条件尽量保持一致。

重点比较：

- interface-family correctness/plausibility
- BICR
- physical attachment
- gap
- unintended penetration
- collision
- interface visual plausibility
- meaningless connector geometry

不要要求 K1 立即大幅提升 IoU。

核心是：

接口是否更像一个有机械意义的 joint realization。

--------------------------------------------------
9. Mechanical Meaningfulness Gate
--------------------------------------------------

从 Try-5A.3 开始：

任何新增 coarse CAD geometry
都必须有设计来源。

每个新增 geometry 至少包含：

- feature_id
- owning_link
- mechanical_role
- source_evidence
- source_design_node
- why_required
- related_interface/body
- CAD strategy

例如合法：

feature:
shoulder_support_web

mechanical_role:
rigidly connects shoulder body to J01 carrier

source:
interface knowledge + body layout

非法：

feature:
box_17

reason:
fill 3 mm gap

如果新增 geometry：

- 无 mechanical role
- 无 design provenance
- 不能映射到 Interface/Body/Graph node

则：

MECHANICAL_MEANINGFULNESS_FAIL

即使数值指标变好也不能接受。

--------------------------------------------------
10. 禁止 direct geometry patch
--------------------------------------------------

以后 repair 不允许：

detected gap
→ FreeCAD.addBox(...)
→ PASS

必须：

diagnosis
→ update design representation
→ regenerate affected CAD

例如：

gap closure
必须先更新：

Interface Contract
或
LinkCoarseSpec
或
Body Region Spec

再：

CAD IR
→ FreeCAD

原则：

Repair the design,
not the final mesh/solid directly.

--------------------------------------------------
PART II
Try-5A.3-II
Hierarchical Repair Scope Arbitration
--------------------------------------------------

11. 新增 Repair Scope Arbiter
--------------------------------------------------

建立：

Repair Scope Arbiter

它的职责不是直接修改 CAD。

输入：

- deterministic gate failures
- interface metrics
- attachment metrics
- collision metrics
- current Robot Plan
- Interface Contract
- LinkCoarseSpec
- renders
- VLM structured diagnosis
- repair history

输出：

应该修改到哪一层。

--------------------------------------------------
12. 五级 Repair Scope
--------------------------------------------------

固定：

R0 PARAMETER_REPAIR

只修改参数。

适用于：
- topology正确
- interface family正确
- body family正确
- 只是 radius / width / depth / spacing 等轻微错误

--------------------------------------------------

R1 LOCAL_FEATURE_REPAIR

修改单一局部 feature / region。

适用于：
- local gap
- local clearance
- local transition
- localized collision
- local section mismatch

--------------------------------------------------

R2 BODY_REGION_REPLAN

重新设计 Link 的一段 body。

适用于：
- 当前局部 shape family 不合理
- repeated local collision
- proximal/middle/distal region 结构错误

--------------------------------------------------

R3 WHOLE_LINK_REPLAN

重规划整个 Link body。

适用于：
- body family错误
- main topology错误
- structural path错误
- interface-to-interface body organization错误

--------------------------------------------------

R4 INTERFACE_PAIR_REPLAN

重新规划：

shared interface
+
parent local region
+
child local region

适用于：
- interface family选择错误
- 接口本身导致持续 attachment/collision failure
- visual structure与当前 interface family明显冲突

--------------------------------------------------
13. VLM 的角色
--------------------------------------------------

Deterministic evaluator 负责：

WHAT failed

例如：

- gap 3.0 mm
- BICR fail
- collision volume 2500 mm³
- sweep collision
- body disconnected

VLM 负责辅助判断：

WHY it may have failed

例如：

- interface family appears wrong
- fork structure missing
- body region family incompatible
- current support geometry has no visual/mechanical basis

Repair Arbiter 负责：

HOW MUCH must be changed

即选择：

R0 / R1 / R2 / R3 / R4

最终 PASS 仍然由 deterministic gate 决定。

--------------------------------------------------
14. Arbiter 输出 Schema
--------------------------------------------------

例如：

{
  "target": "J03/L02-L03",

  "failed_gates": [
    "PHYSICAL_ATTACHMENT",
    "COLLISION"
  ],

  "deterministic_evidence": {...},

  "vlm_diagnosis": {
    "suspected_root_cause": "interface_family_mismatch",
    "confidence": 0.86
  },

  "repair_scope": "R4_INTERFACE_PAIR_REPLAN",

  "reason": "...",

  "protected_states": [
    "URDF_J03_FRAME",
    "other_frozen_interfaces"
  ],

  "upstream_objects_to_modify": [
    "InterfaceContract_J03",
    "L02_distal_region",
    "L03_proximal_region"
  ]
}

--------------------------------------------------
15. Repair Scope Pilot
--------------------------------------------------

不要直接全机器人无限循环。

先选/构造 4 类典型错误进行开发验证。

Case A:
参数略错

预期：
R0

Case B:
局部碰撞或局部 gap

预期：
R1 或 R2

Case C:
整个 body family / topology错误

预期：
R3

Case D:
interface family根本错误

预期：
R4

要求：

Arbiter 给出 repair scope，
然后执行一次对应 design-level repair。

--------------------------------------------------
16. True Replan 要求
--------------------------------------------------

R2/R3/R4 不能只是：

same recipe + new parameters

R2 至少允许：
- replace local shape family
- rebuild local structural path

R3 至少允许：
- replace body family
- change topology/centerline/body organization

R4 至少允许：
- replace interface family
- rebuild Interface Contract
- rebuild both adjacent local body regions

否则不能记为真正 replan。

--------------------------------------------------
17. Progressive Freezing
--------------------------------------------------

继续保留：

- Kinematic state freezing
- passed interface freezing
- passed Link freezing
- passed region freezing

但：

如果 Arbiter 判定 R4，
允许解冻：

该 Joint 对应 interface
+
parent/child local regions

不能因为“之前 PASS”
永久禁止纠正错误设计。

--------------------------------------------------
18. Repair acceptance
--------------------------------------------------

每次 repair 后必须重新经过：

1. Mechanical Meaningfulness Gate
2. Interface/Attachment Gate
3. Collision Gate
4. Coarse Morphology Gate

如果 repair：

指标改善
但产生 meaningless geometry

→ REJECT

如果 morphology改善
但 mechanical hard gate恶化

→ ROLLBACK

--------------------------------------------------
19. 新增指标
--------------------------------------------------

A. Interface Knowledge Metrics

- knowledge retrieval coverage
- selected family distribution
- interface family change rate
- CUSTOM_INTERFACE rate
- interface physical validity

B. Mechanical Meaningfulness

新增：

Meaningful Geometry Rate

MGR =
generated geometry with valid mechanical role + provenance
/
all newly generated nontrivial geometry

目标接近：

100%

同时记录：

Meaningless Patch Count

目标：

0

C. Repair Arbiter

- Repair Scope Accuracy
- R0/R1/R2/R3/R4 distribution
- true replan rate
- repair success rate
- regression rate
- rollback rate

--------------------------------------------------
20. 尽量建立独立的 Scope GT
--------------------------------------------------

对于 4 个 repair pilot cases：

在运行 Arbiter 前，
人工/协议冻结：

expected_repair_scope

例如：

Case A -> R0
Case B -> R1/R2
Case C -> R3
Case D -> R4

只用于 evaluator。

不要把 expected scope 输入 Arbiter。

这样可以计算：

Repair Scope Accuracy。

--------------------------------------------------
21. 本轮不进入完整粗模型多轮修复
--------------------------------------------------

Try-5A.3 当前首先验证两个机制：

A:
Interface Knowledge Base 是否有用

B:
Repair Scope Arbiter 是否能选对修改粒度

暂时不要直接重新跑：

整机 3-round iterative repair loop

等这两个模块证明有效，
下一轮再把它们接回 coarse reconstruction loop。

--------------------------------------------------
22. 本轮禁止
--------------------------------------------------

不要加入：

- Try-5B Semantic Inventory
- fine Link detailing
- detailed gripper internals
- cosmetic modeling
- Robot B
- FEA
- dynamics
- control
- grasp simulation

--------------------------------------------------
23. Dataflow Audit
--------------------------------------------------

必须验证：

Knowledge retrieval
→ Interface Candidate
→ Interface Contract
→ CAD geometry

真实连接。

同时验证：

Repair diagnosis
→ Repair Scope
→ upstream spec change
→ CAD IR
→ FreeCAD

真实连接。

禁止：

有 JSON / markdown 输出，
但 CAD 完全没有消费。

--------------------------------------------------
24. GT Leakage
--------------------------------------------------

Knowledge Base 不能包含：

- Robot A GT CAD
- GT STEP geometry
- per-link GT dimensions
- exact GT interface

Repair 也不能读取 GT CAD。

GT 只用于：

- evaluator
- final visual comparison
- frozen repair-scope label for pilot

--------------------------------------------------
25. 代码开发规则
--------------------------------------------------

IMPORTANT:

直接修改现有 try5 主代码。

不要创建：

- try5A3_backend
- try5A3_scripts copy
- parallel pipeline
- compatibility layer for old implementation

开发阶段允许大胆重构。

但关键节点必须 Git commit。

建议：

Commit 1:
interface knowledge base + retrieval

Commit 2:
mechanical meaningfulness gate

Commit 3:
repair scope arbiter

Commit 4:
repair pilot + evaluation

历史结果不要覆盖即可。

--------------------------------------------------
26. 执行顺序
--------------------------------------------------

Phase 1
建立 Interface Knowledge Base

Phase 2
实现 Knowledge Retrieval / Candidate Ranking

Phase 3
运行 K0/K1 interface pilot

Phase 4
实现 Mechanical Meaningfulness Gate

Phase 5
实现 Repair Scope Arbiter

Phase 6
构造/冻结 4 类 repair pilot case

Phase 7
执行 R0/R1/R2/R3/R4 scope selection

Phase 8
执行一次 design-level repair

Phase 9
重新 deterministic evaluation

Phase 10
统一报告

--------------------------------------------------
27. 第一停点
--------------------------------------------------

先只完成：

Phase 1–4

即：

1. 建立第一版 Robot Interface Knowledge Base
2. 实现 candidate retrieval/ranking
3. 对 Robot A 的 joints 运行 K0/K1
4. 输出 interface family selection
5. 实现 Mechanical Meaningfulness Gate
6. 检查当前历史“小方块”式 patch 是否会被新 Gate 拒绝
7. 做 leakage / dataflow audit

完成后停止。

不要立即实现 Repair Scope Arbiter。

先向我汇报：

- 知识库包含哪些 interface family；
- 各 joint K0/K1 分别选择了什么；
- 哪些 joint 的 interface family发生变化；
- K1 是否更符合视觉和机械语义；
- BICR/gap/collision 是否变化；
- 是否出现 CUSTOM_INTERFACE；
- 历史无意义小方块是否被 Mechanical Meaningfulness Gate 拦截；
- Knowledge Base 是否真实影响 CAD；
- 是否存在 GT leakage。

我确认后再进入 Phase 5–10。