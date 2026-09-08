# RobotCAD Try-5A.2
# Quality-Gated Iterative Coarse Reconstruction
# Pose-Aware Local Repair + Progressive Freezing

Try-5A 与 Try-5A.1 已完成。

已知：

Try-5A：
- Interface-first A2 将 Connected Joint Rate 提高到 100%
- Floating Link Rate 降到 0
- Mean interface gap = 0
- nominal-radius mismatch = 0
- excessive axial penetration = 0
- 但 coarse geometry 未改善
- collision-aware body planning 尚未建立

Try-5A.1：
- C1 collision-aware body planning 真实进入 CAD
- True collision events：181 -> 130
- Total intersection volume：554812.5 -> 313085.5 mm^3
- 接口全部保持
- 但 collision-free sweep pose rate 仍为 0%
- C2 morphology recovery 导致 collision volume rebound
- 当前仍存在：
  1. body-interface 实体连接检查不足
  2. virtual link 被错误实体化
  3. global body scaling 修复空间过粗
  4. 缺少真正自动的多轮 selective repair loop

因此 Try-5A.2 的目标是：

> 在冻结正确 URDF skeleton 和 shared interfaces 的前提下，
> 建立一个 deterministic-gate-first、
> pose-aware、
> region-level、
> selective、
> iterative coarse repair loop，
> 让机械臂从“接口能接但仍大量碰撞”
> 推进到“接口正确，并开始具备真实 collision-free motion”。

本轮不进入 Try-5B。

--------------------------------------------------
1. 核心研究问题
--------------------------------------------------

RQ1：

Quality-Gated Iterative Repair
是否比 Try-5A.1 的 one-shot body replan
更有效地降低真实碰撞？

RQ2：

Pose-indexed + region-level local repair
是否比 whole-link/global scaling
更有效地解决碰撞，
同时减少 geometry regression？

RQ3：

在 mechanical hard gates 全部冻结之后，
VLM-assisted coarse morphology refinement
是否能改善视觉粗形态，
而不重新破坏接口与运动可用性？

--------------------------------------------------
2. 实验对象
--------------------------------------------------

继续只使用：

Robot A = Try-5A / Try-5A.1 开发机器人。

不要：

- Robot B
- transfer evaluation
- 新数据集
- 新机械臂

Try-5A.2 仍然是 development experiment。

--------------------------------------------------
3. 起始条件
--------------------------------------------------

定义：

D0 = frozen Try-5A.1 C1

原因：

C1 相比 C0：

- collision events 更少
- intersection volume 最低
- interfaces preserved

C2 的 morphology replan 导致 collision rebound，
因此不要从 C2 开始。

D0 必须原样冻结，
不能重新调参。

--------------------------------------------------
4. 正式实验条件
--------------------------------------------------

只做：

D0
D1
D2

--------------------------------------------------
D0 — Frozen C1 Baseline
--------------------------------------------------

直接复用 Try-5A.1 C1。

特点：

- interface-first
- collision-aware
- one-shot body replan
- no iterative repair

作为 baseline。

--------------------------------------------------
D1 — Deterministic Quality-Gated Iterative Coarse Repair
--------------------------------------------------

流程：

D0
↓
Deterministic Hierarchical Gates
↓
Failure Localization
↓
Pose-Indexed Local Repair Contract
↓
Selective Region / Link Rebuild
↓
Exact Collision Re-evaluation
↓
PASS / REPAIR / REPLAN / FROZEN
↓
repeat

最多 3 个 repair rounds。

D1：

禁止使用 VLM morphology feedback。

只允许：

- body-interface attachment repair
- local collision repair
- local body section replan
- pose-aware clearance repair
- regional structural replan

目的：

单独验证 deterministic iterative repair 是否有效。

--------------------------------------------------
D2 — D1 + VLM-Assisted Coarse Morphology Refinement
--------------------------------------------------

只有当 D1 已满足 mechanical hard gates 后，
才允许进入 D2。

D2 在 D1 final model 上增加：

- major silhouette
- broad thickness
- taper direction
- major body proportion
- coarse housing profile

VLM 只能做 coarse morphology diagnosis。

每一次 VLM-triggered modification 后：

必须重新通过：

