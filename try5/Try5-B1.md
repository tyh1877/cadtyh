# RobotCAD Try-5B.1
# Mechanically Constrained Link Refinement Pilot
# Visual Grounding + Executable Body Families + Semantic Topology + Selective Repair

继续直接修改现有 try5 主代码。

IMPORTANT：

1. Try-5A coarse-stage 已冻结，不得随意修改其机械定义；
2. Try-5B0 FAST evaluator 已通过，后续 refinement loop 默认使用 FAST_REPAIR_MODE + dirty-set；
3. 不创建新的平行 backend / pipeline / scripts 副本；
4. 直接修改现有 try5 implementation；
5. 历史结果可保留 snapshot，但代码保持 single evolving codebase；
6. 本轮只做 3 个 representative Links；
7. 不扩展到整机全部 Link；
8. 全部实验完成后统一汇报。

==================================================
0. 当前背景
==================================================

Try-5A 已完成并冻结：

- URDF kinematic authority
- Robot-level planning
- Interface Knowledge Base
- motion-aware Interface Contract
- interface-first modeling
- parent/child rigid groups
- BICR / attachment rules
- swept-clearance
- exact mechanical evaluator
- R0–R4 coarse repair
- Mechanical Meaningfulness Gate

Try-5A.5 已证明：

- 完整 Robot A 可从零生成；
- BICR = 100%
- moving joints JR3 = 100%
- final GCFR ≈ 91.4%
- no floating / accidental fusion / virtual solid / meaningless patch

但 geometry fidelity 很低：

- whole IoU ≈ 0.139
- silhouette IoU ≈ 0.249
- mean per-link IoU ≈ 0.023

当前主要问题：

1. Link body 大量退化为 cylinder / simple bar；
2. Robot Plan 中已有 central_web / dual_side_plate / tapered_beam 等语义，
   但没有真实编译成对应 CAD topology；
3. 相同 interface family 的 joint 外观高度模板化；
4. Link 内部真实机械结构仍然恢复不足。

Try-5B.1 的任务：

> 在不破坏机械骨架的情况下，
> 显著提高代表性 Link 的真实几何与机械结构表达。

==================================================
1. 核心研究问题
==================================================

RQ1：

Local Visual Grounding
+
Executable Body Family

是否能够显著解决 coarse Link 的 cylinder/primitive collapse？

RQ2：

Semantic Inventory
+
Mechanical Topology Graph

是否能够进一步恢复 Link 内部有机械意义的结构？

RQ3：

结构化 refinement / replanning
是否能提高 geometry fidelity，
同时保持：

- BICR
- JR3
- interface
- swept clearance
- GCFR

不显著退化？

==================================================
2. 实验对象：只选 3 个代表性 Link
==================================================

从 Robot A 自动选择三个代表性 physical Links：

A. Arm Carrier Link
代表：
- elongated body
- central web / dual side plate / tapered beam
- proximal/distal joint transition

B. Joint / Wrist Housing Link
代表：
- complex housing
- joint-local shape
- interface family相同但实例外观不同

C. Gripper / End-Side Complex Link
代表：
- 多个机械子结构
- rail / slider / jaw / fork / support 等复杂关系

要求：

三个 Link 类型尽量不同。

记录：

- link_id
- role
- why selected
- current coarse body family
- current geometry weakness

==================================================
3. 冻结机械约束
==================================================

对于每个 pilot Link，从 frozen Try-5A 读取并冻结：

- URDF frame
- parent/child joint
- joint origin
- joint axis
- joint limits
- Interface Contracts
- interface mating geometry
- rigid-group ownership
- protected interface regions
- swept-clearance regions
- neighbor collision context

Try-5B.1 允许修改：

- Link body geometry
- body family implementation
- section/profile
- structural topology
- local housing
- large openings/cutouts
- visible structural features

禁止直接修改：

- URDF
- joint semantics
- frozen interface frame
- parent/child rigid-group relation

如果发现 interface 本身必须重新设计：

输出：

ESCALATE_TO_COARSE_STAGE

不要在 B.1 中偷偷修改 frozen interface。

==================================================
4. Visual Evidence Pack
==================================================

