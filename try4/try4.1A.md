# RobotCAD Try-4.1A
# Representation Pilot: Topology Graph + Shape-Family Vocabulary

目标：
验证 Try-4.0 的主要瓶颈是否可以通过：

1. Mechanical Topology Graph
2. CAD Shape-Family Vocabulary

得到改善。

本轮不研究：
- 新的 Repair 机制
- Quality-Gated Selective Repair
- 多 Agent
- 全部 3 台机器人
- 完整 Try-4.1

只使用 Try-4.0 中 4 个最典型的困难 Macro-Part。

优先包含：
- R02_P02：central web vs parallel rods
- 一个复杂 stepped housing
- 一个 fork / slot 类 Part
- R02_P06 gripper

保持：
- 同一批输入
- 同一 Codex CLI
- 同一 FreeCAD backend
- 同一 evaluator
- 不修改 GT
- 不增加 repair round

--------------------------------------------------
A0 — Frozen Try-4.0 Baseline
--------------------------------------------------

直接复用 Try-4.0 当前生成流程和结果。

流程：

Visual/Semantic Evidence
→ current Mechanical Feature Graph / planning
→ CAD IR
→ FreeCAD

禁止重新调参或增强 A0。

A0 作为 frozen baseline。

--------------------------------------------------
A1 — + Mechanical Topology Graph
--------------------------------------------------

在 CAD planning 前增加：

Mechanical Topology Graph

流程：

Visual Evidence
→ Mechanical Topology Graph
→ current Feature/CAD planning
→ CAD IR
→ FreeCAD

Topology Graph 必须表达：

Nodes:
- functional body/substructure
- structural member
- joint region
- open space / gap
- interface region

Relations 至少支持：
- connected_to
- branches_into
- parallel_to
- attached_at_end
- attached_on_side
- separated_by_gap
- symmetric_with
- encloses / surrounds

例如 R02_P02 不应只表达：

two bars

而应能够表达：

main_web
→ branches_into terminal_fork
→ left_prong / right_prong
→ separated_by gap

要求：
- A1 不新增 shape-family vocabulary；
- 尽量保持 A0 的 CAD operation vocabulary；
- 目的是单独验证 Topology Graph 的作用。

保存：
mechanical_topology_graph.json

--------------------------------------------------
A2 — + Shape-Family Vocabulary
--------------------------------------------------

在 A1 基础上增加：

CAD Shape-Family Vocabulary

流程：

Visual Evidence
→ Mechanical Topology Graph
→ Shape-Family Selection
→ Mechanical Feature Graph
→ CAD IR
→ FreeCAD

先冻结一个小 vocabulary，不要做大型模板库。

建议只支持 8–12 个通用 family，例如：

- straight_link_body
- single_web
- tapered_web
- terminal_fork
- dual_side_plate
- u_channel
- revolved_joint_housing
- stepped_housing
- open_slot
- flange
- rail_slider_pair
- jaw_linkage

禁止：
- robot-specific template
- case-specific template
- UR5_upper_arm 等具体机器人命名

Shape family 必须是可泛化机械结构。

例如：

Topology:
single central member
+ terminal bifurcation

Shape family:
tapered_web
+ terminal_fork

然后再转成具体 CAD operations。

--------------------------------------------------
公平性要求
--------------------------------------------------

A0/A1/A2 必须保持：

- same 4 parts
- same images / text / URDF context
- same Codex model
- same FreeCAD backend
- same evaluator
- same execution settings
- no repair
- no post-generation manual correction

A1/A2 多出的规划调用允许记录为额外方法成本。

--------------------------------------------------
评价指标
--------------------------------------------------

继续报告：

- IoU
- Chamfer
- HD95
- Mechanical Feature Recall
- CAD validity
- export/recompute success

新增结构指标：

1. Component/Region Count Accuracy
2. Branch/Fork Accuracy
3. Opening/Gap Recall
4. Topology Relation F1

同时保存统一 contact sheet：

GT | A0 | A1 | A2

人工观察只作为开发诊断，不作为正式主指标。

--------------------------------------------------
重点检查
--------------------------------------------------

对于每个 Part，明确回答：

1. A0 的主要结构错误是什么？
2. A1 是否正确表达了机械 topology？
3. A1 的 topology 是否真正影响 CAD 生成？
4. A2 是否选择了更合理的 shape family？
5. 是否仍退化成 box/cylinder/parallel rods？
6. topology 指标是否改善？
7. 几何指标是否也同步改善？
8. 哪个 Part 改善最大？
9. 哪个 Part 仍然失败？

特别关注 R02_P02：

A0:
parallel rods

期望 A1/A2 能逐步趋向：

single central web
+
terminal fork
+
proximal/distal joint structure

--------------------------------------------------
成功判断
--------------------------------------------------

Try-4.1A 不要求 4 个 Part 全部成功。

如果观察到：

A0 < A1
在 topology correctness 上明显改善；

并且：

A1 < A2
在 shape-family correctness / geometry 上继续改善；

则认为：

Mechanical Topology Graph
+
Shape-Family Vocabulary

值得进入 Try-4.1B。

如果 A1 topology 正确但 CAD 仍错误：
说明瓶颈主要在 topology → shape family / CAD translation。

如果 A2 仍然 topology 错：
说明瓶颈仍然在 visual → topology grounding。

--------------------------------------------------
输出
--------------------------------------------------

experiments/try4_1A/

  A0/
  A1/
  A2/

  topology_graphs/
  shape_family_plans/
  cad_artifacts/
  contact_sheets/

results/
  geometry_metrics.csv
  topology_metrics.csv
  feature_metrics.csv
  try4_1A_report.md

--------------------------------------------------
最终报告
--------------------------------------------------

完成后只回答：

1. A0/A1/A2 的主要指标；
2. 4 个 Part 各自的结构变化；
3. Topology Graph 是否有效；
4. Shape-Family Vocabulary 是否有效；
5. 当前瓶颈位于：
   - visual → topology
   - topology → shape family
   - shape family → CAD
   - FreeCAD execution
6. 是否建议进入 Try-4.1B Structural Replanning Pilot。

完成 Try-4.1A 后停止，不要继续实现 Try-4.1B。