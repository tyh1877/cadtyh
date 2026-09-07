# RobotCAD Try-4.1B
# Shape-Family Realization & Structural Replanning Pilot

Try-4.1A 已完成并停止。

已知结论：
- Mechanical Topology Graph 有效；
- A0 -> A1 的平均几何指标全部改善；
- Shape-Family Vocabulary 有价值，但效果不稳定；
- 当前主要瓶颈位于：
  1. topology -> shape-family
  2. shape-family -> CAD profile / parameterization
  3. articulated gripper 的 substructure realization
- FreeCAD execution 不是当前主要瓶颈。

本轮不要扩大实验规模。

只研究两个最典型失败 Part：

- R02_P04：complex stepped housing
- R02_P06：gripper

不要运行 Robot C。
不要重新跑三台机器人。
不要增加新的多 Agent 系统。
不要加入多轮 Quality-Gated Repair 主实验。

--------------------------------------------------
1. Try-4.1B 核心研究问题
--------------------------------------------------

RQ1：

当 Mechanical Topology 已经基本正确时，
显式的 Executable Shape-Family Schema
是否能提高 topology -> CAD 的几何实现质量？

RQ2：

当当前 shape family / substructure 明显错误时，
系统能否执行真正的 Structural Replan：

- 删除错误结构；
- 更换 shape family；
- 修改 substructure graph；
- 重建对应 CAD；

而不是：

相同 recipe + 新参数。

--------------------------------------------------
2. 实验条件
--------------------------------------------------

本轮只做：

B0
B1
B2

--------------------------------------------------
B0 — Frozen A1 Baseline
--------------------------------------------------

直接复用 Try-4.1A 的 A1：

Mechanical Topology Graph
-> current CAD planning
-> FreeCAD

不要重新生成 B0。
不要调参。
不要增强。

B0 = frozen A1 result。

原因：

R02_P04 和 R02_P06 中，
A1 都优于 A2，
因此 B0 用 A1 作为最合理 frozen baseline。

--------------------------------------------------
B1 — Executable Shape-Family Realization
--------------------------------------------------

在 B0 基础上增加：

Executable Shape-Family Schema

流程：

Visual Evidence
-> Mechanical Topology Graph
-> Shape-Family Selection
-> Executable Shape-Family Parameters
-> Mechanical Feature Graph
-> CAD IR
-> FreeCAD

关键变化：

Shape Family 不能只是一个自然语言标签。

禁止：

{
  "shape_family": "stepped_housing"
}

然后由 CAD planner 自己猜。

必须展开成足够具体的参数化几何结构。

--------------------------------------------------
3. Shape-Family Schema
--------------------------------------------------

建立：

schemas/
  executable_shape_family_v1.schema.json

docs/
  executable_shape_family_v1.md

每个 family 至少定义：

- required substructures
- required geometric parameters
- optional parameters
- reference frame
- connectivity rules
- symmetry rules
- open-space / gap rules
- allowed CAD strategies
- invalid configurations

--------------------------------------------------
4. R02_P04 stepped housing
--------------------------------------------------

不要只表达：

stepped_housing

至少拆成类似：

- base housing body
- upper stepped cover/body
- proximal cylindrical/joint region
- front / rear transition
- side walls
- local recess / opening if visible
- mounting/interface region

参数至少考虑：

- overall length
- overall width
- overall height
- step_count
- step_positions
- local step heights
- top profile
- side profile
- front radius / chamfer
- rear taper
- joint boss radius
- joint boss depth
- wall / cover thickness if visually supported
- reference frame

不要从 GT STEP 直接读取这些参数给 generator。

参数必须来自允许的视觉/URDF evidence。

GT 只能用于 evaluator。

--------------------------------------------------
5. R02_P06 gripper substructure decomposition
--------------------------------------------------

R02_P06 禁止继续作为一个大：

jaw_linkage

Feature。

保持：

1 URDF link
=
1 Macro-Part output

但内部必须拆成 substructure graph。

至少考虑：

Gripper Macro-Part
├── central carriage
├── left rail
├── right rail
├── left slider
├── right slider
├── left jaw
├── right jaw
├── left linkage
├── right linkage
├── pivot group
└── central/open working gap

如果某些结构从视觉证据无法确认，
允许标：

uncertain / optional

禁止强行虚构隐藏内部机构。

--------------------------------------------------
6. Gripper substructure 参数化
--------------------------------------------------

每个 substructure 至少记录：

- substructure_id
- semantic role
- parent
- reference frame
- approximate bbox
- orientation
- shape family
- symmetry relation
- connection relation
- gap relation
- pivot relation if applicable

例如：

left_jaw / right_jaw：

- jaw length
- jaw thickness
- jaw opening direction
- jaw tip family
- symmetry axis
- spacing

rail pair：

- rail length
- rail spacing
- orientation
- section family

linkage pair：

- link length
- link width
- pivot positions
- connection endpoints

不要把 gripper 实现成：

a few boxes + bars

然后仍然认为 family realization 成功。

