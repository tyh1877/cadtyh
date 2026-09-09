# RobotCAD Try-5A.4
# Knowledge-Guided Motion-Realizable Joint Reconstruction
# From URDF Kinematics to Mechanically Articulated CAD

请继续直接修改现有 try5 主代码，完成 Try-5A.4。

IMPORTANT：

1. 不要新建 Try-5A.4 独立 pipeline/backend/scripts 副本；
2. 直接修改当前 try5 implementation；
3. 开发阶段允许重构、删除旧实现、修改 schema；
4. 使用 Git commit 保存关键节点；
5. 历史实验结果不要覆盖；
6. 本轮中间不要停下来向我汇报；
7. 所有开发、实验、评价、审计完成后，再一次性给最终报告。

==================================================
0. 背景与当前结论
==================================================

Try-5 已经得到以下证据：

A. URDF Kinematic Skeleton：
- topology / frame / FK 已较稳定；
- URDF 应继续作为 kinematic authority。

B. Try-5A：
- Robot-Level Planning 本身未明显改善 geometry；
- Interface-first Shared Joint Design 明显改善逻辑连接；
- 但当时 evaluator 把 port/frame consistency 错当成 physical connectivity。

C. Try-5A.1 / A.2：
- exact collision evaluator 已建立；
- AABB 只能用于 broad phase；
- physical Body-Interface Attachment evaluator 发现历史 BICR 实际为 0%；
- virtual tool-center frame 不应实体化；
- collision-aware body planning 能降低 collision，但 sweep-free pose rate 仍为 0%。

D. Try-5A.3：
- Robot Interface Knowledge Base 已真实改变 interface family selection；
- knowledge retrieval → Interface Contract → CAD IR → FreeCAD 的数据流真实存在；
- Mechanical Meaningfulness Gate 能拦截明显无意义 patch；
- 但知识库目前主要解决“接口叫什么/选哪一类”，
  还没有解决“这种机械接口为什么能够运动，以及 CAD 中如何实现允许 DOF”。

当前核心瓶颈：

Knowledge-guided interface selection
≠
Motion-realizable mechanical joint

本轮要解决：

URDF Joint
→ Motion Semantics
→ Mechanical Interface Realization
→ Parent/Child Rigid Groups
→ Motion Clearance
→ CAD
→ URDF-driven motion validation

==================================================
1. Try-5A.4 核心目标
==================================================

本轮只回答：

> 能否把输入 URDF 中的 joint
> 真正转换成一个具有机械意义、
> parent/child 分属独立刚体、
> 具有正确 DOF 和运动间隙、
> 可以随 URDF 运动而不只是静态拼接的 CAD joint？

核心原则：

Kinematics defines motion.
Knowledge defines mechanical realization.
CAD realizes geometry.
Deterministic simulation verifies motion.

本轮优先级：

Mechanical articulation
>
Collision-free motion
>
Coarse appearance
>
Fine geometry

本轮不要进入 Try-5B fine detailing。

==================================================
2. 实验对象
==================================================

仍然只使用现有 Robot A。

不要运行：
- Robot B
- transfer robot
- 新数据集

首先选择 Robot A 中 3 个代表性 physical joints 做 motion-realization pilot。

至少覆盖：

Joint A：
shoulder revolute joint

要求：
- 大结构 rotary housing / support；
- parent/child attachment；
- rotary clearance。

Joint B：
elbow revolute joint

优先选择具有：
- fork / boss / coaxial structure
的 joint。

Joint C：
wrist / gripper neighborhood joint

要求：
- spatially constrained；
- neighbor collision risk；
- motion swept clearance difficult。

根据当前 Robot A 的真实 joint IDs 自动选择并记录，
不要 hard-code 虚构 joint。

如果样本实际机械语义与上述描述不同，
选择最接近的三个代表性 physical joints，
并说明原因。

==================================================
3. Knowledge Base 从“接口类别”升级为“运动实现知识”
==================================================

继续使用现有：

try5/knowledge/robot_interfaces/

直接升级已有 knowledge entries。

不要重新搭大型 RAG。

每个 interface family 除已有内容外，
必须新增以下知识：

