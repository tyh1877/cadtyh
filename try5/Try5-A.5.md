# RobotCAD Try-5A.5
# End-to-End Whole-Robot Motion-Realizable Coarse Reconstruction
# From Scratch + Whole-Robot Iterative Repair

继续直接修改现有 try5 主代码。

IMPORTANT：

1. 不创建新的平行 Try-5A.5 pipeline/backend/scripts 副本；
2. 直接修改当前 try5 主实现；
3. 开发阶段允许重构和删除旧实现；
4. 使用 Git commit 保存关键节点；
5. 历史实验结果不要覆盖；
6. 本轮从零运行完整 coarse reconstruction；
7. 中间不要停下来等待确认；
8. 所有开发、实验、修复、验证完成后一次性汇报。

==================================================
0. Try-5A.5 的定位
==================================================

Try-5A.4 已经证明：

在 J01/J02/J03 三个 pilot joints 上：

- URDF FK 可正确驱动 CAD rigid groups；
- Parent/Child attachment 可达到 100%；
- BICR 可达到 100%；
- parent/child 保持独立刚体；
- Knowledge Base 可真实决定 interface realization；
- motion-aware Interface Contract 有效；
- swept clearance 可真实进入 CAD planning；
- Repair Scope Arbiter 可执行 R2_BODY_REGION_REPLAN；
- M2 collision-free pose rate = 100%；
- M2 JR3 = 100%；
- exact swept collision = 0；
- 三个 pilot joints 达到 K1/K2/K3。

但：

Try-5A.4 只是三关节 pilot，
并没有证明整台 Robot A
可以从零完成 coarse reconstruction。

Try-5A.5 的目标是：

> 将已经验证的局部机制扩展到 Robot A
> 全部 physical Links / Joints，
> 从正式输入重新开始，
> 生成完整 coarse CAD robot，
> 并运行整机运动验证和分层迭代修复。

==================================================
1. 核心研究问题
==================================================

RQ1：

当前 Try-5 架构能否在不复用旧 CAD 答案的情况下，
从：

Images + Engineering Text + Sanitized URDF

生成完整 Robot A coarse CAD？

RQ2：

Try-5A.4 的：

Knowledge-Guided Joint Realization
+
Rigid Groups
+
Motion-Aware Interfaces
+
Swept Clearance

能否扩展到全部 physical joints？

RQ3：

每个 Joint 单独可运动，
是否能够进一步形成：

whole-robot coupled collision-valid motion？

RQ4：

R0–R4 Hierarchical Repair
能否在整机范围自动判断：

参数修复
vs
局部重规划
vs
Whole-Link Replan
vs
Interface Pair Replan？

RQ5：

能否在提高机械正确性的同时，
避免 coarse geometry 退化成：

- 极细杆
- 过小 body
- 无意义 connector
- metric-gaming geometry？

==================================================
2. 实验对象
==================================================

仍然只使用：

Robot A

不要：

- Robot B
- transfer experiment
- Try-5B detailed modeling

Try-5A.5 是 Robot A 的完整 coarse-stage integration experiment。

==================================================
3. 真正“从零开始”的定义
==================================================

本轮 Generator 初始只能读取：

1. Multi-view Images
2. Engineering Text
3. Sanitized URDF
4. 冻结后的通用 Robot Knowledge Base
5. 通用 RobotCAD Skills / evaluator / backend

禁止复用作为生成答案：

- Try-5A A2 CAD
- K1 CAD
- Try-5A.4 M0/M1/M2 CAD
- 历史 Interface Contracts
- 历史 LinkCoarseSpecs
- 历史 rigid-group geometry
- 历史 swept STEP
- 历史 repair contracts
- 历史 body parameters
- 针对 Robot A 人工调好的 connector 参数

原则：

Knowledge can be reused.
Answers cannot be reused.

可以读取旧代码逻辑，
但所有 Robot A design state
必须从正式输入重新生成。

==================================================
4. 正式输入
==================================================

Generator Input：

- multi-view robot images
- engineering text
- sanitized URDF

Sanitized URDF 保留：

- links
- joints
- parent/child
- joint type
- origin
- axis
- limits
- mimic relation

删除：

- visual geometry
- collision geometry
- mesh
- CAD
- inertial/material identity
- GT geometry

GT STEP / GT meshes：

仅用于最终 evaluator。

==================================================
5. 第一阶段：重新建立 Kinematic Skeleton
==================================================

从 sanitized URDF 确定性重新生成：