--------------------------------------------------
7. Shape Family 必须编译成 Mechanical Feature Graph
--------------------------------------------------

流程必须是：

Topology Graph
↓
Shape-Family Schema
↓
Mechanical Feature Graph
↓
Executable CAD IR
↓
FreeCAD

禁止：

shape family
↓
case-specific FreeCAD Python

所有 case-specific 几何决策必须进入中间表示。

--------------------------------------------------
8. B1 的目标
--------------------------------------------------

B1 不做 iterative repair。

只回答：

> 更完整的 executable shape-family parameterization
> 是否能让 R02_P04 / R02_P06
> 比 B0 更接近正确机械结构？

如果 B1 失败：

保留失败结果。

不要立即进入手工修补。

--------------------------------------------------
B2 — True Structural Replanning
--------------------------------------------------

B2 从 B1 的失败结果开始。

只有当结构 Gate 失败时才触发：

STRUCTURAL_REPLAN

Structural Replan 必须允许：

1. 删除错误 feature group
2. 替换 shape family
3. 修改 topology subgraph
4. 修改 substructure decomposition
5. 修改 CAD construction strategy
6. rebuild affected region / full part when necessary

--------------------------------------------------
9. 什么不算真正 REPLAN
--------------------------------------------------

以下不算 Structural Replan：

- 改 width
- 改 length
- 改 radius
- 改 spacing
- 改 loft section size
- 相同 recipe 换一组参数

这些只能叫：

PARAMETER_UPDATE

只有发生：

shape family change
或
substructure graph change
或
construction strategy change

才记：

TRUE_STRUCTURAL_REPLAN = true

--------------------------------------------------
10. Structural Replan 示例
--------------------------------------------------

R02_P04：

如果：

stepped_housing
-> short rectangular stepped block

明显无法表达 reference structure，

允许：

stepped_housing
→ compound_profile_housing

并重新定义：

- base body
- side profile
- upper cover profile
- joint boss
- rear transition

--------------------------------------------------

R02_P06：

如果：

jaw_linkage
-> boxes + bars

失败，

必须允许：

single jaw-linkage abstraction
→ explicit gripper substructure graph

即：

carriage
+
rail pair
+
slider pair
+
jaw pair
+
linkage pair
+
pivot group
+
working gap

--------------------------------------------------
11. Independent Topology Annotation
--------------------------------------------------

Try-4.1A 的 topology metrics 不是完全独立 GT。

本轮必须先为：

R02_P04
R02_P06

建立：

independent_topology_gt.json

要求：

由 GT STEP / GT reference
离线人工或规则标注：

- node roles
- major substructures
- connectivity
- branch relations
- opening/gap
- symmetry
- attachment relations

重要：

independent topology annotation：

只进入 evaluator。

禁止进入：

B1/B2 generator prompt
Mechanical Topology planner
Shape-Family selector

否则造成 GT 泄漏。

--------------------------------------------------
12. Topology Metrics
--------------------------------------------------

本轮重新计算：

- Node Role F1
- Topology Relation F1
- Component/Region Count Accuracy
- Branch/Fork Accuracy
- Opening/Gap Recall
- Symmetry Relation Accuracy

这些指标必须基于：

independent_topology_gt.json

不能再用当前 Agent 自己写的 target graph 作为 GT。

--------------------------------------------------
13. Shape-Family Gate
--------------------------------------------------

增加一个轻量 Gate：

SHAPE_FAMILY_GATE

检查：

- selected family 是否支持当前 topology；
- required substructures 是否完整；
- family-required open space 是否存在；
- family-required symmetry 是否存在；
- family 参数是否完整。

如果失败：

SHAPE_FAMILY_FAIL

进入 Structural Replan。

--------------------------------------------------
14. Structure Realization Gate
--------------------------------------------------

FreeCAD build 后增加：

STRUCTURE_REALIZATION_GATE

检查：

声明的 substructure
是否真正进入 CAD。

例如 gripper：

计划声明：

- rail_pair
- jaw_pair
- linkage_pair
- working_gap

如果最终 CAD 只有：

- 4 boxes
- 2 bars

且没有对应结构关系，

则：

STRUCTURE_REALIZATION_FAIL

即使 IoU 尚可，
也不能 PASS。

--------------------------------------------------
15. 不做完整多轮 Repair
--------------------------------------------------

Try-4.1B 不做 Try-4.0 那种：

Round 1
Round 2
Round 3

循环。

流程只允许：

B0
↓
B1 initial realization
↓
Structure/Shape Gate
↓
若失败：
一次 B2 Structural Replan
↓
final evaluation

只允许一次 structural replan。

目的：

干净验证 structural replan 是否有价值。

--------------------------------------------------
16. Progressive Freezing 仅保留必要版本
--------------------------------------------------

如果 B1 中某些 major substructure 已正确：

标记：

PROTECTED_SUBSTRUCTURE

B2 不应无原因重做。

例如：

R02_P04：
proximal joint boss 已正确
但 upper housing 错误

则只允许重建：

upper housing / transition