A. Kinematic semantics
- compatible joint type
- allowed DOF
- constrained DOF
- motion axis
- motion range semantics

B. Parent-side rigid structure
- 哪些结构属于 parent link
- 如何连接 parent body
- 哪些区域必须 rigid

C. Child-side rigid structure
- 哪些结构属于 child link
- 如何连接 child body
- 哪些区域必须 rigid

D. Parent-child relation
- 哪些部分允许接触
- 哪些部分需要 clearance
- 哪些部分绝对不能 fuse

E. Motion-preserving constraints
- radial clearance
- axial clearance
- swept clearance
- rotation/translation corridor

F. Forbidden configurations
例如：
- parent interface 与 child interface Boolean Fuse
- solid bridge crossing revolute clearance
- body penetrating motion swept volume
- connector locking intended DOF

G. CAD realization strategy
不是保存 GT CAD，
而是描述可参数化 construction logic。

H. Verification rules
- attachment
- coaxiality
- clearance
- allowed relative motion
- collision sweep

==================================================
4. 典型知识示例
==================================================

例如 fork_pin_interface 应表达：

joint_semantics:
  revolute

parent_side:
  fork_left
  fork_right
  rigidly_attached_to_parent_body

child_side:
  central_boss
  rigidly_attached_to_child_body

relations:
  fork_left symmetric_with fork_right
  central_boss between fork arms
  all bore/pin axes coaxial with URDF axis

allowed_motion:
  child rotates relative to parent about URDF axis

required_clearance:
  rotational clearance between boss and fork
  side clearance between boss and fork arms

forbidden:
  fuse parent and child
  bridge fork opening with solid
  attach child boss to parent body

CAD realization:
  parent fork geometry
  child central boss
  coaxial bore/shaft clearance region

verification:
  parent attachment valid
  child attachment valid
  axis aligned
  requested range rotates without unintended collision

类似地升级：

- coaxial_rotary_interface
- nested_rotary_housing
- rail_slider_interface
- planar_mount_interface
- end_tool_interface

==================================================
5. Motion-Aware Interface Contract
==================================================

升级现有 Interface Contract schema。

每个 physical moving joint 至少新增：

- allowed_dof
- constrained_dof
- motion_axis
- motion_range
- parent_rigid_group
- child_rigid_group
- parent_attachment_region
- child_attachment_region
- allowed_contact_regions
- required_clearance_regions
- swept_clearance_region
- forbidden_fusion_pairs
- relative_motion_rule
- motion_validation_rule

例如：

{
  "joint_id": "J3",

  "joint_type": "revolute",

  "allowed_motion": {
    "type": "rotation",
    "axis_source": "URDF_J3_AXIS",
    "min": "...",
    "max": "..."
  },

  "parent_rigid_group": {
    "link_id": "L2",
    "members": [
      "parent_body",
      "parent_interface"
    ]
  },

  "child_rigid_group": {
    "link_id": "L3",
    "members": [
      "child_body",
      "child_interface"
    ]
  },

  "forbidden_fusion_pairs": [
    ["parent_interface", "child_interface"]
  ],

  "clearance": {...},

  "swept_clearance_region": {...}
}

==================================================
6. 最重要的刚体原则
==================================================

必须实现并审计：

# Link 内部

Body_i
+
InterfaceCarrier_i

必须属于同一个 rigid group。

即：

parent body ↔ parent interface
必须刚性连接。

child body ↔ child interface
必须刚性连接。

# Joint 两侧

ParentRigidGroup
与
ChildRigidGroup

必须保持为两个独立刚体。

禁止因为“连接”而：

Boolean Fuse(parent, child)

否则 revolute/prismatic DOF 被机械上锁死。

核心原则：

Rigid within Link.
Movable across Joint.

==================================================
7. Physical Attachment 必须真实实现
==================================================

继续使用严格 BICR evaluator。

对于每个 joint：

Parent Attachment = PASS
Child Attachment = PASS

要求：

interface carrier 与自己的 link body
具有真实 CAD rigid attachment path。

允许：
- same solid
- explicit mechanical connector belonging to same rigid group