- Kinematic Gate
- Interface/Attachment Gate
- Collision Gate

如果 morphology 改善，
但 collision / attachment 明显退化：

自动 rollback。

--------------------------------------------------
5. 先修复两个 evaluator 漏洞
--------------------------------------------------

正式运行 D1 前，
必须先修正 Try-5A.1 中暴露出的两个问题。

--------------------------------------------------
5.1 Physical Body-Interface Attachment Gate
--------------------------------------------------

过去：

Connected Joint Rate = 100%

主要证明：

- frame
- axis
- port parameters

一致。

但不能证明：

interface carrier
真的和本 Link body 连成机械实体。

新增：

# Internal Body-Interface Connectivity Rate
BICR

定义：

BICR =
physically attached physical interface carriers
/
all physical interface carriers

对于每个 physical Link 的接口 carrier：

必须满足至少一种允许条件：

A. 与主 body Boolean union 为同一 solid；

B. 与主 body 有真实非零接触面积，
且该连接被显式声明为 rigid multi-body structure；

C. 通过明确的 rigid connector geometry 连接。

禁止：

interface carrier 与 body 完全悬空，
但只因为 frame 一致就 PASS。

记录：

- body-interface minimum distance
- contact area
- same-solid / multi-solid state
- connectivity path

目标：

BICR = 100%

--------------------------------------------------
5.2 Virtual Link Filtering
--------------------------------------------------

所有 URDF Link 增加：

link_realization_type:

- physical_body
- rigid_subassembly
- interface_only
- virtual_frame

只有：

physical_body
rigid_subassembly

可以进入：

- FreeCAD solid generation
- STEP/STL
- render
- geometry evaluator
- collision evaluator

interface_only：

只在需要时保留 interface metadata / helper object，
默认不生成独立实体。

virtual_frame：

只保留坐标系 / App::FeaturePython / metadata。

禁止生成实体。

新增指标：

Spurious Virtual Geometry Count

目标：

0

特别检查：

tool_center_frame / marker 类 Link。

--------------------------------------------------
6. Hierarchical Deterministic Gates
--------------------------------------------------

粗阶段必须按以下顺序验证：

Gate 1
Kinematic Gate

Gate 2
Interface / Attachment Gate

Gate 3
Collision / Clearance Gate

Gate 4
Coarse Morphology Gate

高优先级 Gate 未通过时：

禁止进入低优先级修复。

--------------------------------------------------
7. Gate 1 — Kinematic Gate
--------------------------------------------------

检查：

- URDF topology
- parent-child mapping
- joint axis
- joint origin
- joint limits
- canonical pose
- FK consistency
- mimic relation

这层以 sanitized URDF 为 authority。

Try-5A 已基本通过，
因此原则上冻结。

如无异常：

KINEMATIC = FROZEN

--------------------------------------------------
8. Gate 2 — Interface / Attachment Gate
--------------------------------------------------

拆成三部分。

A. Interface Frame Correctness

- axis
- center
- orientation
- radius / envelope
- URDF frame consistency

B. Internal Body-Interface Connectivity

- body ↔ parent interface carrier
- body ↔ child interface carrier
- BICR

C. Parent-Child Physical Assembly

- intended gap
- contact
- clearance
- excessive penetration
- mating relation

只有：

Frame correct
+
Body attached
+
Parent/child physically valid

才算：

INTERFACE_GATE = PASS

--------------------------------------------------
9. Gate 3 — Exact Collision / Clearance Gate
--------------------------------------------------

继续使用：

Broad phase:
AABB / OBB

Narrow phase:
B-Rep Boolean Common
或 equivalent exact intersection

禁止：

AABB overlap = collision

正式 repair feedback 只使用 narrow-phase result。

每个 collision event 至少记录：

- pose_id
- joint configuration
- link_i
- link_j
- region_i
- region_j
- collision type
- exact intersection volume
- minimum clearance if available

--------------------------------------------------
10. Collision 分类
--------------------------------------------------

至少分类：

EXPECTED_INTERFACE_CONTACT

ADJACENT_UNINTENDED_COLLISION

NONADJACENT_COLLISION

MOTION_INDUCED_COLLISION

EXPECTED_INTERFACE_CONTACT：

不作为 repair target。

其它三类：

