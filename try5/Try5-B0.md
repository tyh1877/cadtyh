# RobotCAD Try-5B0
# Fast Mechanical Evaluator
# Hierarchical Collision Evaluation + Cached Geometry + Selective Exact B-Rep

Try-5A coarse-stage 已冻结。

现在进入 Try-5B0。

IMPORTANT：

1. Try-5B0 不是新的 CAD 生成方法实验；
2. 它是后续 Try-5B Link refinement 的 evaluator acceleration stage；
3. 直接修改现有 try5 主代码；
4. 不创建新的 parallel evaluator/backend；
5. 不修改已经冻结的 Try-5A mechanical definitions；
6. 不改变 Try-5A final CAD；
7. 本轮只优化 evaluation speed；
8. 最终结果必须与 frozen Exact evaluator 做一致性验证。

==================================================
1. 核心目标
==================================================

当前 Try-5A 的 mechanical evaluator 过多依赖：

FreeCAD exact B-Rep common()
distToShape()
逐 pose
逐 link-pair
重复计算。

后续 Try-5B 会频繁修改单个 Link，
如果每轮都重新做全量 Exact B-Rep，
迭代成本过高。

Try-5B0 目标：

建立：

Kinematic Culling
→ Broad Phase
→ Cached Mesh/BVH Narrow Phase
→ Selective Exact B-Rep

并支持：

Dirty-Set Incremental Re-evaluation

要求：

FAST evaluator 用于：
- repair loop
- Link refinement loop
- quick gate

Exact B-Rep 保留用于：
- suspicious pairs
- interface/near-contact
- final mechanical audit

==================================================
2. 不修改冻结的机械定义
==================================================

禁止修改：

- URDF authority
- FK
- joint/interface semantics
- rigid groups
- BICR definition
- forbidden fusion definition
- JR3 definition
- GCFR definition
- collision taxonomy
- Mechanical Meaningfulness Gate
- Repair Scope Arbiter semantics

Try-5B0 只改变：

“如何更快计算这些机械指标”。

==================================================
3. Frozen Reference
==================================================

使用：

Try-5A.5 final frozen Robot A

作为 reference baseline。

先使用当前 Exact B-Rep evaluator
重新得到 reference results：

- per-joint JR3
- 128 coupled configurations
- GCFR
- collision pair list
- collision event count
- intersection volume
- minimum clearance
- BICR
- interface validity

保存为：

EXACT_REFERENCE

后续所有 FAST evaluator 结果
必须与其比较。

==================================================
4. Fast Evaluator 总体架构
==================================================

实现四级流程。

Level 0:
Kinematic / semantic culling

Level 1:
AABB / OBB broad phase

Level 2:
Cached triangle mesh + BVH narrow phase

Level 3:
Selective Exact B-Rep verification

默认 repair loop：

L0 → L1 → L2

只有满足 trigger 条件时进入 L3。

==================================================
5. Level 0 — Kinematic / Semantic Culling
==================================================

在几何碰撞前排除无需检查的 pair。

至少支持：

- virtual frame pair
- same rigid group
- explicitly allowed interface contact
- fixed known-safe internal pair
- pair whose swept bounding regions cannot intersect
- frozen unchanged pair with reusable cached result

输出：

culled_pair_count
remaining_pair_count

必须可审计。

==================================================
6. Level 1 — Broad Phase
==================================================

对剩余 pair 使用：

AABB
优先再增加 OBB，如果已有实现方便。

只用于筛选。

禁止：

AABB overlap = true collision

输出：

broad_phase_candidates

==================================================
7. Level 2 — Cached Mesh/BVH Narrow Phase
==================================================

对每个 CAD revision 的每个 physical Link：

只 tessellate 一次。

缓存：

- triangle mesh
- vertex/face arrays
- BVH/AABB tree
- local bbox
- local OBB
- geometry hash
- revision id

不同 pose 只应用 rigid transform。

不要每个 pose 重新：

- tessellate
- export STL
- rebuild BVH

Mesh/BVH 至少支持：

- collision yes/no
- candidate triangle intersections
- approximate minimum clearance
- collision severity proxy
- pair-level contact status

==================================================
8. Geometry Cache
==================================================

缓存 key 至少包括：

- link_id
- CAD revision/hash
- tessellation parameters

如果 Link 没有被修改：

复用其 mesh/BVH。

如果只有 L03 修改：

只失效 L03 cache。

其它 Link cache 保持。

记录：

cache_hit_rate

==================================================
9. Dirty-Set Incremental Evaluation
==================================================

这是 Try-5B0 的关键。

如果本轮只修改：

L03

不要重新计算所有：

55 link pairs × all poses

只重新计算：

L03 ↔ all relevant links

以及受 L03 影响的：