不允许：
- floating carrier
- metadata-only attachment
- arbitrary meaningless cube patch

Mechanical Meaningfulness Gate 继续生效。

任何 connector 必须：

- mechanical_role
- design provenance
- source knowledge / design node
- owning rigid group
- CAD strategy

==================================================
8. 建立 Motion Clearance Envelope
==================================================

这是 Try-5A.4 的核心新增能力。

不要继续：

CAD 完成
→ 最后检查 collision

而是：

URDF motion
→ swept volume
→ body/interface design constraint

对于每个 pilot joint：

根据 joint limits 采样至少：

- q_min
- 25%
- 50%
- 75%
- q_max

必要时增加更多样本。

对于 revolute：

让 child rigid group
绕 frozen URDF axis
相对 parent rigid group 运动。

对于 prismatic：

沿 frozen URDF axis 平移。

计算：

- child swept occupancy
- interface swept occupancy
- nearby body conflict region
- required clearance corridor

建立：

motion_clearance_spec.json

==================================================
9. Motion Swept Clearance 不是 GT
==================================================

swept clearance 只能由：

- generated geometry
- URDF joint
- current Interface Contract
- current parent/child rigid groups

计算。

禁止读取：

- GT STEP motion
- GT swept volume
- GT joint CAD
- GT clearance dimensions

==================================================
10. Body 必须适应 Motion Envelope
==================================================

如果 body 侵入 motion clearance：

优先修改：

- local body section
- housing envelope
- interface-adjacent region
- local transition

而不是：

- 移动 URDF joint
- 改 joint axis
- 缩整个机器人
- 直接删除机械必要结构

原则：

Motion constraints are hard constraints.
Body adapts around them.

==================================================
11. M0 / M1 / M2 三个条件
==================================================

本轮只做三个条件。

--------------------------------------------------
M0 — Frozen Current Knowledge-Guided Interface
--------------------------------------------------

使用当前 Try-5A.3 K1 的 interface decision / realization。

不要重新优化。

M0 代表：

Knowledge-guided interface family selection
but no explicit motion-realizable realization.

作为 baseline。

--------------------------------------------------
M1 — Executable Motion Interface
--------------------------------------------------

在 M0 基础上新增：

- motion-aware Interface Contract
- parent rigid group
- child rigid group
- strict own-body attachment
- forbidden parent-child fusion
- explicit DOF
- explicit mechanical clearance
- mechanically meaningful connector logic

但：

M1 不使用 motion swept body replanning。

目的：

回答：

“把 interface family 进一步展开成真正的运动接口结构，
是否改善 joint mechanical realization？”

--------------------------------------------------
M2 — + Motion-Swept Design
--------------------------------------------------

在 M1 基础上增加：

URDF joint range
→ pose sampling
→ swept clearance
→ exclusion/corridor
→ local body/interface-adjacent replanning

目的：

回答：

“把运动轨迹提前加入设计约束后，
是否能让 joint 真正获得更多 collision-free motion？”

M2 不进入 fine appearance refinement。

==================================================
12. M0/M1/M2 公平性
==================================================

三组保持：

- same Robot A
- same 3 pilot joints
- same input images
- same engineering text
- same sanitized URDF
- same Codex model
- same FreeCAD backend
- same knowledge base content where applicable
- same evaluator
- same motion pose sampling
- same collision engine

M1/M2 新增方法成本允许记录。

==================================================
13. 真正的运动实现
==================================================

不要依赖 FreeCAD native assembly joint
作为实验唯一实现。

正式运动验证采用：

Generated Link CAD
+
URDF FK
+
Rigid Group Transform

对于每个 q：

compute T_i(q)

然后：

transform each physical rigid link geometry

并检查：

- joint relation
- collision
- clearance
- interface consistency
- EE pose

这样可以避免 FreeCAD native joint API
成为研究阻塞点。

如已有 FreeCAD native joint
可作为辅助展示，
但不是 hard requirement。

==================================================
14. Motion Playback
==================================================

必须为 3 个 pilot joints
生成 motion playback artifact。

至少保存：

