# RobotCAD Try-5A.1
# Collision-Aware Coarse Body Planning
# Freeze Interfaces, Replan Bodies

Try-5A 已完成，结论为 partial success。

已知：
- A2 Connected Joint Rate = 100%
- Floating Link Rate = 0
- Interface Gap = 0
- nominal-radius mismatch = 0
- excessive axial penetration = 0
- URDF frame / axis / origin consistency 正确
- FreeCAD 执行稳定
- 但 coarse geometry 没有改善
- conservative sweep collision-free rate = 0%
- 当前主要瓶颈为 coarse body geometry + collision-aware planning

本轮不要重做 Try-5A。
不要修改已通过的 Joint Interface Contracts。
不要进入 Try-5B 细节建模。

--------------------------------------------------
1. 核心研究问题
--------------------------------------------------

RQ1：
在冻结正确接口后，
加入 collision-aware body envelope / free-space constraint，
是否能减少非预期碰撞？

RQ2：
在 collision constraint 基础上，
加入视觉 coarse morphology constraint，
是否能同时保持装配正确和改善粗几何？

核心原则：

Freeze interfaces,
replan bodies.

--------------------------------------------------
2. 实验对象
--------------------------------------------------

继续只使用 Try-5A 的 Robot A。

不要运行 Robot B。
不要扩大数据集。

A2 作为 frozen starting point。

--------------------------------------------------
3. 正式输入
--------------------------------------------------

沿用 Try-5A：

- multi-view images
- engineering text
- sanitized URDF
- frozen Robot Assembly Plan
- frozen Joint Interface Contracts
- frozen A2 interface geometry

禁止新增：

- GT STEP generator input
- GT per-link CAD
- GT interface geometry
- GT body dimensions

GT 仅进入 evaluator。

--------------------------------------------------
4. 冻结内容
--------------------------------------------------

以下内容必须冻结：

- URDF topology
- joint origin
- joint axis
- joint limits
- shared interface frame
- parent port
- child port
- interface family
- interface radius/depth
- interface gap/clearance rules
- protected interface regions

后续 Body Replan 不得修改这些内容。

--------------------------------------------------
5. 可修改内容
--------------------------------------------------

只允许修改：

- main body geometry
- body envelope
- cross-section
- taper
- coarse housing shape
- body transition
- non-interface coarse structure

原则：

Interface A
→ collision-aware body
→ Interface B

--------------------------------------------------
6. 新增 Body Planning Representation
--------------------------------------------------

升级 LinkCoarseSpec，增加：

- centerline
- interface_to_interface_span
- allowed_body_region
- forbidden_collision_region
- neighbor_exclusion_regions
- maximum_cross_section
- preferred_section_family
- visual_silhouette_constraints
- protected_interface_regions
- motion_swept_exclusion_regions

建议输出：

collision_aware_link_spec.json

--------------------------------------------------
7. Body Free-Space Envelope
--------------------------------------------------

对每个 Link 建立：

# Allowed Body Region

定义：

Link body 应尽量位于允许区域内。

同时建立：

# Forbidden / Exclusion Regions

包括：

- neighboring link protected volume
- joint rotation clearance volume
- nonadjacent link collision volume
- gripper/wrist motion clearance region
- interface protected region

不要只靠 Agent 自由估尺寸。

--------------------------------------------------
8. Motion-Swept Exclusion Volume
--------------------------------------------------

利用 URDF joint limits / sampled joint poses：

对邻近 link 计算粗 motion swept region。

Body 不应侵入会导致明显运动干涉的区域。

本轮不要求高精度动力学。

只需要：

- sampled FK
- transformed coarse geometry
- swept occupancy / collision envelope

--------------------------------------------------
9. Collision Detection 分两级
--------------------------------------------------

不要只使用 AABB 作为最终碰撞结论。

必须实现：

# Broad Phase
AABB 或 OBB

用于快速筛选可能碰撞 pair。

# Narrow Phase
对命中 pair 使用更精确方法：

优先：
- B-Rep intersection
或
- mesh triangle collision / intersection
或
- exact boolean common volume

至少得到：

- true collision pair
- intersection volume
- minimum clearance if possible

明确区分：

AABB_OVERLAP

和

TRUE_GEOMETRIC_COLLISION

--------------------------------------------------
10. 邻接 / 非邻接碰撞分类
--------------------------------------------------

每个 collision pair 分类：

A. expected interface contact

允许。

B. adjacent unintended collision

相邻 link 在接口外错误干涉。

C. nonadjacent collision

非邻接 link 干涉。

D. motion-induced collision

静态不碰，但 joint sweep 中碰撞。

Evaluator 必须区分这些情况。

--------------------------------------------------
11. 三个实验条件
--------------------------------------------------

本轮只做：

C0
C1
C2

--------------------------------------------------
C0 — Frozen A2
--------------------------------------------------

直接复用 Try-5A A2。

不重新生成。
不调参。

作为 baseline。

--------------------------------------------------
C1 — + Collision-Aware Body Envelope
--------------------------------------------------

冻结全部 interfaces。

新增：

