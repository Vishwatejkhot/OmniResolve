from dataclasses import dataclass
from typing import Any

@dataclass
class RankedResult:
    node_id: str
    node_type: str
    data: dict[str, Any]
    score: float = 0.0

def reciprocal_rank_fusion(
    *ranked_lists: list[RankedResult],
    k: int = 60,
) -> list[RankedResult]:
    scores: dict[str, float] = {}
    registry: dict[str, RankedResult] = {}

    for ranked in ranked_lists:
        for rank, result in enumerate(ranked, start=1):
            scores[result.node_id] = scores.get(result.node_id, 0.0) + 1.0 / (k + rank)
            registry[result.node_id] = result

    fused = sorted(registry.values(), key=lambda r: scores[r.node_id], reverse=True)
    for result in fused:
        result.score = scores[result.node_id]
    return fused