- sampled pose renders
- start/mid/end poses
- optional GIF/video if existing pipeline supports
- joint-state table
- collision overlays

目标是直观看到：

这些 link 不是静态拼接，
而是在 URDF kinematic transform 下真实作为独立刚体运动。

==================================================
15. Kinematic motion 与 Mechanical motion 分开评价
==================================================

报告必须明确区分：

LEVEL K1 — Pose-Driven Motion

CAD rigid links 能随 URDF FK 正确变换。

LEVEL K2 — Collision-Valid Motion

关节一定范围内：
- no unintended collision
- clearance acceptable

LEVEL K3 — Mechanically Realized Motion

除 K1/K2 外，还满足：
- parent interface attached to parent body
- child interface attached to child body
- parent/child not fused
- interface mechanism mechanically plausible
- joint family与视觉/知识相容
- motion依靠真实接口空间关系，而不是悬浮刚体

==================================================
16. Hard Mechanical Gates
==================================================

每个 pilot joint 至少检查：

A. Parent Attachment Gate
B. Child Attachment Gate
C. Forbidden Fusion Gate
D. Joint Axis Gate
E. Joint Center Gate
F. Motion Clearance Gate
G. Mechanical Meaningfulness Gate
H. Exact Collision Gate

如果：

parent/child fuse into one solid

则该 joint 直接：

MOTION_REALIZATION_FAIL

即使画面上可以通过修改 Placement “播放”。

==================================================
17. Collision Detection
==================================================

继续：

Broad phase:
AABB/OBB

Narrow phase:
exact B-Rep common / precise mesh collision

正式 motion validity 只采用 narrow-phase。

区分：

EXPECTED_INTERFACE_CONTACT
ADJACENT_UNINTENDED_COLLISION
NONADJACENT_COLLISION
MOTION_INDUCED_COLLISION

==================================================
18. Joint Range Realization
==================================================

新增：

Joint Range Realization Rate

例如 revolute joint：

在 URDF allowed range 的 sampled poses 中：

满足全部 hard motion constraints 的比例。

定义：

JR3 =
valid_motion_samples
/
all_requested_samples

同时记录：

- first collision angle
- maximum collision-free interval
- min clearance across range
- collision volume vs q

==================================================
19. Pilot 成功标准
==================================================

Try-5A.4 不要求整台机器人全 range 100% collision-free。

但希望至少观察到：

M0 → M1：
- BICR / attachment 提高
- forbidden fusion = 0
- mechanical joint representation 更合理

M1 → M2：
- collision event减少
- swept collision volume减少
- collision-free pose rate提高
- 至少部分 joint 获得非零 collision-free motion interval

关键目标：

当前长期：

Sweep-Free Rate = 0%

Try-5A.4 希望首次实现：

Sweep-Free Rate > 0

更理想：

至少一个或多个 pilot joint
实现完整 requested range collision-free。

==================================================
20. Repair Scope Arbiter 接入
==================================================

Try-5A.3 已规划 Repair Scope Arbiter。

本轮在 motion realization 后正式使用其层级：

R0 PARAMETER_REPAIR
R1 LOCAL_FEATURE_REPAIR
R2 BODY_REGION_REPLAN
R3 WHOLE_LINK_REPLAN
R4 INTERFACE_PAIR_REPLAN

但不要做无限迭代。

每个 M2 pilot joint 最多允许：

2 次 motion-driven repair。

==================================================
21. Motion Failure → Repair Scope
==================================================

典型 routing：

Case A：
mechanism/family正确，
clearance 小量不足

→ R0 / R1

Case B：
某一局部 housing
只在特定 pose collision

→ R1 / R2

Case C：
整个 body 占据 joint swept space

→ R3

Case D：
知识库 family 和视觉/运动需求明显不匹配，
并且多次局部修复失败

→ R4

R4 必须允许：

- interface family change
- rebuild Interface Contract
- rebuild parent local region
- rebuild child local region

==================================================
22. VLM 在本轮的角色
==================================================

VLM 不是运动 Judge。

Deterministic evaluator 决定：

- attachment
- axis
- clearance
- collision
- motion validity
- range realization