对每个 pilot Link 建立：

VisualEvidencePack

只允许使用正式输入的：

- multi-view robot images
- engineering text
- frozen URDF context

禁止使用：

- GT STEP crop
- GT per-link mesh render
- GT CAD projection
- GT B-Rep segmentation

VisualEvidencePack 至少包含：

- global context views
- link-local crops
- proximal joint crops
- distal joint crops
- feature-level crops

并结构化记录：

- visible contour
- dominant section
- thickness cues
- symmetry
- open/closed structure
- fork/web/plate/housing cues
- curvature
- major recess/opening
- occlusion

每个 observation 标记：

VISIBLE
PARTIALLY_VISIBLE
OCCLUDED
UNCERTAIN

==================================================
5. Semantic Inventory
==================================================

在生成精细 CAD 前，
每个 Link 必须先输出：

LinkSemanticInventory

分为：

REQUIRED
OPTIONAL
UNCERTAIN

例如 arm link：

REQUIRED:
- proximal_joint_housing
- main_structural_carrier
- distal_joint_region

OPTIONAL:
- terminal_fork
- major_cutout
- reinforcement
- visible recess

UNCERTAIN:
- hidden bearing
- hidden actuator
- unclear boss

Gripper 可能包括：

- carriage
- rail_pair
- slider_pair
- jaw_pair
- pivot_group
- linkage
- working_gap

同时为每个 feature 设置 evidence level：

E1 = strong
E2 = moderate
E3 = weak

规则：

E3 默认不得直接生成实体，
除非后续获得更多证据。

==================================================
6. Mechanical Topology Graph
==================================================

Semantic Inventory 回答：

“有什么”。

Mechanical Topology Graph 回答：

“它们怎么组成”。

节点：

- structural feature
- housing
- web
- plate
- fork
- rail
- slider
- jaw
- linkage
- boss
- opening
等。

边至少支持：

- connected_to
- attached_to
- continues_into
- branches_into
- supports
- surrounds
- symmetric_with
- parallel_to
- coaxial_with
- separated_by_gap
- constrained_along

例如：

central_web
→ continues_into
→ distal_fork

fork_left
→ symmetric_with
→ fork_right

禁止只有 feature list，
没有 feature relation。

==================================================
7. Executable Body Family
==================================================

Try-5B.1 最重要的技术任务：

建立真正的：

Body Family
→ Executable Geometry Schema
→ CAD IR
→ FreeCAD

至少支持当前三个 pilot Link 所需 family，例如：

- central_web
- dual_side_plate
- straight_beam
- tapered_beam
- fork_body
- compound_profile_housing
- stepped_housing
- wrist_housing
- coarse_shell
- rail_carriage
- jaw_structure
- compound_link_body

不要为了覆盖数量强行实现所有 family。

==================================================
8. 禁止 silent family downgrade
==================================================

如果 Planner 输出：

body_family = central_web

实际 CAD 必须执行：

central_web

禁止：

central_web
→ unsupported
→ cylinder_between()

禁止：

tapered_beam
→ box

禁止：

fork_body
→ two unrelated rods

如果 family 尚未实现：

EXECUTABLE_FAMILY_MISSING

直接失败并记录。

新增：

Family Realization Rate

目标：

100%

==================================================
9. Body Family 必须真实展开
==================================================

例如 central_web 至少应包含：

- actual profile
- thickness
- proximal transition
- central web
- distal transition

dual_side_plate：

- left plate
- right plate
- spacing
- mechanically meaningful cross support if required

tapered_beam：

- different proximal/distal sections
- taper / loft / profile transition

fork_body：

- main body
- bifurcation start
- left fork
- right fork
- working gap

compound_profile_housing：

- main housing profile
- step/change in section
- major recess/opening
- interface transition

不能只靠 family 名称不同，
实际仍使用相同 primitive recipe。

==================================================
10. Joint-local Instance Geometry
==================================================

Knowledge Base 继续负责：

mechanical prior

Images 负责：

instance geometry

即使 J01/J02 都属于 fork-pin：

也不能默认：

- 相同 fork length
- 相同 housing diameter
- 相同 side-wall
- 相同 transition

