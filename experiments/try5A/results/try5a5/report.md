# Try-5A.5 最终报告

状态：**COMPLETE（达到协议硬门；未达到95%理想GCFR）**

## 结论

实验从六视图、工程文本、sanitized URDF 与冻结通用知识库重新开始，生成
Robot A 的11个 physical links、全部 joint interfaces 和整机粗粒度 FreeCAD。
七个 moving joints 的独立 JR3 均为100%；128组固定种子 Sobol coupled
configurations 中117组有效，最终 GCFR=91.40625%。因此达到 Whole-Robot
Coarse K1/K2/K3 的90%硬门。剩余11个高折叠碰撞构型保留为 UNRESOLVED，
95%理想目标未达到。

| Round | GCFR | Collision events | Total volume (mm³) | Max volume (mm³) |
|---|---:|---:|---:|---:|
| 0 | 56.25% | 127 | 108512.901 | 10624.060 |
| 1 | 80.46875% | 64 | 30418.985 | 2858.181 |
| 2 | 89.0625% | 52 | 24111.256 | 2855.963 |
| 3 | 91.40625% | 46 | 20309.269 | 2851.891 |

## 最终问题 1–25

1. **是否真正从零开始？** 是。Skeleton、classification、Robot Plan、interface selections、contracts、LinkCoarseSpecs、CAD IR 和 CAD 全部重新生成。
2. **是否读取旧 Robot A CAD/design答案？** Generator/repair 没有读取 A2、K1、A.4 CAD 或历史 design state；旧通用代码逻辑允许复用。
3. **多少 physical/virtual links？** 11 physical，1 virtual（L11 tool frame）。
4. **多少 moving/fixed/mimic joints？** 7 moving，4 fixed；J09 是1个 mimic joint。
5. **Robot Plan 是否重新生成？** 是，并由图像尺度、工程文本语义与 URDF 拓扑约束后续 specs/CAD。
6. **各 joint family？** J00 nested rotary；J01/J02 fork-pin；J03/J05 coaxial rotary；J04/J06/J07 planar mount；J08/J09 rail slider；J10 end-tool virtual interface。
7. **是否出现 CUSTOM_INTERFACE？** 没有，custom rate=0。
8. **Knowledge Base 是否被冻结？** 是，冻结 SHA-256 为 670933aaa45b68ef4c86e54f554e94b901eefb2af112267c261ce32093641aad。
9. **是否增加 Robot-A-specific knowledge？** 没有。
10. **所有 physical links 是否生成？** 是，11/11。
11. **FCStd/STEP/STL 是否有效？** 是；所有 link 与 assembly 完成导出、reopen 和 recompute，silent fallback=0。
12. **BICR 是否100%？** 是。
13. **存在 physical floating 吗？** 不存在；rigid subassembly 使用显式刚性约束。
14. **存在 accidental parent-child fuse 吗？** 不存在。
15. **存在 virtual solid 吗？** 不存在，L11 只保留 frame。
16. **出现 meaningless patch 吗？** 没有；Meaningless Patch Count=0，缺失 provenance 的 negative control 被拒绝。
17. **每个 moving joint 的 JR3？** J00/J01/J02/J03/J05/J08/J09 均为100%。
18. **哪些 joint full-range PASS？** 七个 moving joints 全部通过 q_min/25%/50%/75%/q_max。
19. **哪个 joint 最难？** J02；开发阶段 q_min 曾发生 shoulder/forearm 邻域碰撞，最终通过 limit-stop contact contract 与 R3 设计修复。
20. **Fixed joint 是否正确 rigid？** 是，J04/J06/J07 为零相对DOF的实体 mount；J10 是固定 virtual frame。
21. **Prismatic joint 是否正确滑动？** 是，J08/J09 使用 keyed rail/carriage，完整 stroke 通过且其余五个DOF被几何拒绝。
22. **Mimic joint 是否正确联动？** 是，J09 确定性绑定 J08，multiplier=-1、offset=0。
23. **Round 0 GCFR？** 56.25%。
24. **Round 1/2/3 GCFR？** 80.46875%、89.0625%、91.40625%。
25. **最常见 collision pair？** 最终为 L01–L04 和 L00–L04，各6/128；L01–L04 最大交叠体积更高。