VLM 只辅助：

1. interface family visual plausibility
2. root-cause diagnosis
3. repair scope arbitration

例如：

“当前视觉上明显为 fork structure，
但 CAD 使用 closed coaxial housing，
且运动碰撞持续存在。”

VLM 可以建议：

R4_INTERFACE_PAIR_REPLAN

但最终改完后必须重新经过 deterministic gates。

==================================================
23. Mechanical Meaningfulness Gate 继续严格执行
==================================================

禁止再次出现：

gap/collision
→ add meaningless box
→ metric improves

所有新增 geometry 必须映射到：

- interface knowledge node
- rigid attachment node
- body structural node
- motion clearance design node

新增 geometry 如果：

mechanical_role = unknown

直接：

MECHANICAL_MEANINGFULNESS_FAIL

==================================================
24. Knowledge 不应该强迫错误 family
==================================================

知识库是 prior，不是绝对答案。

如果：

- visual evidence
- motion feasibility
- deterministic constraints

共同表明当前 KB candidate 不合理，

允许：

CUSTOM_INTERFACE

或选择排名第二 family。

记录：

why KB first candidate rejected。

==================================================
25. 主要指标
==================================================

A. Interface / Attachment

- Parent Attachment Rate
- Child Attachment Rate
- BICR
- Physical Floating Rate
- Forbidden Parent-Child Fusion Count
- Mechanical Meaningfulness Rate

B. Joint geometry

- Joint Axis Angular Error
- Joint Axis Offset Error
- Joint Center Error
- Coaxiality
- clearance

C. Motion

- Collision-Free Joint Sweep Pose Rate
- Joint Range Realization Rate
- Maximum Collision-Free Interval
- First Collision Pose/Angle
- Total Swept Collision Volume
- Minimum Clearance
- Motion-Induced Collision Count

D. Representation

- selected interface family
- rigid-group correctness
- knowledge entry consumed
- custom interface rate

E. Repair

- repair scope distribution
- repair success rate
- R4 rate
- regression / rollback
- motion improvement after repair

==================================================
26. Geometry 指标仅作为辅助
==================================================

继续报告：

- per-link IoU
- whole-robot IoU
- silhouette
- nChamfer
- nHD95

但本轮不以 geometry fidelity
作为核心成功条件。

不要为了提高 IoU
牺牲 joint motion。

==================================================
27. Dataflow Audit
==================================================

必须证明：

URDF joint
→ motion semantics
→ knowledge retrieval
→ motion-aware Interface Contract
→ rigid-group spec
→ CAD IR
→ FreeCAD

真实消费。

以及：

URDF limits
→ sampled poses
→ swept clearance
→ M2 body/interface local planning
→ CAD geometry

真实消费。

至少做 counterfactual：

A. 改 joint limit
应改变 swept clearance。

B. 改 knowledge family
应改变 interface realization。

C. 改 clearance parameter
应改变 joint CAD / motion metric。

==================================================
28. Leakage
==================================================

Generator 不得读取：

- GT STEP
- GT B-Rep
- GT interface dimensions
- GT mechanical internals
- GT collision-free body
- GT motion clearance

GT 只进入：

- geometry evaluator
- final visual comparison

知识库不能包含 Robot A 特定答案。

==================================================
29. 不做什么
==================================================

本轮禁止进入：

- Try-5B Semantic Inventory
- fine link detailing
- detailed holes
- cosmetic fillets
- detailed gripper reconstruction
- Robot B
- FEA
- motor sizing
- torque/load
- controller
- dynamic simulation
- grasp physics

只研究：

mechanically realizable articulated coarse CAD。

==================================================
30. 输出与开发目录原则
==================================================

IMPORTANT：

代码：

继续直接使用当前 try5 主代码。

不要复制：
- backend
- evaluator
- scripts
- skills

实验 artifact / results
可以在现有 Try-5 results tree
增加 Try-5A.4 标识，
但不要建立第二套代码系统。

使用 Git 保存：

建议关键 commit：

1. motion-aware knowledge/schema
2. rigid-group + attachment realization
3. swept-clearance generation
4. M0/M1/M2 experiment
5. repair + final evaluation

