from production.monitoring import trace_node
from graphrag.neo4j_client import run_query

@trace_node("customer_resolver")
async def customer_resolver(state: dict) -> dict:
    customer_id = state.get("customer_id")
    if customer_id:
        return {}

    emails = []
    order_ids = []
    for event in state.get("channel_history", []):
        sender = event.get("sender", "")
        if "@" in sender:
            emails.append(sender.lower())
        raw_id = event.get("raw_channel_id", "")
        content = event.get("content", "")
        for text in (raw_id, content):
            import re
            for m in re.finditer(r"\bord[_-]?([A-Za-z0-9]{6,12})\b", text, re.IGNORECASE):
                order_ids.append(f"ord_{m.group(1)}")

    customer = None

    if emails:
        records = await run_query(
            "MATCH (c:Customer {email: $email}) RETURN c LIMIT 1",
            {"email": emails[0]},
        )
        if records:
            customer = records[0].get("c", {})

    if not customer and order_ids:
        records = await run_query(
            """
            MATCH (c:Customer)-[:PLACED]->(o:Order {id: $order_id})
            RETURN c LIMIT 1
            """,
            {"order_id": order_ids[0]},
        )
        if records:
            customer = records[0].get("c", {})

    updates: dict = {}
    if customer:
        updates["customer_id"] = customer.get("id", "")
        if not state.get("order_id") and order_ids:
            updates["order_id"] = order_ids[0]
    else:
        if emails:
            import hashlib
            updates["customer_id"] = f"cust_{hashlib.md5(emails[0].encode()).hexdigest()[:8]}"

    return updates
