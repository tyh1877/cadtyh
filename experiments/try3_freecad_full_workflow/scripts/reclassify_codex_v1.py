"""One-time, lossless reclassification of the historical template pilot.

Archives replaced text/status files byte-for-byte, keeps numerical tables and
raw outputs in place, and checks preserved inputs/results before and after.
Does not generate CAD, change metrics, or implement the next Try-3 method.
"""
from pathlib import Path
import hashlib
import json
import shutil
from datetime import datetime, timezone

EXP = Path(__file__).resolve().parents[1]
ARCHIVE = EXP / "archive/codex_agent_v1_reclassification"
REPLACED = ["README.md", "REQUIREMENT_EVIDENCE_CHECKLIST.md",
            "CODEX_CONTINUATION_CHECKLIST.md",
            "results/codex_agent_v1_try3_report.md",
            "results/codex_agent_v1_completion_audit.json"]

def digest(path):
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()

def main():
    if ARCHIVE.exists():
        raise SystemExit("Archive already exists; refusing to overwrite historical evidence.")
    preserved = [p for p in EXP.rglob("*") if p.is_file()
                 and "__pycache__" not in p.parts and "archive" not in p.relative_to(EXP).parts
                 and p.relative_to(EXP).as_posix() not in REPLACED]
    before = {p.relative_to(EXP).as_posix(): digest(p) for p in preserved}
    originals = []
    for relative in REPLACED:
        source = EXP / relative
        target = ARCHIVE / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
        assert digest(source) == digest(target)
        originals.append({"path": relative, "sha256": digest(source), "bytes": source.stat().st_size})
    now = datetime.now(timezone.utc).isoformat()
    status = {
        "run_id": "codex_agent_v1",
        "classification": "URDF_DRIVEN_COARSE_GEOMETRY_TEMPLATE_PILOT",
        "archive_status": "ARCHIVED_IN_PLACE",
        "try3_completion": "INCOMPLETE",
        "causal_claims": "WITHDRAWN",
        "rq1": "NOT_VALIDATED", "rq2": "NOT_VALIDATED",
        "rq3": "BASIC_FREECAD_OPERATION_EXECUTION_ONLY",
        "all_five_cases": "PREVIOUSLY_OBSERVED_DEVELOPMENT_CASES",
        "historical_holdout_label": "PRESERVED_FOR_PROVENANCE_ONLY_NOT_UNTOUCHED_CONFIRMATORY_HOLDOUT",
        "historical_execution": {"case_version_exports": "15/15", "link_version_exports": "189/189", "operations": 693},
        "historical_checks": "Archived PASS checks concern artifact/schema execution; they do not certify scientific validity, semantic input isolation, or full editability.",
        "supersedes": "results/codex_agent_v1_completion_audit.json at commit 8ae7fa0",
        "reclassified_at": now,
        "scope": "Step 1 only: archive and correct interpretation; no generation/evaluator changes."
    }
    (EXP / "results/codex_agent_v1_completion_audit.json").write_text(json.dumps(status, indent=2) + "\n", encoding="utf-8")
    report = """# 本次结果重新界定：URDF 驱动的粗几何模板试验

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
"""
    (EXP / "results/codex_agent_v1_try3_report.md").write_text(report, encoding="utf-8")
    (EXP / "README.md").write_text("""# Try-3 FreeCAD full-workflow workspace

**完整 Try-3 尚未完成。** `codex_agent_v1` 已重新界定并就地归档为
“URDF 驱动的粗几何模板试验”。此前完整完成及架构因果有效性结论已撤回。

当前权威说明：`results/codex_agent_v1_try3_report.md`。
机器可读状态：`results/codex_agent_v1_completion_audit.json`。
原报告/清单/审计：`archive/codex_agent_v1_reclassification/`，均为历史材料。

模型仍在 `runs/codex_agent_v1/<V0|V1|V2>/<case>/`；指标表和图像路径不变。
五台案例均已查看，后续均作为开发案例。历史 config、freeze 和表格中的
holdout 标签只用于追溯，不代表未触碰的确认性测试集。

原目标仍由 `TRY3_FREECAD_PROTOCOL.md` 与 `try3/try3.md` 定义；本次归档
没有降低原实验要求。GLM 视觉历史记录、Fusion 结果与其他试验仍独立保存。
""", encoding="utf-8")
    checklist = """# Try-3 当前证据状态（取代历史全勾选清单）

原清单已逐字节归档，历史“PASS”不等于科学完成。

- [x] 历史模型、数值表、图片与冻结记录保留。
- [x] 原报告、README、两份清单与机器审计归档并记录 SHA-256。
- [x] 本次运行重新界定为 URDF 驱动的粗几何模板试验。
- [x] 完整 Try-3 完成与 RQ1/RQ2 因果有效性结论撤回。
- [x] 五台案例均标记为已查看的开发案例。
- [x] 基础 FreeCAD 操作、导出与打开记录作为有限工程证据保留。
- [ ] 真正逐 link 视觉观察及语义证据审查。
- [ ] MEP 和共享接口实际驱动几何；通过反事实依赖检查。
- [ ] 按原要求建立 V0/V1/V2 可归因比较。
- [ ] Feature Graph → SkillCall → IR 的可验证编译与失败传播。
- [ ] 结构/表面细节和可靠的几何归属处理。
- [ ] 实测 B-Rep 接口、轴线、间隙、ICS、干涉与适用运动检查。
- [ ] 参数修改后可更新的整机装配及重算验证。
- [ ] 统一四视角实体渲染及可见特征质量评估。
- [ ] 完整 Try-3 科学验证完成。

此次授权仅包括第一步重新界定与归档；以上后续项目没有在此步实现。
归档验证见 `archive/codex_agent_v1_reclassification/manifest.json`。
"""
    for relative in ["REQUIREMENT_EVIDENCE_CHECKLIST.md", "CODEX_CONTINUATION_CHECKLIST.md"]:
        (EXP / relative).write_text(checklist, encoding="utf-8")
    after = {relative: digest(EXP / relative) for relative in before}
    assert before == after, "Protected evidence changed during reclassification"
    record = {"created_at": now, "historical_commit": "8ae7fa059a99f35c4ff85238e3efe285d89ebf6a",
              "archive_meaning": "superseded claims; retain for provenance, do not cite as current conclusions",
              "archived_originals": originals, "preserved_files": before,
              "preservation_check": "PASS", "preserved_file_count": len(before)}
    (ARCHIVE / "manifest.json").write_text(json.dumps(record, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({"archived_originals": len(originals), "preserved_files": len(before), "preservation_check": "PASS"}))

if __name__ == "__main__":
    main()
