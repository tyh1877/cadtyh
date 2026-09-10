# Try-5B1 Mechanically Constrained Link Refinement Pilot

## Outcome

PASS. 三个 pilot 已完成 F0/F1/F2、结构化 refinement、evaluator-only 几何/语义评估及机械审计。F2 相对 F0 明显改善，但 F2 的 mean IoU 略低于 F1；Semantic/Topology 增益没有转化为额外 IoU 增益。

## Required answers

1. L03 arm carrier、L04 wrist housing、L07 gripper support；三者覆盖细长承载件、局部壳体和末端复杂支承。

2. F0 分别由 central_web/wrist_block/straight_beam 名称驱动，但实际为圆柱连接体与简单杆。

3. 三者均有 primitive collapse，L03/L04 的语义 family 尤其没有展开。

4. 每个 EvidencePack 含六个全局视图、六个原图裁剪及轮廓、截面、厚度、对称、开口、曲率和遮挡状态。

5. Inventory 详见 semantic_inventories/*.json；E3 隐藏件均未实体化。

6. 图中显式记录 continues_into/supports/surrounds/symmetric_with/separated_by_gap 等关系。

7. F1: L03 central_web；L04 compound_profile_housing；L07 gripper_support。

8. 全部真实 dispatch 并写入 FCStd；9. Family Realization Rate=100.0%；10. silent downgrade=0。

11. mean IoU F0/F1/F2=0.1010/0.1557/0.1520。

12. mean nChamfer=0.1019/0.0797/0.0801；nHD95=0.3005/0.2353/0.2337。

13. mean silhouette IoU=0.3276/0.4041/0.4003。

14. IoU 提升最大 L03；15. F2 IoU 最低、最困难 L04。

16. mean Semantic F1=0.000/0.915/1.000；17. Relation F1=0.000/0.756/1.000。

18. refined-condition unsupported features=0；19. meaningless geometry=0。

20. refinement rounds=8；21. scopes={'P3': 2, 'P2': 4, 'P1': 2}；22. true whole-link replans=2。

23. rollback=4；24. structured diagnosis found cylindrical carrier, generic housing, missing transverse support/gap；25. hallucinated component=0。

26. BICR=100.0%；27. relevant JR3 F2=[{'joint_id': 'J02', 'jr3': 1.0, 'full_range_pass': True}, {'joint_id': 'J03', 'jr3': 1.0, 'full_range_pass': True}]。

28. interface frames/contracts unchanged=True；29. GCFR F0 frozen=0.914062, F1=0.914062, F2=0.914062。

30. dirty FAST wall F1/F2=0.989/1.288s；31. P2/P3 后 Selective Exact local audit=True，并完成 F2 全量 Exact。

32. GT leakage=0；生成 worker 的输入 job 不含 GT 路径或 annotation。

33. body-family generator 仍限制可覆盖 family 数，但三种 pilot family 已可执行；34. 主要瓶颈转为图像到精确 profile/section 参数 grounding。

35. 是否进入 B2 取决于相对几何改善且机械硬门通过；本轮不启动 B2。