- local joint sweep
- coupled configurations
- interface neighborhood

其它未修改 pair：

直接复用上一 revision 结果。

最后运行轻量：

global sanity check

==================================================
10. Dirty Dependency Graph
==================================================

建立：

changed_link
→ affected_joint
→ affected_pairs
→ affected_poses/configurations

例如：

L04 modified

必须重算：
- L04 relevant interfaces
- L04 collision pairs
- J03/J04 local sweep if applicable
- all coupled configurations involving L04 geometry transform

但不需要重新 tessellate
未修改的其它 Links。

==================================================
11. Level 3 — Selective Exact B-Rep
==================================================

Exact B-Rep 不删除。

只在以下情况调用：

A. Mesh/BVH 判断 collision

B. approximate clearance < threshold_delta

C. interface / mating region

D. repair candidate 与旧结果非常接近，存在判断不确定性

E. final accepted Link refinement

F. final whole-robot audit

G. random audit sample，用于监控 FAST evaluator drift

==================================================
12. Exact Trigger Policy
==================================================

建立结构化规则，例如：

if mesh_collision:
    exact_check = true

if approx_clearance < delta:
    exact_check = true

if interface_pair:
    exact_check = true

if final_audit:
    exact_check = true

否则：

FAST result 可以直接用于 repair routing。

delta 在 Robot A dev 上选择，
并记录，不用 GT 调参。

==================================================
13. Repair Loop 不再依赖 exact intersection volume
==================================================

FAST repair routing 优先使用：

- collision yes/no
- collision pose count
- collision pair frequency
- approximate clearance
- triangle penetration severity
- region localization

不要求每次计算 exact intersection volume。

Exact volume 只用于：

- selective verification
- final report
- difficult candidate comparison

==================================================
14. FAST / FINAL 两种模式
==================================================

实现统一 evaluator 的两个模式。

FAST_REPAIR_MODE

用于：
- Link refinement
- repair rounds
- quick validation

特点：
- culling
- cached mesh/BVH
- dirty-set
- selective exact

FINAL_AUDIT_MODE

用于：
- final accepted CAD
- paper-level metrics

特点：
- 保留 exact B-Rep verification
- 对所有 FAST suspicious pairs做 exact
- 必要时完整复核冻结 configuration set

不要维护两套独立 evaluator 代码。

==================================================
15. Interface / Attachment 不要完全 mesh 化
==================================================

以下 hard mechanical checks
仍优先保留 exact / deterministic CAD semantics：

- BICR
- body-interface physical connectivity
- forbidden parent-child fusion
- interface frame
- joint axis/origin
- virtual link filtering

Try-5B0 主要加速：

collision / clearance / motion evaluation。

不要为了速度削弱 attachment correctness。

==================================================
16. 一致性实验
==================================================

对 frozen Try-5A.5 final：

比较：

EXACT_REFERENCE
vs
FAST_REPAIR_MODE

至少使用：

A. 全部 per-joint sweep samples

B. 128 frozen coupled configurations

比较：

- collision/no-collision classification
- collision pair detection
- collision-free pose classification
- JR3
- GCFR
- near-contact classification
- repair target ranking

==================================================
17. 最重要的安全要求：不能漏真实碰撞
==================================================

重点计算：

False Negative Rate

即：

Exact = collision
FAST = clear

目标：

0%

开发阶段宁可 FAST 有少量 false positive，
也不要漏掉真实 collision。

同时报告：

False Positive Rate

即：

FAST = collision/suspicious
Exact = clear

允许存在一定比例，
因为这些可以交给 selective Exact 过滤。

==================================================
18. Mechanical Decision Agreement
==================================================

除了 pair classification，
还比较：

Repair Decision Agreement

例如：

Exact evaluator 会把：

L03–L07
列入 repair queue。

FAST evaluator 是否也会列入？

计算：

- repair target recall
- repair target precision
- top-k collision pair agreement

核心目标：

repair target recall = 100%

==================================================
19. Speed Benchmark
==================================================

必须测量：

A. 当前 Exact 全量 evaluator

B. FAST evaluator cold-cache

C. FAST evaluator warm-cache

D. Dirty-set 单 Link 修改场景

至少记录：

- total wall time
- per-stage time
- tessellation time
- BVH build time
- broad phase time
- mesh narrow phase time
- Exact calls
- Exact time
- cache hit rate

==================================================
20. 单 Link 修改模拟
==================================================

模拟后续 Try-5B 场景：

只修改一个 Link，
例如：

- upper arm
- wrist
- gripper-side link

不要真正优化 geometry，
只做一个合法小参数变化用于 benchmark。

然后比较：

Full Exact Re-evaluation
vs
Dirty-Set FAST Re-evaluation

