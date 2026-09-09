# Try-5A.4 完成实验报告

状态：**COMPLETE（协议规定的三关节 pilot 范围）**

## 结论

Try-5A.4 的七个历史缺口已经补齐。J01/J02/J03 的 M2 CAD 现在具有：真实
A2/K1 基线重放、仓库 URDF FK 世界变换、相互独立的 parent/child 刚体、各自
body 的严格附着、可约束五个非预期自由度的 fork-pin 或 coaxial-bearing 几何、
由预先计算 swept STEP 驱动的局部 body replan，以及 FreeCAD exact B-Rep
运动验证。结论限定在三个 pilot joint，不扩张为整机 K3。

| 条件 | Parent attachment | Child attachment | BICR | Collision-free poses | JR3 | Collision events | Swept collision volume |
|---|---:|---:|---:|---:|---:|---:|---:|
| M0 | 0% | 0% | 0% | 30% | 0% | 21 | 23887.204 mm³-samples |
| M1 | 100% | 100% | 100% | 80% | 80% | 6 | 15122.260 mm³-samples |
| M2 | 100% | 100% | 100% | 100% | 100% | 0 | 0 |

M2 的 30 个冻结姿态全部通过；J01/J02 最小间隙为 0.6 mm，J03 为 0.2 mm。

## 最终问题 1–35

1. **选择了哪三个关节，为什么？** J01（`shoulder_housing → upper_arm_link`）、J02（`upper_arm_link → forearm_link`）、J03（`forearm_link → wrist_gripper_body`）；均由真实 Robot A role transition 自动选择。
2. **URDF type/axis/limits？** 三者均为 revolute，局部轴均为 `[0,1,0]`；J01 `[-1.937315,1.867502]`、J02 `[-1.605703,2.111848]`、J03 `[-2.146755,1.745329]` rad。
3. **K0/K1 families？** J01、J02 均为 `fork_pin_interface → fork_pin_interface`；J03 为 `coaxial_rotary_interface → coaxial_rotary_interface`。
4. **family 新增了什么 motion rules？** Rotary families 增加 URDF-axis rotation、五个 constrained DOF、parent/child ownership、radial/axial/swept clearance、禁止跨 joint fuse、参数化 construction 和 exact sweep verification；fork-pin 具体化为双叉耳/贯穿 pin/child bore，coaxial 具体化为双 bearing/inner rotor/axial shoulders；rail、fixed mount 和 virtual tool family 也分别加入 prismatic、全约束和零实体规则。
5. **M0/M1/M2 是什么？** M0 直接读取并哈希 A2/K1 FCStd/IR；M1 用同一 K1 family 构造可执行 pin/bearing 和严格 rigid groups，但不重规划 body；M2 先冻结 child/interface swept STEP，再经 Arbiter 的 R2 决策让 parent body 消费 sweep bbox 重规划。
6. **Parent Attachment Rate？** `0% → 100% → 100%`。
7. **Child Attachment Rate？** `0% → 100% → 100%`。
8. **BICR？** `0% → 100% → 100%`。
9. **还有 floating interface 吗？** M0 有六个未附着 interface side；M1/M2 为零。
10. **发生 parent-child accidental fuse 吗？** 没有；两侧始终是独立 FreeCAD top-level rigid objects。
11. **Forbidden Fusion Count 是否为零？** 是，M0/M1/M2 均为零。
12. **Rigid groups 正确吗？** 是；M1/M2 的 body 与本侧 interface 均形成单一 connected solid，跨 joint 保持分离。
13. **CAD 是否真的保持两个独立刚体？** 是；FCStd/STEP 中分别保存 parent/child group，并由不同 FK transform 驱动。
14. **URDF FK 能否驱动 CAD？** 能。使用 canonical `kinematics.py`；axis error=0°、center error=0 mm、relative-transform 最大误差 `6.94e-18`，并记录所有 descendant 与 L11 EE pose。
15. **生成 motion playback 吗？** 是；每个 joint/condition 都有实际 FreeCAD B-Rep tessellation contact sheet，M2 各有完整 10-frame GIF。
16. **Collision-free pose rate？** M0 30%、M1 80%、M2 100%。
17. **JR3？** M0 0%（attachment hard gate 失败）、M1 80%、M2 100%。
18. **哪个 joint 首次获得非零 interval？** 三者均在 M1 首次获得：J01 80%、J02 90%、J03 70%。
19. **有完整 requested range collision-free joint 吗？** 有；J01/J02/J03 在 M2 的 q_min、八分位采样、q=0 和 q_max 全部通过。
20. **Swept clearance 是否真实影响 CAD？** 是；swept STEP 在 M2 前生成并冻结 hash，M2 CAD IR 引用该 hash，planner 用其 bbox 决定 side rail 与 rear bridge；limit counterfactual 会改变下游 parent bbox。
21. **M1→M2 collision 改善？** 是；events `6→0`、pose rate `80%→100%`、swept collision volume `15122.260→0`。
22. **仍有哪些 collision？** 在冻结的 parent/child 加下游 nonadjacent neighbor 采样范围内没有 M2 collision。连续采样间的解析证明不在本协议要求内。
23. **哪些 repair scope？** J01/J02/J03 均由实际 `repair_scope_arbiter.arbitrate` 选择 `R2_BODY_REGION_REPLAN`。
24. **执行 R4 吗？** 没有；R2 一轮即通过，未满足 R4 触发条件。
25. **R4 改变 family 吗？** 不适用；没有执行 R4。
26. **出现 meaningless patch 吗？** 没有；所有 feature 均具备 role、provenance、knowledge node、owning group 与 CAD strategy。
27. **Meaningfulness Gate 有效吗？** 是；全部正式 feature 通过，缺少上述字段的 `gap_box` negative control 被拒绝。
28. **VLM 是否仅作辅助？** 本轮没有使用 VLM；scope、motion 和 acceptance 全部由确定性证据决定，VLM 未充当 judge。
29. **Knowledge 是否不仅改变名称？** 是；fork-pin 与 coaxial family 产生不同的 parent/child topology，family counterfactual 改变实际 CAD；DOF gate 对对应 pin/bore 或 bearing/rotor 几何执行。
30. **达到哪一级？** 三个 pilot 均达到 K1 Pose-Driven、K2 Collision-Valid 和 K3 Mechanically Realized。
31. **FreeCAD 是否仍不是瓶颈？** 是；两阶段 CAD、STEP sweep、exact collision 和 pose mesh 全部自动完成。
32. **当前最大瓶颈？** 将三关节局部方法扩展到 Robot A 全部 physical joints，同时控制 coarse morphology；不是 FreeCAD API。
33. **值得扩展到全部 physical joints 吗？** 值得；三种代表性关节均通过，且 counterfactual/dataflow 已闭环。
34. **具备进入整机 coarse motion reconstruction 的条件吗？** 具备；下一阶段应保持相同 FK、rigid group、sweep-first 和 exact-collision gates 扩展全机。
35. **具备进入 Try-5B 的条件吗？** 尚不直接进入；应先完成整机 coarse motion reconstruction。A.4 pilot 本身已完成，但整机 K3 是 Try-5B 前的工程门。