## 最终问题 26–50

26. **Global Collision Graph 是否驱动 repair？** 是；每轮 edge frequency、poses 与 volumes 进入 scheduler 和现有 Repair Scope Arbiter。
27. **R0/R1/R2/R3/R4 数量？** R0=0、R1=6、R2=11、R3=16、R4=0。
28. **是否真实触发 R4？** 没有；R1–R3 已达到90%硬门，没有足够证据解冻 interface family。
29. **R4 是否更换 family？** 不适用。
30. **提前冻结多少 Link/region？** Round0–3 的 collision graph 涉及全部11个 physical links，因此没有无依据提前冻结；final acceptance 后11/11全部冻结。
31. **Rollback 多少次？** 1次。35 mm axial-offset candidate 导致相邻接口回归，已回滚到18 mm方案。
32. **Events/volume 如何变化？** Events 127→64→52→46；total volume 108512.901→30418.985→24111.256→20309.269 mm³。
33. **Final GCFR？** 91.40625%，即117/128。
34. **是否达到90%？** 是。
35. **是否达到95%？** 否。
36. **存在 unresolved configurations？** 是，11/128；均保留在 whole_robot_motion.json 与 final collision graph。
37. **Whole-robot playback 是否成功？** 是，home→extended→folded→side→wrist/gripper→return home 六姿态均 exact-collision-free。
38. **CAD links 是否随 FK 多关节运动？** 是；每个 playback pose 同时改变多个 joint，并对11个 physical rigid groups 应用 URDF FK。
39. **EE pose/FK 是否正确？** 是；L11 frame 来自相同确定性 FK 和 mimic state。
40. **Geometry 指标？** Whole IoU=0.13924、whole silhouette IoU=0.24854、mean per-link IoU=0.02318、nChamfer=0.05328、nHD95=0.21963。细节保真度仍低。
41. **Morphology 是否严重退化？** 没有按计划尺度发生 collapse：最小宽度比例0.72、长度保持、silhouette retention约86.8%；但绝对外观质量仍有限。
42. **Meaningfulness Gate 是否阻止 metric gaming？** 是；所有正式 feature 具备8项 provenance/role 字段，arbitrary box negative control 被拒绝。
43. **FreeCAD 是否仍不是主要瓶颈？** 功能上不是；所有 CAD/STEP/STL/reopen/exact checks 成功。计算时间较长但未阻塞方法。
44. **当前最大瓶颈？** 高折叠 coupled configurations 中 shoulder/base 与 wrist/gripper 的非邻接碰撞，以及较低的 coarse visual fidelity。
45. **达到 Whole-Robot Coarse K1？** 是。
46. **达到 Whole-Robot Coarse K2？** 是，GCFR超过90%硬门。
47. **达到 Whole-Robot Coarse K3？** 是：BICR=100%、DOF/fixed/prismatic/mimic语义正确、无 floating/fusion/virtual/meaningless geometry。
48. **满足进入 Try-5B 条件？** 尚不建议立即进入。A.5硬门已过，但最好先处理11个 unresolved configurations并改善 morphology。
49. **若不进入，还缺什么？** 最后一项是把 GCFR 从91.41%推进到至少95%，同时提高 whole/per-link silhouette。
50. **是否值得冻结粗建模架构？** 值得冻结核心架构：clean input、knowledge contract、interface-first CAD、FK/exact evaluator、collision graph、R0–R4与progressive freezing；具体 body morphology 参数不应冻结。

## Dataflow, leakage and reproducibility

真实消费链为 Images/Text/URDF → Robot Plan → frozen KB → Interface Contract →
motion clearance → LinkCoarseSpec → CAD IR → FreeCAD。修复链为 coupled exact
collision → Global Collision Graph → Repair Arbiter → upstream design update →
selective rebuild。Joint-limit、interface-family 和 local-body 三个 counterfactual
均改变了对应 sweep、CAD 或 motion metrics。

Generator/repair 未读取 GT 或历史 Robot A 答案；GT 仅在最终 geometry evaluator
中使用。正式128配置与 Round-3 语义复跑得到相同 GCFR、JR3、collision rows。
重型 FCStd/STEP/STL 与逐姿态 mesh 留在忽略目录，tracked manifest 保存其 hash。