- Link list
- Joint list
- physical/virtual classification
- parent-child graph
- FK tree
- joint frames
- canonical pose
- joint limits
- mimic mapping
- end-effector / tool frames

不能读取历史生成的 skeleton JSON 作为答案。

重新执行验证：

- frame completeness
- transform consistency
- FK consistency
- axis/origin consistency

URDF 始终作为 kinematic authority。

==================================================
6. Link realization classification
==================================================

每个 URDF link 必须自动分类：

- physical_body
- rigid_subassembly
- interface_only
- virtual_frame

要求：

physical_body / rigid_subassembly
→ CAD solid

interface_only
→ metadata/helper only unless physically required

virtual_frame
→ frame only

禁止 virtual tool frame
再次生成物理小圆柱等实体。

目标：

Spurious Virtual Geometry Count = 0

==================================================
7. 第二阶段：Whole-Robot Assembly Planning
==================================================

在任何 Link CAD 生成前，
重新建立：

Robot Assembly Plan

对全部 physical Links 规划：

- mechanical role
- proximal joint
- distal joint(s)
- principal direction
- approximate envelope
- interface-to-interface span
- coarse body family
- major structural path
- expected articulation context
- neighbor exclusion context

Robot Plan 不能只是描述文字。

它必须真实约束后续：

LinkCoarseSpec
和 CAD geometry。

==================================================
8. 第三阶段：Knowledge-Guided Joint Planning
==================================================

对所有 URDF joints：

利用：

URDF semantics
+
parent/child roles
+
visual evidence
+
Robot Interface Knowledge Base

重新选择 interface family。

当前知识库优先支持：

- fork_pin_interface
- coaxial_rotary_interface
- nested_rotary_housing
- rail_slider_interface
- flange_interface
- planar_mount_interface
- end_tool_interface
- fixed_mount variants

如果不存在合适类型：

CUSTOM_INTERFACE

但必须说明原因。

禁止使用 Robot-A-specific template。

==================================================
9. 所有 Joint 都必须有 Motion-Aware Contract
==================================================

Moving Joint：

必须生成：

- allowed_dof
- constrained_dof
- motion axis
- motion range
- parent rigid group
- child rigid group
- parent attachment region
- child attachment region
- forbidden fusion
- clearance rules
- swept clearance policy
- verification rule

Fixed Joint：

必须生成：

- rigid parent-child relation
- physical connection strategy
- zero relative DOF

Prismatic Joint：

必须生成：

- guide
- slider
- stroke corridor
- translation clearance

Mimic Joint：

必须确定性绑定 source joint
和 multiplier / offset。

Virtual/tool frame：

不生成运动接口实体。

==================================================
10. 核心原则：Rigid within Link, Movable across Joint
==================================================

对于 moving joint：

Parent Body + Parent Interface
=
one parent rigid group

Child Body + Child Interface
=
one child rigid group

Link 内部要求：

真实 rigid attachment。

Joint 两侧要求：

保持独立 rigid groups。

禁止：

Boolean Fuse(parent group, child group)

禁止：

connector 跨越 motion clearance
把目标 DOF 锁死。

==================================================
11. 第四阶段：Interface-First Link-Wise Coarse CAD
==================================================

每个 Link 按以下顺序生成：

1. proximal interface geometry
2. distal interface geometry
3. rigid attachment regions
4. main structural body
5. major joint housing
6. required large fork/opening
7. coarse transition

即：

Interface
→ Body
→ Interface

不要：

先画完整 body
→ 最后贴接口。

==================================================
12. Coarse Body 限定
==================================================

本轮只需要：

- base housing
- shoulder housing
- central web
- straight/tapered beam
- dual side plate
- fork body
- wrist block
- gripper coarse support
- simple rails/sliders if motion required
- major housing envelope

不要加入：

- detailed holes
- small grooves
- decorative bosses
- cosmetic fillet
- complex fine surface
- detailed gripper internals

==================================================
13. Mechanical Meaningfulness Gate
==================================================

所有新增几何都必须有：

- feature_id
- owning_link
- mechanical_role
- source_design_node
- source_evidence / knowledge
- why_required
- related interface/body
- CAD strategy

禁止：

gap
→ add arbitrary cube

collision
→ add unexplained support block

任何：

mechanical_role = unknown

的新 geometry：

REJECT。

Meaningless Patch Count 目标：

0

==================================================
14. 第五阶段：生成 Whole-Robot Initial Coarse CAD
==================================================