进入 collision repair queue。

--------------------------------------------------
11. Region-Level Link Representation
--------------------------------------------------

不要再只允许 whole-link scaling。

每个 physical Link 至少拆为：

- proximal_interface_region
- proximal_body_region
- middle_body_region
- distal_body_region
- distal_interface_region

复杂 Link 可增加：

- left_side_region
- right_side_region
- upper_region
- lower_region
- wrist_cluster_region
- gripper_support_region

接口区域默认：

FROZEN / PROTECTED

--------------------------------------------------
12. Pose-Indexed Exclusion Volume
--------------------------------------------------

对于每个 collision-causing region，
根据实际失败 pose 建立：

pose_indexed_exclusion_region

例如：

{
  "link_id": "L04",
  "region": "distal_body_region",
  "collision_with": "L07",

  "critical_poses": [
    {
      "pose_id": "q_041",
      "joint_state": {...},
      "intersection_volume_mm3": 3280
    }
  ],

  "avoid_volume": {...},

  "preferred_escape_direction": "-Y",

  "protected_regions": [
    "proximal_interface",
    "distal_interface"
  ]
}

修复时必须消费这个信息。

不要只告诉 Agent：

"L04 collides with L07"

--------------------------------------------------
13. Pose-Aware Local Repair Contract
--------------------------------------------------

每个 repair 必须结构化。

例如：

{
  "repair_id": "...",
  "link_id": "L04",
  "region": "distal_body_region",

  "failure_type": "MOTION_INDUCED_COLLISION",

  "collision_with": "L07",

  "critical_poses": [...],

  "current_intersection_volume_mm3": ...,

  "repair_action": "LOCAL_SECTION_OFFSET",

  "parameter_targets": {
    "local_width": "decrease",
    "section_center_y": "shift_negative"
  },

  "protected": [
    "J04_interface",
    "J05_interface",
    "middle_body_region"
  ],

  "must_preserve": [
    "body-interface connectivity",
    "link centerline continuity"
  ]
}

--------------------------------------------------
14. Repair Action Vocabulary
--------------------------------------------------

限制为少量可执行动作：

LOCAL_SECTION_SHRINK

LOCAL_SECTION_EXPAND

LOCAL_SECTION_OFFSET

LOCAL_PROFILE_REPLACE

LOCAL_TAPER_CHANGE

LOCAL_BODY_CORRIDOR_REPLAN

LOCAL_TRANSITION_REPLAN

ATTACHMENT_UNION_REPAIR

BODY_REGION_REPLAN

FULL_BODY_REPLAN

不要自由生成大量新 action。

--------------------------------------------------
15. Repair 层级
--------------------------------------------------

错误按层级 routing：

KINEMATIC_FAIL
→ FRAME_REPAIR

INTERFACE_FRAME_FAIL
→ INTERFACE_REPLAN

BODY_ATTACHMENT_FAIL
→ ATTACHMENT_UNION_REPAIR

LOCAL_COLLISION_FAIL
→ LOCAL_BODY_REPAIR

PERSISTENT_COLLISION_FAIL
→ BODY_REGION_REPLAN

GLOBAL_BODY_FAILURE
→ FULL_BODY_REPLAN

COARSE_MORPHOLOGY_FAIL
→ MORPHOLOGY_REPLAN

不要把所有问题交给一个通用 Repair Agent。

--------------------------------------------------
16. Progressive Freezing
--------------------------------------------------

状态粒度至少到：

- Joint
- Interface
- Link
- Region

例如：

J01:
FROZEN

L01:
  proximal_interface = FROZEN
  lower_body_region = REPAIR
  middle_body_region = FROZEN
  distal_interface = FROZEN

Repair 只能修改：

REPAIR / REPLAN

状态对象。

禁止重建 FROZEN region。

--------------------------------------------------
17. Selective Partial Rebuild
--------------------------------------------------

每轮不要重建整台机器人。

流程：

Evaluate Whole Robot
↓
Identify failing joint/link/region
↓
Generate repair contracts
↓
Rebuild only affected Link/Region
↓
Reload Assembly
↓
Re-evaluate affected collision pairs
↓
Run global sanity check

例如只有：

L00–L01
L04–L07

失败：

不要调用 Codex 重建 L02/L03 等已通过 Link。

