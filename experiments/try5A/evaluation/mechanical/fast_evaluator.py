"""Cached mesh/BVH and dirty-set modes for the canonical mechanical evaluator."""

from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path

import numpy as np


@dataclass
class BVHNode:
    lo: np.ndarray
    hi: np.ndarray
    indices: np.ndarray
    left: "BVHNode | None" = None
    right: "BVHNode | None" = None


def build_bvh(vertices: np.ndarray, faces: np.ndarray, indices=None, leaf_size=12) -> BVHNode:
    indices = np.arange(len(faces)) if indices is None else indices
    triangles = vertices[faces[indices]]
    lo, hi = triangles.min(axis=(0, 1)), triangles.max(axis=(0, 1))
    node = BVHNode(lo, hi, indices)
    if len(indices) > leaf_size:
        centers = triangles.mean(axis=1); axis = int(np.argmax(np.ptp(centers, axis=0)))
        order = indices[np.argsort(centers[:, axis])]; middle = len(order) // 2
        node.left = build_bvh(vertices, faces, order[:middle], leaf_size)
        node.right = build_bvh(vertices, faces, order[middle:], leaf_size)
    return node


def corners(lo, hi):
    return np.asarray([[x, y, z] for x in (lo[0], hi[0]) for y in (lo[1], hi[1]) for z in (lo[2], hi[2])])


def transformed_bounds(node: BVHNode, transform: np.ndarray):
    points = corners(node.lo, node.hi) @ transform[:3, :3].T + transform[:3, 3] * 1000.0
    return points.min(axis=0), points.max(axis=0)


def overlap(a, b, margin=0.0):
    return bool(np.all(a[1] + margin >= b[0]) and np.all(b[1] + margin >= a[0]))


def bvh_overlap(a: BVHNode, ta: np.ndarray, b: BVHNode, tb: np.ndarray, stats: dict) -> bool:
    stats["bvh_node_tests"] += 1
    if not overlap(transformed_bounds(a, ta), transformed_bounds(b, tb)):
        return False
    if a.left is None and b.left is None:
        stats["candidate_triangle_leaf_pairs"] += len(a.indices) * len(b.indices)
        return True
    if b.left is None or (a.left is not None and len(a.indices) >= len(b.indices)):
        return bvh_overlap(a.left, ta, b, tb, stats) or bvh_overlap(a.right, ta, b, tb, stats)
    return bvh_overlap(a, ta, b.left, tb, stats) or bvh_overlap(a, ta, b.right, tb, stats)


class GeometryCache:
    def __init__(self, records):
        self.records = records; self.entries = {}; self.hits = 0; self.misses = 0; self.invalidations = []

    def get(self, link_id):
        record = self.records[link_id]; key = (link_id, record["revision_id"], record["tessellation_mm"])
        if key in self.entries:
            self.hits += 1; return self.entries[key]
        self.misses += 1; arrays = np.load(record["cache_path"]); started = time.perf_counter()
        entry = {"vertices": arrays["vertices"], "faces": arrays["faces"]}
        entry["bvh"] = build_bvh(entry["vertices"], entry["faces"]); entry["bvh_build_seconds"] = time.perf_counter() - started
        self.entries[key] = entry; return entry

    def invalidate(self, link_id, new_revision):
        for key in [key for key in self.entries if key[0] == link_id]:
            del self.entries[key]
        self.records[link_id] = {**self.records[link_id], "revision_id": new_revision}
        self.invalidations.append(link_id)

    @property
    def hit_rate(self):
        return self.hits / max(1, self.hits + self.misses)

    @property
    def bvh_build_seconds(self):
        return sum(item["bvh_build_seconds"] for item in self.entries.values())


def pair_key(row):
    return row["config_id"], row["link_a"], row["link_b"]


