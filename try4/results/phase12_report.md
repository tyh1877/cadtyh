# Try-4 Phase 1＋2 报告

已完成本轮要求的参考准备与外观建模标准，等待用户确认 Phase 3。
本轮没有启动 T0/T1/T2，没有生成重建 Macro-Part 或完整机械臂装配。
图中几何全部是原生 GT STEP 的参考渲染，不能作为 AI 重建成果。

## 三台机器人与划分

| ID | 来源 | 角色 | 机械臂 DOF（不含夹爪） | Macro-Part 数 | 导入叶组件/实体 |
| --- | --- | --- | ---: | ---: | ---: |
| R01 | PincherX-100 | DEV_A | 4 | 5 | 7/9 |
| R02 | ViperX-300s | DEV_B | 6 | 7 | 24/24 |
| R03 | ReactorX-200 | TRANSFER | 5 | 6 | 9/16 |

共 18 个语义 Macro-Part，覆盖 40 个源叶组件和 49 个实体。
每个源叶组件只分配一次；compound 内的多个实体随所属组件保留。

- R01：底座、肩部转轴壳体、上臂承载组件、前臂侧框、平行夹爪组件。
- R02：底座、双肩支撑、上臂侧框、肘部/前臂滚转壳体、下前臂壳体、
  腕部俯仰/滚转支架、双导轨夹爪组件。
- R03：底座裙罩及安装组件、肩部支撑组件、上臂侧框、前臂侧框、
  腕部俯仰/滚转支架、平行夹爪组件。

详细 ID、英文 semantic label、role class、RGB 和源成员在
`../robots/semantic_parts/*.json`；简表为 `semantic_part_index.csv`。
18 个颜色在本实验内互不重复。夹爪是多体功能子装配，不是一个刚性零件；
后续生成必须保留独立手指、导轨和工作间隙。

## 参考图与检查

每台整机生成 front/rear/left/right/top/isometric 六张彩色 context。
每个 part 单独显示并重新 fitAll，生成 front/side/top/isometric 四张图。
原图均为 1400×1400 正交渲染，保存实际相机参数；隔离视图不使用整机
bbox 裁图，因此不会把零件只留成小碎片。不同视角自动取景尺度可不同，
比较投影特征大小时必须使用同一视图，不能直接跨图比较像素长度。

共 90 张原图：18 张全局、72 张隔离；自动前景/边界检查 90/90 通过。
检查内容是非空、前景占比、分辨率和边界，不等于特征正确性评分。
已逐一查看全部 18 个部件四视图及三张六视图整机 contact sheet。
细长零件正视图可能显得窄，但 side/top/isometric 补充其完整外形。
源文件本身含简化壳体，不能要求恢复其中未显示的内部结构或制造细节。

| Robot | 六视图整机 | 四视图部件 |
| --- | --- | --- |
| R01 | [global](contact_sheets/R01_global.png) | [isolated](contact_sheets/R01_isolated.png) |
| R02 | [global](contact_sheets/R02_global.png) | [isolated](contact_sheets/R02_isolated.png) |
| R03 | [global](contact_sheets/R03_global.png) | [isolated](contact_sheets/R03_isolated.png) |

## RobotPart-LOD v1 和特征清单

已建立 `../skills/robot_part_modeling_standard/SKILL.md`，覆盖主形状、
关节区域、功能外观、结构外观和主要曲面五类要求。允许省略螺纹齿、
logo/文字、极小倒角、螺钉头精确形状与不可见内部；不允许以占位 Box/
Cylinder 代替有明确证据的外观结构。

18 份逐部件清单含 56 项 expected features，其中 46 项标为功能关键项。
这些是本轮基于参考图与语义上下文的离线标注，尚非独立专家真值或 MFR。
所有条目都带具体 region 与实际存在的 evidence_views，未循环分配整机标签。

典型条目包括：上臂双侧板及矩形槽、末端开口圆缺口、前臂三角减重孔、
偏置外形、腕部曲边支架和滚转端面、夹爪导轨与相对手指。圆形盖板边界
与通孔明确区分，不能因看到圆圈就添加孔。

普通细节相对尺寸暂定 2% 作为 DEV_A/B 的开发候选规则；关键接口/功能
特征不受该尺寸门槛限制。2% 尚未经过重建结果校准，不是最终 Quality
Gate。IoU/CD/HD95/MFR/停滞阈值均尚未冻结，需按 Phase 5–9 在 A/B 确定。
Robot C 只准备参考，尚未生成/评估，不用于修改阈值。

## 输入包与泄漏审计

生成了 18 个 packet-only 目录，每包有 10 张图片、一个 part_input.json
及 LOD 文档。JSON 包含语义/颜色、近远端关节、局部匿名 URDF、接口描述、
全局运动学尺度、expected features 和允许操作范围。全局尺度来自 sanitized
URDF 的机械臂关节平移长度之和，明确不等于精确 reach 或 GT part 尺寸。

源 STEP、source body/component 名称映射、原始 URDF 和 CAD 几何留在离线
区域；未把 GT bbox、profile、面参数或 feature tree 放入生成包。
18/18 包的文件类型、依赖闭包和图像哈希审计通过。审计不等于运行时文件
隔离：Phase 3 必须给每个 Codex CLI 上下文只提供该包及共享技能，不能从
本次已查看离线源清单的上下文直接继承生成。已发现本机 codex.exe，但
尚未启动生成 session，也未搭建额外 API 框架。

## 限制与确认点

1. 三台都属同厂商系列。DEV_B 是本原生 STEP 候选内相对困难的对象，
   不覆盖高度自由曲面工业壳体；TRANSFER 只能作为同系列方法迁移诊断。
2. joint 关联基于组件语义与 URDF；STEP/URDF 数值刚体配准尚未验证。
   包内保留局部 frame 并明确禁止把它直接当作图像投影或实测接口坐标。
3. 多体夹爪 Macro-Part 包含相对运动成员；后续不能融合为一块实体。
4. 共享建模/Review/Repair 技能、具体 IR、Scheduler 和评价器属于后续阶段，
   本轮只落实了 LOD Skill；允许操作列表不是后端能力通过证书。

渲染准备出现一次 GUI 文档尚未建立的实现错误（提前隐藏主窗口导致
activeView 不可用），已在参考准备阶段修正并重新生成；没有重建结果被
筛选或重跑。最终自动检查见 reference_audit.json、leakage_audit.json、
phase12_validation.json。Phase 1＋2 完成后依 try4.md 第 53 节停止，
待用户确认以上分组、LOD 与限制后再继续 Phase 3。