--------------------------------------------------
18. D1 Iteration Loop
--------------------------------------------------

Round 0：

D0 frozen C1

然后：

Round 1
Round 2
Round 3

每一轮：

1. deterministic gates
2. failure localization
3. build repair queue
4. freeze passed regions
5. selective repair
6. FreeCAD partial rebuild
7. exact re-evaluation
8. rollback regression
9. update blackboard

如果提前全部满足 hard gate：

立即停止。

不要强制跑 3 轮。

--------------------------------------------------
19. Regression Protection
--------------------------------------------------

每次 repair 后检查：

- frozen interface unchanged
- BICR not reduced
- new collision not introduced in unrelated region
- collision volume in repaired pair not significantly worse
- previously PASS region still PASS

若 regression：

rollback 当前 candidate。

记录：

Regression Count
Rollback Count

--------------------------------------------------
20. Stagnation Gate
--------------------------------------------------

如果同一 region 连续两轮：

collision volume 改善 < epsilon_collision

且：

collision event count 不下降

则：

LOCAL_BODY_REPAIR
→ BODY_REGION_REPLAN

如果仍无改善：

UNRESOLVED

不要无限循环。

epsilon_collision：

在 Robot A dev 阶段冻结。

--------------------------------------------------
21. Gate 4 — Coarse Morphology
--------------------------------------------------

只有 D1 mechanical hard gates 基本通过后，
D2 才检查 coarse morphology。

确定性指标：

- whole robot IoU
- silhouette IoU
- bbox error
- per-link IoU
- nChamfer
- nHD95
- major dimension ratio

VLM 只辅助判断：

- body too thick/thin
- taper wrong
- shoulder housing family wrong
- wrist envelope oversized
- upper-arm direction / profile明显错误

--------------------------------------------------
22. VLM Morphology Contract
--------------------------------------------------

VLM 不允许自由发明 Feature。

每条 suggestion 必须引用：

- link_id
- existing body region
- existing coarse body family
- visual evidence views

例如：

{
  "link_id": "L02",
  "region": "middle_body_region",
  "issue": "body_too_thick",
  "evidence_views": ["side", "iso"],
  "recommended_action": "LOCAL_SECTION_SHRINK",
  "confidence": 0.88
}

禁止：

"Add a small cylinder here"

如果：

mechanical_role unknown
或
evidence weak

输出：

UNSUPPORTED_VISUAL_SUGGESTION

不执行。

--------------------------------------------------
23. D2 Rollback Rule
--------------------------------------------------

D2 每次 morphology modification 后：

重新跑：

Kinematic Gate
Interface Gate
Attachment Gate
Collision Gate

如果 morphology improves，
但出现以下任一情况：

- Connected Joint Rate下降
- BICR下降
- Floating Link出现
- collision event明显增加
- intersection volume明显反弹
- sweep-free rate下降

则：

ROLLBACK

避免重演 Try-5A.1 C2。

--------------------------------------------------
24. D1/D2 的 Quality Gate
--------------------------------------------------

不要用单一综合分数。

Mechanical hard gate 建议：

- Connected Joint Rate = 100%
- Floating Link Rate = 0
- BICR = 100%
- Spurious Virtual Geometry Count = 0
- interface gap within tolerance
- no excessive interface penetration
- joint frame error within tolerance

Collision target：

开发阶段不要求一次达到 100% collision-free sweep，
但必须：

- collision events clearly lower than D0
- intersection volume clearly lower than D0
- Sweep-Free Pose Rate > 0

尤其：

Sweep-Free Pose Rate 从 0% 提升到 >0%

作为 Try-5A.2 的关键目标。

--------------------------------------------------
25. 指标
--------------------------------------------------

A. Mechanical Hard Metrics

- Connected Joint Rate
- Floating Link Rate
- BICR
- Interface Gap
- Interface Penetration
- Joint Axis Error
- Joint Origin Error
- Spurious Virtual Geometry Count

B. Collision Metrics

- True Collision Event Count
- Collision Pair Count
- Adjacent Unintended Collision Count
- Nonadjacent Collision Count
- Motion-Induced Collision Count
- Total Intersection Volume
- Max Intersection Volume
- Minimum Clearance
- Collision-Free Sweep Pose Rate
- Collision-Free Sample Rate