## 数据流、碰撞与辅助指标

真实链路为：URDF joint/limits → repository FK → K1 knowledge family → motion
contract → CAD IR → family-specific FreeCAD B-Rep → pre-M2 swept STEP → Repair
Scope Arbiter → M2 body planner → exact B-Rep evaluation。Joint-limit、family 和
clearance 三种 counterfactual 在三个 pilot 上全部改变相应下游 CAD。

正式 collision judge 只使用 B-Rep `common/distToShape`；AABB 仅作 broad-phase
记录。表中保留 `EXPECTED_INTERFACE_CONTACT`、`ADJACENT_UNINTENDED_COLLISION`、
`NONADJACENT_COLLISION`、`MOTION_INDUCED_COLLISION` 与 `CLEAR` taxonomy。

辅助 geometry mean（非成功门）：M0/M1/M2 voxel IoU 分别约
0.0264/0.1105/0.0276，nChamfer 约 0.2330/0.1884/0.2677，nHD95 约
0.5331/0.5790/0.6599，silhouette IoU 约 0.1396/0.1659/0.1160。M2 的 appearance
下降被明确保留；本轮按协议优先 motion，不用 GT 调参。

## 复现与限制

运行：`.venv/Scripts/python.exe experiments/try5A/scripts/run_try5a4.py`。
数值表已确定性复跑，collision table 与 joint-range metrics 字节级一致。生成器
未读取 GT；GT 仅在 CAD/motion 冻结之后进入辅助 geometry evaluator。重型 FCStd、
STEP、STL 和逐帧 mesh/render 位于 Git 忽略的 `artifacts/try5a4_completion/`，其
hash 保存在 `cad_artifact_manifest.json`。