确认：

未修改 pair 的结果来自 cache，
修改相关 pair 被重新计算。

==================================================
21. 建议性能目标
==================================================

硬目标：

- False Negative Rate = 0%
- JR3 classification 与 Exact 一致
- GCFR 与 Exact 一致或仅有可解释极小偏差
- repair target recall = 100%

性能目标：

希望：

Full FAST evaluator
>= 3× faster than current Exact

更理想：

>= 5× faster

Dirty-set single-Link re-evaluation：

希望：

>= 10× faster

这些是建议目标，
如果未达到，不要伪造。

==================================================
22. Final Exact Audit
==================================================

所有 FAST evaluator 判断通过后：

对 frozen final Robot A
执行 FINAL_AUDIT_MODE。

确认：

- GCFR
- JR3
- collision pair list
- BICR
- interface validity

与冻结 Try-5A mechanical conclusions
没有被改变。

==================================================
23. Dataflow Audit
==================================================

必须证明：

CAD revision
→ mesh cache/hash
→ BVH
→ transformed pose geometry
→ FAST collision
→ repair queue

真实工作。

以及：

changed Link
→ dirty dependency set
→ selective recompute

真实工作。

做 counterfactual：

修改一个 Link geometry，
应只导致该 Link cache invalidation
和其相关 collision result变化。

==================================================
24. 不允许做的事情
==================================================

本轮禁止：

- 修改 Robot A CAD shape
- 优化 GCFR
- 修改 interface family
- 修改 knowledge base
- 开始 Link refinement
- Try-5B.1 geometry generation
- 加入新的 repair strategy
- Robot B
- FEA/dynamics

只优化 evaluator。

==================================================
25. 代码原则
==================================================

继续直接修改当前 try5 主代码。

不要创建：

- fast_evaluator_v2 parallel pipeline
- copied evaluator tree
- duplicated backend

建议模块化为：

evaluation/
  mechanical/
    collision_fast.py
    collision_exact.py
    geometry_cache.py
    dirty_set.py
    evaluator.py

具体路径可按当前仓库结构调整。

保持：

one evaluator
+
multiple evaluation modes

==================================================
26. 建议 Git 节点
==================================================

至少保存：

Commit 1:
geometry cache + mesh/BVH

Commit 2:
dirty-set evaluation

Commit 3:
selective exact trigger

Commit 4:
benchmark + validation

不用复制代码目录。

==================================================
27. 输出结果
==================================================

至少输出：

fast_vs_exact_pair_results.csv

fast_vs_exact_pose_results.csv

repair_target_agreement.csv

speed_benchmark.csv

cache_statistics.csv

dirty_set_benchmark.csv

selective_exact_calls.csv

try5B0_fast_evaluator_report.md

==================================================
28. 最终报告必须回答
==================================================

1. 原 Exact evaluator 一次完整128-config评估耗时多少？
2. FAST cold-cache耗时多少？
3. FAST warm-cache耗时多少？
4. Full evaluator speedup是多少？
5. 单 Link dirty-set speedup是多少？
6. tessellation是否只对每个 revision执行一次？
7. cache hit rate是多少？
8. AABB/OBB筛掉多少 pair？
9. Mesh/BVH筛掉多少 pair？
10. 最终多少 pair/pose需要 Exact B-Rep？
11. Exact call数量降低多少？
12. False Negative Rate是多少？
13. False Positive Rate是多少？
14. 是否漏掉任何 Exact true collision？
15. JR3是否与 frozen Exact一致？
16. GCFR是否与 frozen Exact一致？
17. collision-free pose classification是否一致？
18. repair target recall是多少？
19. repair target precision是多少？
20. interface/BICR hard gate是否保持原定义？
21. dirty-set是否真实只重算受影响对象？
22. geometry cache是否正确失效？
23. FAST evaluator是否适合后续 refinement loop？
24. FINAL_AUDIT_MODE是否仍能复现 Try-5A mechanical result？
25. 当前主要耗时还在哪里？

==================================================
29. 成功判断
==================================================

Try-5B0 成功的最低要求：

- 不漏真实碰撞；
- mechanical decision基本与 Exact一致；
- repair target recall = 100%；
- frozen JR3/GCFR结论不变；
- evaluation wall time显著下降。

如果 mesh/BVH 无法达到零 false negative：

不要删除 Exact evaluator。

调整：

- mesh resolution
- near-contact threshold
- exact trigger policy

直到 FAST evaluator 足够保守。

==================================================
30. 完成后停止
==================================================

请一次性完成：

- implementation
- validation
- speed benchmark
- dirty-set benchmark
- exact comparison
- final audit
- report

中间无需暂停汇报。

全部完成后一次性汇报结果。

不要开始 Try-5B.1。