C. Geometry Metrics

- Whole Robot IoU
- Whole Silhouette IoU
- per-link IoU
- nChamfer
- nHD95
- bbox error
- reach error

D. Iteration Metrics

- repair rounds
- active link count per round
- active region count per round
- early frozen link ratio
- frozen region ratio
- repair success rate
- regression rate
- rollback count
- unresolved regions
- Codex calls
- execution time

--------------------------------------------------
26. 重点 Collision Regions
--------------------------------------------------

根据 Try-5A.1 优先关注：

A. L00–L01
base / shoulder

B. L04–L08
wrist / gripper cluster

但不能 hard-code 只修这些。

正式 Scheduler 必须基于 evaluator 自动发现 repair target。

它们只是 expected stress regions。

--------------------------------------------------
27. 每轮 Artifact
--------------------------------------------------

保存：

round_0/
round_1/
round_2/
round_3/

每轮至少：

- assembled.FCStd
- assembled.step
- assembled.stl
- renders/
- collision_pairs.csv
- collision_heatmap/
- repair_queue.json
- repair_contracts/
- part_state.json
- region_state.json
- metrics.json
- rollback_log.json

--------------------------------------------------
28. 必须输出可视化
--------------------------------------------------

至少生成：

Round 0 | Round 1 | Round 2 | Round 3

统一视角 robot renders。

额外建议：

- collision heatmap
- repaired regions highlight
- frozen regions highlight

并输出曲线：

Collision Event Count vs Round

Intersection Volume vs Round

Sweep-Free Pose Rate vs Round

Whole IoU vs Round

Active Repair Regions vs Round

--------------------------------------------------
29. Dataflow Audit
--------------------------------------------------

必须证明：

collision evaluator
→ repair contract
→ body spec
→ CAD IR
→ FreeCAD geometry

真实连接。

至少做 counterfactual test：

改变某个：

pose-indexed exclusion
或
repair target local section

应导致对应 region CAD 真实改变。

禁止出现：

repair_contract.json 生成了，
但 CAD 仍按旧 body recipe 执行。

--------------------------------------------------
30. GT Leakage
--------------------------------------------------

Generator / Repair 不能读取：

- GT STEP
- GT per-link mesh
- GT B-Rep
- GT dimensions
- GT collision-free geometry
- GT Feature Tree

GT 只进入：

geometry evaluator
最终 reference render comparison

Collision repair 必须基于：

generated geometry
+
URDF
+
deterministic collision result

不是 GT CAD。

--------------------------------------------------
31. 本轮禁止加入
--------------------------------------------------

不要加入：

- Try-5B Semantic Inventory
- fine Feature Graph
- gripper detailed linkage reconstruction
- detailed holes
- fillet/chamfer detail
- cosmetic feature hallucination
- Robot B
- FEA
- dynamics
- torque
- control
- grasp simulation

--------------------------------------------------
32. 结果比较
--------------------------------------------------

核心比较：

D0 vs D1

回答：

Quality-Gated
+
Pose-Aware
+
Region-Level
+
Iterative Repair

是否比 one-shot C1 更有效？

D1 vs D2

回答：

在 mechanical constraints 已稳定的情况下，
VLM-assisted morphology
是否能提高 coarse fidelity，
而不重新引入 collision？

--------------------------------------------------
33. 关键成功模式
--------------------------------------------------

理想结果：

D0:
interfaces correct
collision still high
sweep-free = 0

D1:
interfaces preserved
BICR = 100%
virtual solids = 0
collision strongly reduced
sweep-free > 0

D2:
mechanical metrics preserved
collision remains low
geometry / silhouette improves

--------------------------------------------------
34. 失败解释
--------------------------------------------------

如果 D1 仍：

Sweep-Free Pose Rate = 0

即使多轮 local repair 后也没有改善：

不要继续增加 repair rounds。

应判断瓶颈位于：

- coarse body representation
- interface envelope design
- local free-space representation
- articulated-body spatial planning

并建议重新设计 representation。

如果 D1 有效但 D2 失败：

说明：

Mechanical repair 有效，
但视觉 morphology refinement
仍然会破坏机械可用性。