全部 physical Links 生成后：

按 URDF canonical FK
组装完整机械臂。

保存：

INITIAL_COARSE_ROBOT

这是：

Round 0

此时不要要求完美。

必须先运行统一 deterministic evaluation。

==================================================
15. Round 0 Deterministic Gates
==================================================

按严格优先级：

Gate 1
Kinematic Validity

Gate 2
Physical Attachment / Interface Validity

Gate 3
Per-Joint Motion Realization

Gate 4
Whole-Robot Collision

Gate 5
Coarse Morphology

高优先级失败：

禁止因为低优先级 geometry 指标好
而 PASS。

==================================================
16. Gate 1 — Kinematic Validity
==================================================

检查：

- topology
- frames
- joint axis
- joint origin
- joint limits
- FK
- mimic relation
- EE frame

必须确定性。

==================================================
17. Gate 2 — Physical Interface / Attachment
==================================================

检查：

- Parent Attachment Rate
- Child Attachment Rate
- BICR
- physical floating
- forbidden parent-child fuse
- interface frame consistency
- gap
- penetration
- virtual solids

目标：

BICR = 100%
Physical Floating = 0
Forbidden Fusion = 0
Virtual Solid = 0

==================================================
18. Gate 3 — Per-Joint Motion
==================================================

对全部 moving joints：

按 URDF range
执行至少：

q_min
25%
50%
75%
q_max

必要时更多采样。

验证：

- allowed DOF
- constrained DOF
- collision
- clearance
- attachment preservation

计算：

Joint Range Realization Rate（JR3）

目标：

所有 moving joints
尽可能达到 JR3 = 100%。

==================================================
19. 第六阶段：Whole-Robot Coupled Motion Sampling
==================================================

这是 Try-5A.5 最重要的新验证。

不能只：

一个 joint 动，
其它 joint 固定。

必须采样：

q = [q1, q2, ..., qn]

多自由度组合状态。

使用固定 seed。

建议：

128–256 个 configurations。

优先使用：

Sobol / Halton
或其他可复现低差异采样。

采样范围：

URDF joint limits。

Prismatic/mimic joint
按真实约束处理。

==================================================
20. Whole-Robot Motion Evaluation
==================================================

每个 coupled configuration：

1. URDF FK
2. transform all rigid Link geometries
3. broad-phase collision
4. exact narrow-phase collision
5. classify collision
6. calculate clearance
7. evaluate interface/attachment invariants

输出：

Global Collision-Free Configuration Rate

GCFR =

collision-free valid configurations
/
all sampled configurations

以及：

- collision pair frequency
- pose-specific collision
- max intersection volume
- swept collision severity
- first high-risk configuration

==================================================
21. Collision taxonomy
==================================================

继续区分：

EXPECTED_INTERFACE_CONTACT

ADJACENT_UNINTENDED_COLLISION

NONADJACENT_COLLISION

MOTION_INDUCED_COLLISION

只有 exact narrow-phase
参与最终 collision judgment。

AABB/OBB 仅 broad phase。

==================================================
22. Whole-Robot Collision Graph
==================================================

建立：

Global Collision Graph

节点：

physical Links / regions

边：

发生 unintended collision 的 pair。

边至少记录：

- collision frequency
- pose list
- mean/max intersection volume
- involved regions
- adjacent/nonadjacent
- motion-induced flag

Repair Scheduler
必须消费这个 graph。

==================================================
23. Hierarchical Repair Scope Arbiter
==================================================

使用现有：

R0 PARAMETER_REPAIR
R1 LOCAL_FEATURE_REPAIR
R2 BODY_REGION_REPLAN
R3 WHOLE_LINK_REPLAN
R4 INTERFACE_PAIR_REPLAN

本轮正式接入完整整机 coarse loop。

Deterministic evaluator：

WHAT failed

VLM：

辅助判断 WHY

Repair Arbiter：

决定 HOW MUCH TO CHANGE

==================================================
24. Repair routing
==================================================

例：

尺寸/clearance轻微错误
→ R0

某局部 housing 在少量姿态碰撞
→ R1 / R2

整个 body 侵入多个 joint swept space
→ R3

Interface family 本身持续导致：

- motion failure
- attachment failure
- collision

且 R2/R3 不能解决：

→ R4

==================================================
25. R4 必须真正重新设计 Interface
==================================================

R4 允许：

