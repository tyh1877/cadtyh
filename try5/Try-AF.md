# Freeze Try-5A Coarse Reconstruction Stage

Try-5A.5 已完成。现在冻结 Try-5A 粗建模阶段。

目标：
把当前已验证的 coarse-stage 核心架构固定下来，作为后续 Try-5B 精细建模的机械约束基础。

请直接在现有 try5 主代码上完成冻结，不复制新 pipeline。

## 1. 冻结以下核心模块

冻结：

- Sanitized URDF as kinematic authority
- Kinematic Skeleton / FK
- physical / virtual link classification
- Robot-level coarse planning framework
- Robot Interface Knowledge Base 当前通用版本
- Knowledge-guided interface selection
- Motion-Aware Interface Contract
- Interface-first modeling principle
- Parent / Child rigid-group representation
- BICR / attachment rules
- forbidden parent-child fusion rules
- swept-clearance generation
- exact mechanical validation logic
- Global Collision Graph
- R0–R4 Repair Scope Arbiter
- Progressive Freezing
- Mechanical Meaningfulness Gate
- virtual-frame filtering

后续 Try-5B 不应随意修改这些定义。

## 2. 不冻结以下部分

不要冻结：

- body geometry realization
- body family → CAD implementation
- Link internal topology / feature graph
- visual grounding
- local profile / section / loft / shell strategy
- geometry-detail repair

这些是 Try-5B 的主要改进对象。

## 3. 固化 Try-5A baseline

保存 Try-5A.5 final 作为 coarse baseline：

- final Robot Plan
- Interface Contracts
- rigid-group states
- coarse Link CAD
- final mechanical metrics
- final GCFR / JR3 / BICR
- collision graph
- reproducibility manifest

确保可以一条命令重新验证当前 frozen baseline。

## 4. 后续 Try-5B 的硬约束

任何 Link refinement 后必须重新检查：

- URDF frame unchanged
- BICR = 100%
- Physical Floating = 0
- Forbidden Fusion = 0
- Virtual Solid = 0
- Meaningless Patch Count = 0
- corresponding JR3 不退化
- swept-clearance 不被破坏
- whole-robot GCFR 不出现严重回归

若 geometry 改善但机械 hard gate 失败：

ROLLBACK。

## 5. 版本管理

使用 Git commit / tag 固化当前节点，例如：

try5A_frozen_coarse_stage

不要创建新的代码副本。

输出一份简短：

try5A_frozen_spec.md

说明：
- 冻结了什么；
- 为什么冻结；
- 哪些部分允许 Try-5B 修改；
- Try-5B 必须保持哪些 mechanical invariants。

完成后停止，不要开始 Try-5B。