必须根据各自 local visual evidence
生成不同实例参数与外形。

原则：

KB tells HOW IT WORKS.
Image tells WHAT THIS INSTANCE LOOKS LIKE.

==================================================
11. 三个实验条件
==================================================

使用：

F0
F1
F2

--------------------------------------------------
F0 — Frozen Coarse Baseline
--------------------------------------------------

直接使用 Try-5A.5 frozen coarse Link。

不重新生成。

代表当前：

mechanically valid
but geometrically crude

baseline。

--------------------------------------------------
F1 — Visual Grounding + Executable Body Family
--------------------------------------------------

增加：

- VisualEvidencePack
- true Body Family dispatch
- executable profile/section/schema
- joint-local instance geometry

暂时不加入完整 Semantic Topology repair。

目标：

解决：

- cylinder collapse
- generic bar
- identical housing templates

重点恢复：

- main profile
- section
- taper
- web/plate/fork
- housing envelope
- major opening

--------------------------------------------------
F2 — + Semantic Inventory + Mechanical Topology + Selective Repair
--------------------------------------------------

在 F1 基础上增加：

- Semantic Inventory
- E1/E2/E3 evidence
- Mechanical Topology Graph
- structured visual diagnosis
- hierarchical refinement
- selective regeneration

目标：

进一步恢复：

“机械子结构是否正确组成”。

==================================================
12. Refinement Repair Scope
==================================================

Try-5B 使用四级 refinement scope：

P0 PARAMETER_REFINE

适用于：
- thickness
- width
- length
- spacing
- taper
等轻微错误。

P1 FEATURE_REFINE

适用于：
- fork
- opening
- recess
- boss
- jaw
等单 feature错误。

P2 REGION_REPLAN

适用于：
- proximal / middle / distal region
- housing region
- gripper subregion
整体结构错误。

P3 WHOLE_LINK_REPLAN

适用于：
- body family错误
- topology错误
- structural organization错误。

==================================================
13. 禁止 direct CAD patch
==================================================

P1/P2/P3 必须：

Diagnosis
→ update Semantic/Topology/Body Spec
→ regenerate CAD IR
→ FreeCAD

禁止：

“缺一块”
→ FreeCAD.addBox()

禁止：

“视觉上差一点”
→ 随意加 cylinder/boss

所有 geometry 必须继续通过：

Mechanical Meaningfulness Gate。

==================================================
14. VLM 的角色
==================================================

VLM 在 Try-5B 中可以更加积极参与视觉诊断，

但不能作为最终 PASS judge。

输入：

- reference input views
- current Link renders
- semantic inventory
- topology graph
- mechanical constraints

输出必须结构化，例如：

{
  "link_id": "...",

  "missing": [
    "terminal_fork"
  ],

  "incorrect": [
    {
      "feature": "main_carrier",
      "issue": "cylindrical_but_reference_is_flattened_web"
    }
  ],

  "preserve": [
    "proximal_interface",
    "distal_interface"
  ],

  "suggested_scope": "P3_WHOLE_LINK_REPLAN"
}

禁止只输出：

"looks unlike reference"

==================================================
15. Mechanical Hard Gate
==================================================

每次 F1/F2 candidate 都必须重新检查：

- Interface frame unchanged
- BICR = 100%
- Physical Floating = 0
- Forbidden Fusion = 0
- Virtual Solid = 0
- Meaningless Patch = 0
- corresponding moving-joint JR3 not degraded
- swept-clearance preserved
- no new severe local collision

默认使用：

FAST_REPAIR_MODE
+
dirty-set

如果发生：

P2/P3
body topology / shape-family change

第一次接受前必须再运行：

Selective Exact local audit。

==================================================
16. Whole-Robot Mechanical Guard
==================================================

每个 pilot Link 最终 refinement 后：

重新放回完整 Robot A。

至少检查：

- relevant joint sweeps
- affected coupled configurations
- GCFR regression

允许局部 geometry refinement
带来极小变化，

但禁止明显破坏 frozen mechanical conclusions。

如果：

Geometry ↑
but
Mechanical Hard Gate FAIL

→ ROLLBACK