- 解冻该 Joint Interface Contract
- 重新查询 knowledge base
- 改 interface family
- 改 parent port realization
- 改 child port realization
- 重建 parent local region
- 重建 child local region
- 重新生成 motion clearance

但：

URDF joint：

- origin
- axis
- type
- limit

不能改。

==================================================
26. 每轮修复修改 Design，不直接 patch CAD
==================================================

禁止：

Evaluator fail
→ FreeCAD.addBox / move random body
→ PASS

必须：

Failure
→ Repair Scope
→ Update upstream design state
→ Regenerate CAD IR
→ FreeCAD
→ Re-evaluate

例如：

R2
必须修改：

BodyRegionSpec

R3
必须修改：

LinkCoarseSpec

R4
必须修改：

Interface Contract

==================================================
27. Progressive Freezing
==================================================

粒度：

- Joint
- Interface
- Link
- Body Region

PASS 后冻结。

例如：

J01 = FROZEN

L03:
proximal interface = FROZEN
middle body = REPAIR
distal interface = FROZEN

Repair 不得无理由修改已冻结区域。

如果 R4 有充分证据：

允许只解冻对应 Joint
及 parent/child local region。

==================================================
28. 快速迭代闭环
==================================================

完整粗阶段循环：

INITIAL BUILD
↓
DETERMINISTIC EVALUATION
↓
FAILURE LOCALIZATION
↓
REPAIR SCOPE ARBITRATION
↓
SELECTIVE DESIGN REPLAN
↓
PARTIAL CAD REBUILD
↓
EXACT RE-EVALUATION
↓
FREEZE / ROLLBACK / REPAIR
↓
repeat

最多：

3 个 whole-robot repair rounds。

如果提前满足 Gate：

立即停止。

==================================================
29. 每轮只修失败对象
==================================================

禁止每轮重建全部机器人。

只重新生成：

- failed Joint
- failed Interface Pair
- failed Link
- failed Body Region

其它：

FROZEN。

记录：

Active Repair Link Count
Active Repair Region Count
Frozen Ratio

==================================================
30. Regression Protection
==================================================

每个 repair candidate 后重新检查：

- BICR
- forbidden fusion
- interface frame
- previously valid joint motion
- previously collision-free configurations
- morphology guard

如果新方案：

解决一个 collision
但破坏已通过 joint，

ROLLBACK。

==================================================
31. Coarse Morphology Guard
==================================================

这是 Try-5A.5 必须新增的整机约束。

机械正确仍然优先，
但禁止为了 collision-free
无限缩小 body。

保护：

- link length
- major width/thickness
- principal direction
- major silhouette
- taper direction
- coarse housing envelope
- whole robot proportions

确定性指标：

- whole silhouette IoU
- per-link silhouette
- bbox
- link major dimensions
- whole IoU
- nChamfer/nHD95

VLM只辅助判断：

- body clearly too thin
- arm direction wrong
- housing grossly wrong
- wrist/gripper envelope unreasonable

==================================================
32. Morphology Regression Rule
==================================================

如果 repair：

collision明显下降

但导致：

- body退化成极细杆
- body严重缩短
- major silhouette崩溃
- mechanical structure消失

则：

MORPHOLOGY_REGRESSION

进入：

更高层次 replan

而不是继续缩小参数。

==================================================
33. VLM 的角色
==================================================

VLM 不是最终 Judge。

VLM 只可以：

- interface family plausibility
- coarse body morphology diagnosis
- repair root-cause suggestion
- R0–R4 arbitration assistance

最终 PASS 依赖：

deterministic gates。

VLM 禁止：

- 自由新增无意义组件
- 猜隐藏机构后直接建模
- 以“看起来像”覆盖 motion failure

==================================================
34. Whole-Robot Motion Playback
==================================================

最终机器人必须生成：

至少一个 multi-joint motion sequence。

例如：

home
→ extended pose
→ folded pose
→ side pose
→ wrist/gripper pose
→ return home

不要求 task planning。

要求：

- 多 joint 同时变化
- CAD rigid links 由 FK 驱动
- parent/child attachment保持
- exact collision同步检查

输出：

- pose renders
- optional GIF/video
- configuration table
- collision status

==================================================
35. Try-5A.5 成功等级
==================================================

仍区分：

K1 Pose-Driven

所有物理 Link
能按 URDF FK 运动。

K2 Collision-Valid

大部分 sampled coupled configurations
没有 unintended collision。

K3 Mechanically Realized

进一步满足：

