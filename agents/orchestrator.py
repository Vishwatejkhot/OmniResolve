import os
from typing import Annotated, TypedDict

from langgraph.graph import StateGraph, END
from langgraph.graph.message import add_messages
from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver

from agents.channel_normaliser import channel_normaliser
from agents.customer_resolver import customer_resolver
from agents.dispute_classifier import dispute_classifier
from agents.policy_retrieval import policy_retrieval
from agents.evidence_analyser import evidence_analyser
from agents.precedent_agent import precedent_agent
from agents.resolution_engine import resolution_engine
from agents.human_escalation import human_escalation

class CaseState(TypedDict):
    case_id: str
    customer_id: str
    order_id: str
    session_id: str

    channel_history: Annotated[list[dict], add_messages]

    documents: list[dict]
    evidence_scores: dict

    dispute_category: str
    policy_findings: list[dict]
    legal_citations: list[str]
    precedent_cases: list[dict]
    graph_subgraph: dict

    resolution_recommendation: str
    confidence_score: float
    requires_human: bool

    cache_key: str
    retry_count: int
    error_log: list[str]

def _route_after_classification(state: CaseState) -> str:
    if state.get("dispute_category") in ("fraud", "damage", "non_delivery", "other"):
        return "parallel_retrieval"
    return "dispute_classifier"

def _route_after_confidence(state: CaseState) -> str:
    confidence = state.get("confidence_score", 0.0)
    requires_human = state.get("requires_human", False)
    order_value = 0.0
    if state.get("graph_subgraph"):
        subgraph = state.get("graph_subgraph", {})
        order_value = subgraph.get("order_value", 0.0)
    if requires_human or confidence < 0.65 or order_value > 200:
        return "human_escalation"
    return "output_node"

def build_graph() -> StateGraph:
    graph = StateGraph(CaseState)

    graph.add_node("channel_normaliser", channel_normaliser)
    graph.add_node("customer_resolver", customer_resolver)
    graph.add_node("dispute_classifier", dispute_classifier)
    graph.add_node("policy_retrieval", policy_retrieval)
    graph.add_node("evidence_analyser", evidence_analyser)
    graph.add_node("precedent_agent", precedent_agent)
    graph.add_node("resolution_engine", resolution_engine)
    graph.add_node("human_escalation", human_escalation)

    graph.set_entry_point("channel_normaliser")
    graph.add_edge("channel_normaliser", "customer_resolver")
    graph.add_edge("customer_resolver", "dispute_classifier")

    graph.add_edge("dispute_classifier", "policy_retrieval")
    graph.add_edge("dispute_classifier", "evidence_analyser")
    graph.add_edge("policy_retrieval", "precedent_agent")
    graph.add_edge("evidence_analyser", "precedent_agent")
    graph.add_edge("precedent_agent", "resolution_engine")

    graph.add_conditional_edges(
        "resolution_engine",
        _route_after_confidence,
        {
            "human_escalation": "human_escalation",
            "output_node": END,
        },
    )
    graph.add_edge("human_escalation", END)

    return graph

async def get_compiled_graph():
    postgres_url = os.environ["POSTGRES_URL"]
    async with await AsyncPostgresSaver.from_conn_string(postgres_url) as checkpointer:
        await checkpointer.setup()
        compiled = build_graph().compile(checkpointer=checkpointer, interrupt_before=["human_escalation"])
        return compiled