中间不需要向我汇报。

==================================================
31. 最终输出 Artifact
==================================================

至少保存：

- upgraded interface knowledge entries
- motion-aware interface contracts
- rigid_group_specs
- attachment audit
- motion_clearance_specs
- swept-volume artifacts
- M0/M1/M2 CAD
- sampled pose renders
- collision tables
- joint range metrics
- repair contracts
- dataflow audit
- leakage audit
- contact sheets

如果方便，
生成 3 个 pilot joints 的 motion animation/GIF/video；
如果当前环境不适合，
至少保存完整 pose sequence renders。

==================================================
32. 最终报告必须回答
==================================================

所有任务完成后一次性汇报：

1. 选择了哪 3 个 pilot joints？为什么？
2. 它们各自的 URDF joint type / axis / limits 是什么？
3. K0/K1 知识库给出了哪些 interface families？
4. Try-5A.4 后每个 family 新增了哪些 motion realization rules？
5. M0/M1/M2 分别是什么？
6. Parent Attachment Rate 如何变化？
7. Child Attachment Rate 如何变化？
8. BICR 如何变化？
9. 是否仍存在 floating interface？
10. 是否发生 parent-child accidental fuse？
11. Forbidden Fusion Count 是否为 0？
12. 每个 joint 的 rigid groups 是否正确？
13. CAD 是否真的保持 parent/child 为独立刚体？
14. URDF FK 是否能够驱动 CAD Link movement？
15. 是否生成 motion playback？
16. M0/M1/M2 的 collision-free pose rate是多少？
17. Joint Range Realization Rate 是多少？
18. 哪个 joint 首先实现非零 collision-free interval？
19. 是否有 joint 达到完整 requested range collision-free？
20. swept clearance 是否真实影响 CAD？
21. M1 → M2 的 collision 是否改善？
22. 哪些 collision 仍无法解决？
23. 哪些 joint 需要 R0/R1/R2/R3/R4？
24. 是否真正执行了 R4 interface pair replan？
25. R4 是否改变 interface family？
26. 是否再次出现 meaningless geometry patch？
27. Mechanical Meaningfulness Gate 是否有效？
28. VLM 的建议是否只用于 plausibility/root-cause，而非最终 motion Judge？
29. Knowledge Base 是否真实帮助 joint motion realization，而不只是改变 family 名称？
30. 当前机器人达到：
    - K1 Pose-Driven
    - K2 Collision-Valid
    - K3 Mechanically Realized
   中的哪一级？
31. FreeCAD 是否仍不是主要瓶颈？
32. 当前最大瓶颈是什么？
33. 是否值得把方法扩展到 Robot A 全部 physical joints？
34. 是否已经具备进入整机 coarse motion reconstruction 的条件？
35. 是否已经具备进入 Try-5B 的条件？

==================================================
33. 最终判断标准
==================================================

Try-5A.4 的成功不等于：

“动画播放出来了。”

真正成功至少需要证明：

URDF Joint
↓
Mechanical Interface
↓
Parent/Child Rigid Groups
↓
Correct Attachment
↓
Allowed Relative DOF
↓
Motion Clearance
↓
Collision-Aware Motion

即：

机械臂的 Link 不再只是
按照 URDF Placement 静态摆在一起，

而是：

由具有明确机械意义的 joint geometry
连接成相互独立的刚体，
并能够按照 URDF DOF
产生真实可验证的相对运动。

==================================================
34. 执行要求
==================================================

请现在开始完整执行 Try-5A.4。

按合理工程顺序自行完成：

- knowledge upgrade
- schema upgrade
- 3-joint selection
- M0
- M1
- M2
- rigid-group implementation
- attachment
- swept clearance
- motion playback
- exact collision evaluation
- 最多2轮 motion-driven repair
- dataflow audit
- leakage audit
- final report

中间不要暂停，不要等待我确认。

遇到实现问题时：
自行诊断、修改、测试并继续。

除非出现无法继续的外部环境阻塞，
否则不要中途向我询问实现选择。

所有实验完成后，
再一次性汇报最终结果。