后续 Try-5B 必须严格受 mechanical constraints 控制。

--------------------------------------------------
35. 进入 Try-5B 的建议条件
--------------------------------------------------

只有当至少满足：

- Connected Joint Rate = 100%
- Floating Link Rate = 0
- BICR = 100%
- Spurious Virtual Geometry Count = 0
- interface metrics stable
- exact collision显著低于 D0
- Sweep-Free Pose Rate > 0
- coarse morphology 不显著崩坏

才建议进入：

Try-5B
Semantic-Inventory-Guided Link Detailing

--------------------------------------------------
36. 输出目录
--------------------------------------------------

experiments/try5A_2/

  protocol/
    try5A_2_protocol.md

  D0/
  D1/
  D2/

  evaluator/
  body_attachment/
  virtual_link_filter/
  pose_exclusion/
  body_regions/
  repair_contracts/
  blackboard/
  assemblies/
  collision_analysis/
  renders/

results/try5A_2/

  mechanical_metrics.csv
  collision_metrics.csv
  geometry_metrics.csv
  iteration_metrics.csv
  per_round_metrics.csv
  per_pair_collision.csv
  per_region_repair.csv

  try5A_2_report.md

--------------------------------------------------
37. 最终报告必须回答
--------------------------------------------------

1. D0/D1/D2 的主要指标是什么？
2. Connected Joint Rate 是否始终保持 100%？
3. BICR 是否达到 100%？
4. Try-5A.1 中发现的悬空 interface carrier 是否被真实修复？
5. virtual link 实体是否全部移除？
6. Spurious Virtual Geometry Count 是否为 0？
7. D1 一共运行几轮？
8. 每轮修了哪些 Link / Region？
9. 哪些区域提前 FROZEN？
10. True Collision Event Count 每轮如何变化？
11. Intersection Volume 每轮如何变化？
12. Sweep-Free Pose Rate 是否从 0% 提升？
13. L00–L01 是否改善？
14. L04–L08 wrist/gripper cluster 是否改善？
15. 哪些 collision 最难解决？
16. 有多少 repair candidate 被 rollback？
17. Progressive Freezing 是否工作？
18. Region-level repair 是否优于 whole-link scaling？
19. D1 geometry 是否严重恶化？
20. D2 是否改善 morphology？
21. D2 是否重新引入 collision？
22. VLM suggestion 中是否出现 unsupported feature hallucination？
23. Dataflow audit 是否证明 repair contract 真正影响 CAD？
24. FreeCAD 是否仍不是瓶颈？
25. 当前最大瓶颈是什么？
26. 是否满足进入 Try-5B 的条件？

--------------------------------------------------
38. 开发顺序
--------------------------------------------------

严格按以下顺序：

Phase 1
修 Physical Attachment Evaluator

Phase 2
修 Virtual Link Filtering

Phase 3
重新评价 D0

Phase 4
建立 region-level body representation

Phase 5
建立 pose-indexed collision localization

Phase 6
建立 selective repair scheduler

Phase 7
运行 D1 Round 1

Phase 8
Evaluate → repair → repeat
最多 Round 3

Phase 9
冻结 D1 final mechanical state

Phase 10
如 D1 满足 hard gate，
运行 D2 morphology refinement

Phase 11
统一评价

Phase 12
输出 report

--------------------------------------------------
39. 第一停点
--------------------------------------------------

请现在先完成：

Phase 1–3

即：

1. 实现真实 Body-Interface Attachment Gate
2. 实现 BICR
3. 修复 virtual link filtering
4. 移除所有不应实体化的 tool/frame markers
5. 重新评价 frozen D0
6. 区分：
   - logical interface connectivity
   - physical body-interface connectivity
7. 输出修正后的 D0：
   - Connected Joint Rate
   - BICR
   - Floating Link Rate
   - Virtual Geometry Count
   - exact collision baseline
   - sweep-free rate

完成后停止。

不要立即开发 iterative repair。

先向我汇报：

- Try-5A/A.1 旧 evaluator 高估了哪些指标；
- 哪些 link/interface 实际悬空；
- virtual solids 有哪些；
- 修正 evaluator 后 D0 的真实 mechanical validity；
- 是否具备进入 Phase 4–8 的条件。

我确认后再继续。