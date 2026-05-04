from typing import Any

from graphrag.rrf_fusion import RankedResult

def _fmt_node(node_type: str, data: dict[str, Any]) -> str:
    props = {k: v for k, v in data.items() if k != "embedding" and v is not None}
    parts = [f"[{node_type.upper()}]"]
    for k, v in props.items():
        parts.append(f"  {k}: {v}")
    return "\n".join(parts)

def serialise_subgraph(results: list[RankedResult], max_nodes: int = 20) -> str:
    lines: list[str] = ["=== GRAPH CONTEXT ==="]
    for result in results[:max_nodes]:
        lines.append("")
        lines.append(_fmt_node(result.node_type, result.data))
        lines.append(f"  [relevance_score: {result.score:.4f}]")
    lines.append("")
    lines.append("=== END GRAPH CONTEXT ===")
    return "\n".join(lines)

def serialise_case_context(
    customer: dict,
    order: dict,
    product: dict,
    seller: dict,
    disputes: list[dict],
    policy_findings: list[dict],
    precedents: list[dict],
) -> str:
    sections = []

    sections.append("## CUSTOMER")
    sections.append(f"ID: {customer.get('id')}  |  Name: {customer.get('name')}")
    sections.append(f"Dispute count: {customer.get('dispute_count', 0)}  |  Fraud risk: {customer.get('fraud_risk_score', 0.0):.2f}")

    sections.append("\n## ORDER")
    sections.append(f"ID: {order.get('id')}  |  Value: £{order.get('total_value', 0):.2f}  |  Status: {order.get('status')}")
    sections.append(f"Channel: {order.get('channel')}  |  Date: {order.get('date')}")

    sections.append("\n## PRODUCT")
    sections.append(f"SKU: {product.get('sku')}  |  Name: {product.get('name')}  |  Category: {product.get('category')}")
    sections.append(f"Defect rate: {product.get('defect_rate', 0.0):.3f}  |  Return rate: {product.get('return_rate', 0.0):.3f}")

    sections.append("\n## SELLER")
    sections.append(f"ID: {seller.get('id')}  |  Name: {seller.get('name')}")
    sections.append(f"Dispute rate: {seller.get('dispute_rate', 0.0):.3f}  |  Refund rate: {seller.get('refund_rate', 0.0):.3f}  |  Fraud signals: {seller.get('fraud_signals', 0)}")

    sections.append("\n## APPLICABLE POLICIES")
    for i, p in enumerate(policy_findings, 1):
        sections.append(f"{i}. [{p.get('source')}] {p.get('clause')} (relevance: {p.get('relevance_score', 0.0):.2f})")
        sections.append(f"   {p.get('text', '')[:300]}")

    sections.append("\n## PRECEDENT CASES")
    for i, pr in enumerate(precedents, 1):
        sections.append(f"{i}. Case {pr.get('case_id')} | Similarity: {pr.get('similarity', 0.0):.2f} | Outcome: {pr.get('resolution')}")

    return "\n".join(sections)