R02_P06：
rail pair 正确
jaw/linkage 错误

则 rail pair 可以冻结。

--------------------------------------------------
17. 评价指标
--------------------------------------------------

几何：

- IoU
- normalized Chamfer
- normalized HD95
- silhouette IoU

拓扑：

- Node Role F1
- Relation F1
- Branch/Fork Accuracy
- Opening/Gap Recall
- Symmetry Accuracy

结构实现：

- Substructure Realization Recall
- Shape-Family Realization Rate
- Required-Feature Coverage

CAD：

- FCStd validity
- reopen
- recompute
- STEP/STL export
- editable parameters
- zero silent fallback

--------------------------------------------------
18. 重点比较
--------------------------------------------------

R02_P04：

B0
vs
B1
vs
B2

重点看：

- stepped housing 是否不再退化成短 block；
- multi-step profile 是否合理；
- joint boss / cover / body / transition 是否空间关系正确；
- IoU/CD/HD95 是否改善。

--------------------------------------------------

R02_P06：

重点看：

- carriage 是否存在；
- rail pair 是否正确；
- jaw pair 是否正确；
- linkage 是否存在；
- pivot 关系是否出现；
- working gap 是否保留；
- 是否仍主要由独立 boxes/bars 构成。

--------------------------------------------------
19. 不允许扩大 vocabulary
--------------------------------------------------

本轮不要新增大量 shape families。

只允许：

为 R02_P04 / R02_P06 当前确实需要的
通用 family
增加 executable schema。

目标不是：

增加更多名字

而是：

让已有 family 真正可执行、可参数化。

--------------------------------------------------
20. 不允许 case-specific template
--------------------------------------------------

禁止：

R02_P04_template
R02_P06_gripper_template
specific_robot_gripper

允许：

compound_profile_housing
rail_slider_pair
jaw_pair
linkage_pair
pivot_pair
terminal_fork

必须保持通用机械语义。

--------------------------------------------------
21. 公平性
--------------------------------------------------

B0/B1/B2 使用：

- same two parts
- same image/text/URDF evidence
- same Codex CLI
- same FreeCAD backend
- same evaluator
- same render settings

B1/B2 不得额外读取 GT geometry 参数。

GT 只用于 evaluator。

--------------------------------------------------
22. 输出文件
--------------------------------------------------

experiments/try4_1B/

  B0/
  B1/
  B2/

  topology_gt/
    R02_P04_topology_gt.json
    R02_P06_topology_gt.json

  shape_family_schemas/
  topology_graphs/
  substructure_graphs/
  feature_graphs/
  cad_ir/
  cad_artifacts/
  contact_sheets/

results/

  geometry_metrics.csv
  topology_metrics.csv
  substructure_metrics.csv
  cad_validity.csv
  try4_1B_report.md

--------------------------------------------------
23. 最终报告必须回答
--------------------------------------------------

1. B0/B1/B2 的主要几何指标；
2. independent topology metrics；
3. B1 的 Executable Shape-Family Schema 是否真正改变 CAD？
4. R02_P04 是否摆脱 short stepped block 退化？
5. R02_P06 是否摆脱 boxes/bars gripper？
6. Substructure Realization Recall 如何变化？
7. 哪些 family 参数最难估计？
8. 哪些 substructure 最难生成？
9. B2 是否发生 TRUE_STRUCTURAL_REPLAN？
10. 如果发生，具体更改了：
    - topology
    - shape family
    - substructure
    - CAD strategy
    中哪些？
11. B2 是否优于 B1？
12. FreeCAD 是否仍然不是主要瓶颈？
13. 当前瓶颈是否已经进一步收敛到：
    - visual -> topology
    - topology -> family
    - family -> parameterization
    - parameterization -> CAD
    - articulated mechanism representation
14. 是否建议进入 Try-4.1C 三机器人完整评估？

--------------------------------------------------
24. 成功判断
--------------------------------------------------

Try-4.1B 不要求两个 Part 完全重建正确。

如果：

R02_P04：
B1/B2 明显提高结构 realization，
并减少 stepped-housing block degeneration；

以及/或者：

R02_P06：
开始形成真实的
carriage + rails + jaws + linkage + gap
结构，而不是 box/bar proxy；

并且：

independent topology / substructure metrics 改善，

则认为：

Executable Shape-Family
+
Structural Replan

值得进入 Try-4.1C。

如果 topology 已正确，
但几何仍明显失败：

结论应明确：

bottleneck = shape-family parameterization / CAD construction

如果 topology 本身仍错误：

结论应明确：

bottleneck = visual -> topology grounding

--------------------------------------------------
25. 执行顺序
--------------------------------------------------

请按以下顺序：

Phase 1
建立 independent topology GT

Phase 2
建立 executable shape-family schema

Phase 3
运行 B1

Phase 4
执行 shape/structure gate

Phase 5
仅对失败 case 执行一次 B2 structural replan

Phase 6
统一评价

Phase 7
输出 report

完成 Try-4.1B 后停止。

不要继续实现 Try-4.1C。