==================================================
17. Geometry Evaluation
==================================================

GT 只进入 evaluator。

Generator / VLM repair
不得读取 GT STEP / GT per-link mesh。

报告：

- per-link IoU
- nChamfer
- nHD95
- silhouette IoU
- bbox/major dimension error

重点比较：

F0
→ F1
→ F2

不要为了提高 evaluator 数值
把 GT 信息送给 Generator。

==================================================
18. Deterministic Semantic/Topology Evaluation
==================================================

因为只有3个 pilot Link，

请为 evaluator 建立一份人工冻结的：

Evaluator-Only Link Annotation

每个 Link 标注：

- required broad features
- optional broad features
- expected body family
- key relations

例如：

required:
- central_web
- proximal_housing
- distal_fork

relations:
- web connects proximal housing
- web branches into distal fork
- fork left/right symmetric

该 annotation：

只能 evaluator 读取。

Generator/VLM 禁止读取。

据此计算：

- Semantic Feature Precision
- Semantic Feature Recall
- Semantic Feature F1
- Relation Precision
- Relation Recall
- Relation F1
- Body Family Correctness

不使用 AI Judge。

==================================================
19. Family / Feature Metrics
==================================================

至少增加：

Family Realization Rate

planned family
vs
executed family

Feature Coverage

Required Feature Recall

Unsupported Feature Count

Topology Relation F1

Meaningless Geometry Count

目标：

Unsupported/Meaningless geometry
接近 0。

==================================================
20. Refinement Loop
==================================================

每个 Link：

最多 3 rounds。

流程：

Initial F1/F2 build
↓
Visual structured diagnosis
↓
Mechanical Hard Gate
↓
Geometry / Semantic Gate
↓
P0/P1/P2/P3 scope
↓
Update upstream design
↓
Partial rebuild
↓
FAST dirty-set evaluation
↓
Exact local audit if needed
↓
PASS / ROLLBACK / REPLAN

达到 gate 后：

FROZEN

不再继续修改。

==================================================
21. 停止 / Escalation
==================================================

如果连续两轮：

P0/P1 改善很小，

升级：

P2

如果仍然失败：

P3

P3 后仍无改善：

UNRESOLVED

不要无限迭代。

如果根因明确位于：

frozen interface design

则：

ESCALATE_TO_COARSE_STAGE

不要在 B.1 中偷偷解冻 Try-5A。

==================================================
22. Try-5B0 Evaluator 使用原则
==================================================

日常 refinement：

FAST_REPAIR_MODE
+
dirty-set

Topology / body-family改变：

FAST
+
Selective Exact local audit

三个 pilot Links 最终完成后：

FINAL_AUDIT_MODE

重新验证 frozen mechanical metrics。

不要每次都全量 Exact B-Rep。

==================================================
23. Dataflow Audit
==================================================

必须证明：

VisualEvidencePack
→ Body Family / Topology
→ Executable Schema
→ CAD IR
→ FreeCAD

真实消费。

尤其必须检查：

planner 选择：

central_web

最终 CAD 是否真的执行 central_web，

而不是隐藏回退 cylinder。

至少做 counterfactual：

- body family change
- profile change
- topology relation change

必须真实改变 CAD geometry。

==================================================
24. GT Leakage Audit
==================================================

Generator / VLM refinement 禁止读取：

- GT STEP
- GT B-Rep
- GT per-link mesh
- GT feature labels
- evaluator-only topology annotation
- GT dimensions

GT 只用于最终 evaluator。

正式 local crops
只能来自原始输入图像。

==================================================
25. 本轮不做什么
==================================================

不要：

- 精细化全部11个 Links
- Robot B
- detailed fastener reconstruction
- motor internals
- bearing internal detail
- very small holes
- tiny fillets/chamfers
- manufacturing tolerances
- FEA
- dynamics/load
- Try-5A redesign

本轮优先解决：

真实 Link 大结构与机械结构。

==================================================
26. 主要成功标准
==================================================

Try-5B.1 成功需要同时看到：

A. Representation

- Family Realization Rate ≈ 100%
- 不再大规模 cylinder/primitive collapse

B. Geometry