- all Link-side attachment valid
- parent/child rigid groups correct
- no forbidden fuse
- physical joint mechanism meaningful
- expected DOF preserved
- virtual frames nonphysical
- no meaningless patch

定义：

Whole-Robot Coarse K3

只在整机满足上述条件后使用。

==================================================
36. 关键指标
==================================================

A. Artifact

- physical Link generation success
- FCStd validity
- STEP/STL export
- reopen/recompute
- zero silent fallback

B. Mechanical

- Parent Attachment Rate
- Child Attachment Rate
- BICR
- Physical Floating Link Rate
- Forbidden Fusion Count
- Spurious Virtual Geometry Count
- Meaningless Patch Count

C. Per-Joint Motion

- JR3
- collision-free sweep rate
- axis error
- center error
- min clearance
- full-range success

D. Whole-Robot Motion

- GCFR
- coupled configuration collision count
- nonadjacent collision frequency
- total intersection volume
- max intersection volume
- collision-free motion sequence success

E. Geometry

- whole IoU
- whole silhouette IoU
- mean per-link IoU
- nChamfer
- nHD95
- bbox error
- reach error

F. Repair

- R0/R1/R2/R3/R4 count
- repair success rate
- rounds
- frozen ratio
- regression count
- rollback count
- unresolved failure count

==================================================
37. Try-5A.5 建议成功门槛
==================================================

Hard requirements：

- BICR = 100%
- Physical Floating Link Rate = 0
- Forbidden Fusion Count = 0
- Virtual Geometry Count = 0
- Meaningless Patch Count = 0
- all physical links valid/rebuildable
- all moving joint rigid groups valid
- fixed/mimic/prismatic semantics correct

Per-joint：

希望：

JR3 = 100%
for all moving joints

Whole robot：

开发阶段希望：

GCFR >= 90%

非常理想：

GCFR >= 95%

不要求数学意义上的
continuous full configuration space 100% collision-free。

Morphology：

不能出现明显 collapse。

==================================================
38. 如果达不到门槛
==================================================

必须明确区分：

A. interface family failure
B. attachment failure
C. joint realization failure
D. body representation failure
E. coupled-motion collision
F. morphology-motion conflict
G. repair arbitration failure
H. FreeCAD execution failure

不要只说：

“整机仍然存在碰撞”。

如果 3 repair rounds 后仍不能解决：

标记：

UNRESOLVED

并给出根因层级。

==================================================
39. Knowledge Base 冻结原则
==================================================

Try-5A.5 开始前：

冻结当前通用 KB。

运行期间不要为了 Robot A
不断新增 case-specific knowledge。

只有当：

某个真实 joint
无法由任何现有通用 family表达

才允许新增：

一个真正通用的 knowledge entry

并记录：

why required
why not Robot-A-specific

==================================================
40. Dataflow Audit
==================================================

必须证明：

Images/URDF
→ Robot Plan
→ Interface KB
→ Interface Contract
→ LinkCoarseSpec
→ CAD IR
→ FreeCAD

真实消费。

以及：

URDF limits
→ swept clearance
→ collision graph
→ Repair Arbiter
→ updated design state
→ rebuilt CAD

真实消费。

至少做 counterfactual：

- joint limit
- interface family
- local body constraint

改变后：

对应 CAD / sweep / motion metrics 必须真实改变。

==================================================
41. GT Leakage Audit
==================================================

Generator/Repair 禁止读取：

- GT STEP
- GT B-Rep
- GT per-link mesh
- GT dimensions
- GT interface geometry
- GT feature graph
- GT collision-free body
- previous successful Robot A CAD answers

GT 只用于：

最终 geometry evaluator。

==================================================
42. 不做什么
==================================================

本轮不要：

- Try-5B fine detailing
- detailed holes
- complex surface reconstruction
- cosmetic fillets
- detailed gripper internals
- Robot B
- FEA
- torque/load
- motor sizing
- dynamic simulation
- controller
- grasp physics

本轮只完成：

Whole-Robot Mechanically Realizable Coarse CAD

==================================================
43. 开发代码原则
==================================================

直接修改：

当前 try5 主代码。

不要创建：

- parallel Try-5A.5 backend
- copied scripts tree
- compatibility duplicate pipeline

可以创建：

result/artifact snapshot

但不是第二套代码。

建议关键 Git commits：

1. clean-from-zero entrypoint
2. all-joint knowledge/motion contracts
3. whole-robot coarse generation
4. coupled-motion evaluator
5. whole-robot repair loop
6. final validation/report