- allowed body region
- forbidden regions
- neighbor exclusion
- motion swept exclusion
- collision-aware body sizing

流程：

Frozen Interfaces
→ Collision/Free-Space Analysis
→ Collision-Aware Link Body Spec
→ Body Replan
→ FreeCAD
→ Whole Robot Assembly
→ Exact Collision Evaluation

C1 不重点追求视觉相似。

核心目标：

减少 collision，
同时保持 interface metrics 不退化。

--------------------------------------------------
C2 — + Visual Coarse Morphology Replanning
--------------------------------------------------

在 C1 基础上增加视觉约束。

流程：

Frozen Interfaces
→ Collision-Aware Body Space
→ Visual Coarse Morphology Constraints
→ Body Replan
→ FreeCAD
→ Assembly
→ Evaluation

视觉约束只处理：

- major silhouette
- body thickness
- taper direction
- broad housing profile
- main section family
- relative body proportion

不要进入：

- small holes
- small recess
- fillet details
- gripper internals
- cosmetic details

C2 的目标：

在不重新引入 collision 的前提下，
改善粗几何。

--------------------------------------------------
12. C1/C2 都必须保护接口
--------------------------------------------------

每次重新生成 body 后检查：

- interface frame unchanged
- parent/child port unchanged
- nominal radius unchanged
- target gap unchanged
- interface protected geometry preserved

如果 body replan 破坏接口：

该结果 FAIL。

--------------------------------------------------
13. Link Body Replan 顺序
--------------------------------------------------

优先处理 Try-5A 中最困难 Link：

- L02 upper arm
- L07 gripper crossbar
- L01 shoulder housing

以及 collision evaluator 检出的高风险 Link。

不要默认 12 个 Link 全部重建。

使用 Selective Body Replan：

只修改：

- collision-causing links
- severe morphology-error links

已无碰撞且 morphology 合理的 Link：

FROZEN

--------------------------------------------------
14. Collision-Aware Scheduler
--------------------------------------------------

每个 Link 状态：

BODY_OK
COLLISION_REPLAN
MORPHOLOGY_REPLAN
COLLISION_AND_MORPHOLOGY_REPLAN
FROZEN

Scheduler 只处理非 FROZEN Link。

--------------------------------------------------
15. Collision Repair Contract
--------------------------------------------------

如果发生 collision，必须输出结构化 Contract。

例如：

{
  "link_id": "L03",
  "state": "COLLISION_REPLAN",
  "collision_pair": ["L03", "L05"],
  "collision_type": "nonadjacent",
  "intersection_volume_mm3": 420.5,
  "region": "distal_body_side",
  "protected_interfaces": ["J03", "J04"],
  "recommended_action": "REDUCE_CROSS_SECTION",
  "direction": "local_y",
  "do_not_change": [
    "proximal_interface",
    "distal_interface"
  ]
}

禁止自由文本：

“这里可能碰到了，请改一下。”

--------------------------------------------------
16. Visual Coarse Review Contract
--------------------------------------------------

C2 如果 geometry 差：

VLM 只能输出 coarse morphology 级修改：

例如：

- body too thick
- upper arm should taper distally
- shoulder housing too cylindrical
- wrist block oversized

不能要求：

- 加小圆柱
- 加不明凸台
- 猜内部机构

--------------------------------------------------
17. Body Shape Families
--------------------------------------------------

本轮只使用少量 coarse body family：

- central_web
- straight_beam
- tapered_beam
- dual_side_plate
- coarse_shell
- shoulder_housing
- forearm_body
- wrist_block
- base_housing
- simple_crossbar

不要扩展详细 Feature vocabulary。

--------------------------------------------------
18. Robot-Level Planning 升级
--------------------------------------------------

Try-5A 的 Robot Plan 主要是描述性。

Try-5A.1 要让它带几何约束。

每个 Link 至少加入：

- proximal frame
- distal frame
- interface span
- centerline
- max cross-section
- allowed corridor
- exclusion regions
- preferred taper
- visual envelope target

这部分必须真实影响 CAD body。

做 dataflow audit。

--------------------------------------------------
19. 主要评价指标
--------------------------------------------------

A. Interface Preservation

必须继续报告：

- Connected Joint Rate
- Floating Link Rate
- Mean Interface Gap
- nominal-radius mismatch
- excessive interface penetration
- axis/origin error

目标：

C1/C2 不得显著低于 C0。

--------------------------------------------------
20. Exact Collision Metrics
--------------------------------------------------

新增核心指标：

1. True Collision Pair Count
2. Adjacent Unintended Collision Count
3. Nonadjacent Collision Count
4. Intersection Volume
5. Minimum Clearance
6. Collision-Free Joint Sweep Rate
7. Collision-Free Pose Sample Rate

不要把 AABB overlap 直接等同于真实 collision。

--------------------------------------------------
21. Motion Metrics
--------------------------------------------------

继续使用：

- joint-limit sweep
- sampled FK
- workspace

重点是：

Generated geometry 是否能在这些姿态下避免非预期碰撞。

FK 本身因为 URDF authority 仍应保持正确。