F1/F2 相比 F0：

- per-link IoU明显提高
- silhouette明显提高
- Chamfer/HD95整体改善

不强制预设过高绝对阈值，
重点看稳定相对提升。

C. Structure

- Semantic Feature F1提高
- Relation F1提高
- Unsupported feature低
- Meaningless Patch = 0

D. Mechanics

- BICR保持100%
- relevant JR3保持
- interface保持
- no forbidden fuse
- GCFR无严重回归

==================================================
27. 结果解释
==================================================

如果：

F0 → F1 明显改善

说明：

Executable Body Family
+
Local Visual Grounding

有效。

如果：

F1 → F2 继续改善

说明：

Semantic Inventory
+
Mechanical Topology
+
Structured Repair

有额外价值。

如果：

Geometry改善但 mechanics下降

说明：

mechanical constraint preservation
仍不足。

如果：

Mechanics稳定但 geometry不改善

说明主要瓶颈已转变为：

visual → profile/section/topology grounding

而不是：

URDF / interface / FreeCAD。

==================================================
28. 输出
==================================================

至少保存：

- pilot_link_selection
- VisualEvidencePacks
- SemanticInventories
- MechanicalTopologyGraphs
- BodyFamilySpecs
- ExecutableGeometrySchemas
- F0/F1/F2 CAD
- per-round renders
- repair contracts
- family execution audit
- semantic/topology metrics
- geometry metrics
- FAST mechanical metrics
- final Exact audit
- leakage/dataflow audit

==================================================
29. 代码开发原则
==================================================

继续直接修改现有 try5 主代码。

不要复制：

- evaluator
- backend
- pipeline

可以对 body-family geometry implementation
进行较大重构。

这正是 Try-5B 的主要开发对象。

建议 Git 节点：

1. visual evidence + pilot selection
2. executable body-family dispatch
3. semantic inventory + topology graph
4. refinement loop
5. final pilot evaluation

==================================================
30. 最终报告必须回答
==================================================

完成全部实验后统一汇报：

1. 选择了哪3个 Link？为什么？
2. F0 当前各 Link 是怎样建模的？
3. 哪些存在 cylinder/primitive collapse？
4. VisualEvidencePack 包含什么？
5. 三个 Link 的 Semantic Inventory 是什么？
6. Mechanical Topology Graph 是什么？
7. F1 分别选择什么 body family？
8. 是否真实执行这些 family？
9. Family Realization Rate 是多少？
10. 是否仍发生 silent downgrade？
11. F0/F1/F2 的 IoU是多少？
12. nChamfer / nHD95如何变化？
13. silhouette如何变化？
14. 哪个 Link改善最大？
15. 哪个 Link最困难？
16. Semantic Feature F1 如何变化？
17. Relation F1 如何变化？
18. 是否出现 unsupported features？
19. 是否出现 meaningless geometry？
20. 总共进行了几轮 refinement？
21. P0/P1/P2/P3分别触发多少？
22. 是否发生真正 Whole-Link Replan？
23. 是否发生 rollback？
24. VLM主要发现了哪些错误？
25. 是否仍出现 appearance-driven hallucinated components？
26. BICR 是否保持100%？
27. relevant JR3 是否保持？
28. interface是否被破坏？
29. GCFR是否明显下降？
30. FAST evaluator 在实际 refinement 中耗时如何？
31. topology改变后是否进行了 Exact local audit？
32. GT leakage 是否为0？
33. 当前 body-family generator 是否仍是主要瓶颈？
34. 当前主要瓶颈变成什么？
35. 是否值得进入 Try-5B.2 all-link refinement？

==================================================
31. 最终核心判断
==================================================

本轮不是验证：

“AI能不能再多画几个细节。”

而是验证：

> 在 Try-5A 已经建立的机械正确设计空间中，
> AI 能否利用局部视觉证据，
> 将粗糙的 placeholder Link
> 转换成具有真实 body family、
> 正确内部机械拓扑、
> 更接近参考外形的 editable CAD，
> 同时不破坏已经验证的机械可运动性。

请完整完成 Try-5B.1 后再统一汇报。
不要提前进入 Try-5B.2。