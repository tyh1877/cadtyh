# 本次结果重新界定：URDF 驱动的粗几何模板试验

当前分类：`URDF_DRIVEN_COARSE_GEOMETRY_TEMPLATE_PILOT`。
历史运行 `codex_agent_v1` 已就地归档；完整 Try-3 尚未完成。
本文件取代原报告中的方法有效性解释。原报告与原 PASS 审计完整保存在
`../archive/codex_agent_v1_reclassification/`，仅供历史追溯。

## 保留的事实

- 已记录 15/15 整机版本、189/189 link/version 的 FCStd/STEP/STL 导出，
  693 条 FreeCAD 操作和 15 个装配重开检查。它们说明当前操作子集可执行。
- 所有历史数值表、模型、图像、原始运行输出与冻结哈希保持不变。
- V0/V1/V2 名称保留为历史目录标识；应解释为 Box、Loft+两端圆柱、
  调整尺寸并增加法兰三种模板条件，不是已经实现的完整 agent 消融。
- 零件 FCStd 含原生特征；整机通过 STEP 重导入建立 Part::Feature。
  导出/打开成功不能证明关联式参数修改、重算或运动验证通过。

## 撤回的结论

- 撤回“完整 Codex-agent Try3 实验已完成”。
- 撤回“V1 指标改善验证了 Global-to-Local visual grounding 有效”。
- 撤回“V2 指标改善验证了 MEP 或 Interface-first 有效”。
- 撤回“当前三案例 holdout 提供未触碰的确认性验证”。五台案例均已查看，
  后续全部作为方法开发案例；CSV 中 development/holdout/all 标签仅保留历史分组。
- 不以原 completion_audit 的 PASS 或全勾选清单证明上述科学结论。

## 直接代码证据

`scripts/codex_agent_common.py::link_geometry` 使用 URDF 偏移、工程尺度和
版本常数决定尺寸；未从视觉证据推断逐 link 截面和形状。
`scripts/generate_codex_agent_plans.py::build_link_artifacts` 接收 mep/interface
参数却不消费其决策，直接按版本选择 Box、Loft、Cylinder 和 Fuse。
逐 link 视觉特征通过 `visible[index % len(visible)]` 循环分配；这不是
逐 link 图像判断。SkillCall 与 IR 并行生成，后端直接执行 IR。
去掉 MEP/interface 或改变视觉描述，不能据此保证生成几何改变。

## 指标解释限制

原数值仅描述这些模板在旧评价器下的输出，不承担 agent 架构因果解释。
V2 轴线误差在评价代码中直接填写 0，不能作为 B-Rep 实测证据。
primitive_proxy 仅以是否有 Loft 判断，不能证明摆脱粗几何。
接口 gap 是关节中心到采样表面距离之和，不是配合面间隙；AABB 重叠
不是实体干涉体积；尚未完成真实 ICS、clearance/penetration/motion 检查。
可见特征的计划计数和预设执行零值不是独立视觉正确性评估。
路径字符串扫描也不能证明交互会话未接触历史 GT 或结果信息。

## 按 try3.md 重新判断

| 研究问题 | 当前可支持结论 |
| --- | --- |
| RQ1：局部视觉是否改善细粒度几何 | 未有效验证 |
| RQ2：MEP/接口规划是否改善简化与断连 | 未有效验证 |
| RQ3：机械技能是否可靠落到可编辑 CAD | 仅基础 FreeCAD 操作执行得到有限验证 |

完整 Try-3 仍需要真实逐 link 观察、消费 MEP/共享接口的建模决策、
Feature Graph→SkillCall→IR 编译链、结构细节、真实机械评价和参数化装配。
本次只完成重新界定与归档，没有实施这些后续步骤。