--------------------------------------------------
22. Coarse Geometry Metrics
--------------------------------------------------

继续：

- per-link IoU
- nChamfer
- nHD95
- silhouette IoU
- whole-robot IoU
- whole-robot silhouette
- bbox error
- reach error

C1：
允许 geometry 小幅变化，
重点看 collision。

C2：
要求 geometry 相比 C1 改善，
且 collision 不明显反弹。

--------------------------------------------------
23. 关键成功模式
--------------------------------------------------

理想结果：

C0:
interfaces correct
but collision high

C1:
interfaces preserved
collision clearly reduced

C2:
interfaces preserved
collision remains low
geometry/morphology improves

即：

C0
→ +collision constraints
→ C1
→ +visual morphology
→ C2

--------------------------------------------------
24. 失败诊断
--------------------------------------------------

如果 C1 不能减少碰撞：

区分：

- collision evaluator wrong
- free-space envelope wrong
- body corridor wrong
- body planner ignores constraints
- interface envelope too large
- URDF geometry context insufficient

如果 C2 geometry 不改善：

区分：

- visual morphology extraction weak
- body family wrong
- parameter estimation weak
- collision constraints too restrictive

--------------------------------------------------
25. 本轮不做什么
--------------------------------------------------

禁止加入：

- Try-5B Semantic Inventory
- detailed Feature Graph
- detailed gripper mechanism
- small holes
- fillets/chamfers
- cosmetic detail
- Robot B
- multi-round fine repair
- FEA
- torque/load
- dynamics/control

--------------------------------------------------
26. 输出目录
--------------------------------------------------

experiments/try5A_1/

  protocol/
    try5A_1_protocol.md

  C0/
  C1/
  C2/

  body_specs/
  free_space/
  exclusion_regions/
  collision_analysis/
  link_cad/
  assemblies/
  contact_sheets/

results/try5A_1/

  interface_preservation.csv
  exact_collision_metrics.csv
  sweep_collision_metrics.csv
  coarse_geometry_metrics.csv
  per_link_metrics.csv
  per_pair_collision.csv
  resource_metrics.csv

  try5A_1_report.md

--------------------------------------------------
27. 最终报告必须回答
--------------------------------------------------

1. C0/C1/C2 的 Connected Joint Rate 是否保持？
2. Floating Link 是否仍为 0？
3. Interface Gap 是否保持？
4. protected interfaces 是否全部保留？
5. AABB overlap 与 true collision 有多大差异？
6. C0 true collision pair 数是多少？
7. C1 是否显著减少 collision？
8. C2 是否保持 collision 改善？
9. joint sweep collision-free rate 如何变化？
10. 哪些 Link 是主要 collision source？
11. 哪些 collision 属于：
    - adjacent
    - nonadjacent
    - motion-induced
12. 哪些 Link 被重新规划？
13. 哪些 Link 被提前冻结？
14. C1 geometry 是否明显恶化？
15. C2 geometry 是否相比 C1 改善？
16. L02/L07/L01 是否有改善？
17. Robot Plan 的 allowed-body / exclusion constraints 是否真实进入 CAD？
18. collision repair contract 是否真实影响 body？
19. FreeCAD 是否仍不是瓶颈？
20. 当前瓶颈是否变成：
    - free-space estimation
    - collision-aware body planning
    - visual coarse morphology
    - body parameterization
21. 是否已经具备进入 Try-5B 的条件？

--------------------------------------------------
28. 进入 Try-5B 的建议条件
--------------------------------------------------

只有当：

- Connected Joint Rate = 100%
- Floating Link Rate = 0
- interface metrics 不退化
- exact collision 显著降低
- collision-free sweep 有明显提升
- coarse morphology 不显著恶化

时，

才建议进入：

Try-5B
Semantic-Inventory-Guided Link Detailing

--------------------------------------------------
29. 开发顺序
--------------------------------------------------

Phase 1
复用并冻结 A2 interface state

Phase 2
实现 broad-phase + narrow-phase collision evaluator

Phase 3
先重新评价 C0：
得到真实 collision baseline

Phase 4
建立 allowed body region / exclusion regions

Phase 5
运行 C1

Phase 6
分析 C1

Phase 7
加入 visual coarse morphology constraints

Phase 8
运行 C2

Phase 9
统一评价

Phase 10
输出报告

--------------------------------------------------
30. 重要停点
--------------------------------------------------

请先完成：

Phase 1–3

即：

1. 冻结 C0 = A2
2. 实现 exact collision evaluator
3. 区分：
   AABB overlap
   vs
   true geometric collision
4. 重新评价 canonical pose + sampled sweep
5. 输出 collision pair list
6. 输出 per-pair intersection volume / clearance
7. 标出主要 collision-causing links

完成后先停止。

不要立即开始 C1 body replan。

先向我汇报：

- C0 的真实 collision 状况；
- AABB 假阳性比例；
- 哪些 Link/Joint 是主要 collision source；
- 哪些是 expected interface contact；
- 哪些是真正 unintended collision；
- 当前 evaluator 是否足以支持后续 C1。

我确认后再进入 Phase 4。