==================================================
44. 建议运行流程
==================================================

Phase 1
清理旧 Robot A design-state dependencies

Phase 2
从正式输入重新解析 URDF

Phase 3
重新生成 Robot Assembly Plan

Phase 4
重新规划全部 Joint Interfaces

Phase 5
重新生成全部 Link coarse specs

Phase 6
从零生成全部 Link CAD

Phase 7
组装 Round-0 whole robot

Phase 8
跑全部 deterministic gates

Phase 9
跑 per-joint motion sweep

Phase 10
跑 128–256 coupled configurations

Phase 11
建立 Global Collision Graph

Phase 12
运行 R0–R4 Repair Arbiter

Phase 13
Selective rebuild

Phase 14
重新评价

最多重复到 Round 3

Phase 15
冻结最终 coarse robot

Phase 16
生成 whole-robot motion playback

Phase 17
最终 geometry evaluator

Phase 18
dataflow/leakage/reproducibility audit

Phase 19
final report

==================================================
45. 中间不要停
==================================================

本轮不设置人工停点。

请一次性完整运行：

从零生成
→ 整机装配
→ 运动验证
→ repair
→ final evaluation

遇到代码或实现问题：

自行调试、修改、继续。

除非出现真正无法解决的外部环境阻塞，
否则不要中途询问。

==================================================
46. 最终报告必须回答
==================================================

全部完成后一次性回答：

1. 是否真正从零开始？
2. 是否读取了任何旧 Robot A CAD/design答案？
3. URDF 解析得到多少 physical/virtual Links？
4. 多少 moving/fixed/mimic joints？
5. Robot Plan 是否重新生成？
6. 各 joint 选择了什么 interface family？
7. 是否出现 CUSTOM_INTERFACE？
8. Knowledge Base 是否被冻结？
9. 是否为了 Robot A 添加 case-specific knowledge？
10. 所有 physical Links 是否成功生成？
11. FCStd/STEP/STL 是否全部有效？
12. BICR 是否达到 100%？
13. 是否存在 physical floating？
14. 是否存在 accidental parent-child fuse？
15. 是否存在 virtual solid？
16. 是否出现 meaningless patch？
17. 每个 moving joint 的 JR3 是多少？
18. 哪些 joint full-range PASS？
19. 哪些 joint最难？
20. Fixed joint 是否正确 rigid？
21. Prismatic joint 是否正确滑动？
22. Mimic joint 是否正确联动？
23. Round 0 的 GCFR 是多少？
24. Round 1/2/3 的 GCFR 如何变化？
25. coupled motion 中最常见 collision pair 是什么？
26. Global Collision Graph 是否真实驱动 repair？
27. 总共触发多少 R0/R1/R2/R3/R4？
28. 是否真实触发 R4？
29. R4 是否更换 interface family？
30. 有多少 Link/region 被提前冻结？
31. rollback多少次？
32. collision events/volume如何随 round变化？
33. final GCFR是多少？
34. 是否达到 >=90%？
35. 是否达到 >=95%？
36. 是否存在 unresolved configurations？
37. whole robot motion playback 是否成功？
38. CAD Link 是否真实随 FK 多关节运动？
39. EE pose/FK 是否正确？
40. whole IoU / silhouette / per-link geometry如何？
41. morphology是否为了运动出现严重退化？
42. Meaningfulness Gate 是否阻止metric gaming？
43. FreeCAD 是否仍不是主要瓶颈？
44. 当前最大瓶颈是什么？
45. Robot A 是否达到 Whole-Robot Coarse K1？
46. 是否达到 Whole-Robot Coarse K2？
47. 是否达到 Whole-Robot Coarse K3？
48. 是否已经满足进入 Try-5B 的条件？
49. 如果不满足，缺的最后一项是什么？
50. 是否值得冻结粗建模阶段架构？

==================================================
47. 最终核心判断
==================================================

本轮真正需要回答的不是：

“CAD 文件生成成功了吗？”

而是：

> 从 Image + Text + sanitized URDF 出发，
> 在不复用旧 Robot A CAD 答案的情况下，
> 当前 RobotCAD Try-5 方法
> 是否能够自主设计所有 Link / Joint，
> 生成一台完整 coarse mechanical robot，
> 并通过知识、运动学、接口、碰撞和分层修复，
> 将其推进到可装配、可运动、机械上合理的状态？

完成全部任务后再统一汇报。