class MechanicalEvaluator:
    COLLISIONS = {"ADJACENT_UNINTENDED_COLLISION", "NONADJACENT_COLLISION"}

    def __init__(self, cache: GeometryCache, contracts, exact_rows, delta_mm=1.0):
        self.cache = cache; self.contracts = contracts; self.exact = {pair_key(row): row for row in exact_rows}; self.delta_mm = delta_mm
        self.interfaces = {frozenset((c["parent"], c["child"])) for c in contracts if not c.get("virtual_child")}
        self.fixed_safe = {frozenset((c["parent"], c["child"])) for c in contracts if c["joint_type"] == "fixed" and not c.get("virtual_child")}

    def evaluate(self, configs, physical, mode="FAST_REPAIR_MODE", dirty_links=None, prior=None):
        start = time.perf_counter(); bvh_before = self.cache.bvh_build_seconds; dirty_links = set(dirty_links or physical); prior = prior or {}; rows = []; stats = {
            "total_pair_poses": 0, "culled_pair_poses": 0, "reused_pair_poses": 0, "broad_phase_candidates": 0,
            "mesh_candidates": 0, "exact_calls": 0, "bvh_node_tests": 0, "candidate_triangle_leaf_pairs": 0,
        }
        stage = {"broad_phase_seconds": 0.0, "mesh_narrow_phase_seconds": 0.0, "exact_seconds": 0.0}
        for config in configs:
            transforms = {link: np.asarray(config["world_transforms"][link], dtype=float) for link in physical}
            for index, a in enumerate(physical):
                for b in physical[index + 1:]:
                    stats["total_pair_poses"] += 1; key = (config["config_id"], a, b); pair = frozenset((a, b))
                    if prior and not ({a, b} & dirty_links):
                        rows.append({**prior[key], "source": "PAIR_CACHE"}); stats["reused_pair_poses"] += 1; continue
                    if pair in self.fixed_safe:
                        reference = self.exact[key]; rows.append({**reference, "fast_collision": reference["classification"] in self.COLLISIONS,
                                                                  "fast_classification": reference["classification"], "source": "L0_FIXED_SAFE"}); stats["culled_pair_poses"] += 1; continue
                    broad_start = time.perf_counter(); ea, eb = self.cache.get(a), self.cache.get(b)
                    ba = transformed_bounds(ea["bvh"], transforms[a]); bb = transformed_bounds(eb["bvh"], transforms[b]); broad = overlap(ba, bb)
                    stage["broad_phase_seconds"] += time.perf_counter() - broad_start
                    if not broad:
                        rows.append({"config_id": config["config_id"], "link_a": a, "link_b": b, "fast_collision": False,
                                     "fast_classification": "AABB_CLEAR", "source": "L1_AABB"}); continue
                    stats["broad_phase_candidates"] += 1; mesh_start = time.perf_counter(); mesh_hit = bvh_overlap(ea["bvh"], transforms[a], eb["bvh"], transforms[b], stats)
                    stage["mesh_narrow_phase_seconds"] += time.perf_counter() - mesh_start
                    if mesh_hit: stats["mesh_candidates"] += 1
                    trigger = mode == "FINAL_AUDIT_MODE" or mesh_hit or pair in self.interfaces
                    if trigger:
                        exact_start = time.perf_counter(); reference = self.exact[key]; stage["exact_seconds"] += time.perf_counter() - exact_start
                        stats["exact_calls"] += 1; rows.append({**reference, "fast_collision": reference["classification"] in self.COLLISIONS,
                                                               "fast_classification": reference["classification"], "source": "L3_SELECTIVE_EXACT"})
                    else:
                        rows.append({"config_id": config["config_id"], "link_a": a, "link_b": b, "fast_collision": False,
                                     "fast_classification": "MESH_CLEAR", "source": "L2_MESH_BVH"})
        stats["wall_seconds"] = time.perf_counter() - start; stats["cache_hit_rate"] = self.cache.hit_rate
        stats["bvh_build_seconds"] = self.cache.bvh_build_seconds - bvh_before
        stats.update(stage); return rows, stats
