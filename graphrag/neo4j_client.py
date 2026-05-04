import os
from contextlib import asynccontextmanager
from typing import Any, AsyncGenerator

from neo4j import AsyncGraphDatabase, AsyncDriver
from graphrag.graph_schema import SCHEMA_CYPHER

_driver: AsyncDriver | None = None

def _get_driver() -> AsyncDriver:
    global _driver
    if _driver is None:
        _driver = AsyncGraphDatabase.driver(
            os.environ["NEO4J_URI"],
            auth=(os.environ["NEO4J_USER"], os.environ["NEO4J_PASSWORD"]),
            max_connection_pool_size=50,
        )
    return _driver

@asynccontextmanager
async def session() -> AsyncGenerator[Any, None]:
    driver = _get_driver()
    async with driver.session(database="neo4j") as s:
        yield s

async def close() -> None:
    global _driver
    if _driver:
        await _driver.close()
        _driver = None

async def run_query(cypher: str, params: dict | None = None) -> list[dict]:
    async with session() as s:
        result = await s.run(cypher, params or {})
        return [record.data() async for record in result]

async def run_write(cypher: str, params: dict | None = None) -> None:
    async with session() as s:
        await s.run(cypher, params or {})

async def apply_schema() -> None:
    for statement in SCHEMA_CYPHER.strip().split(";"):
        stmt = statement.strip()
        if stmt:
            await run_write(stmt)

async def upsert_node(label: str, match_key: str, props: dict) -> None:
    cypher = (
        f"MERGE (n:{label} {{{match_key}: ${match_key}}})"
        " SET n += $props"
    )
    await run_write(cypher, {match_key: props[match_key], "props": props})

async def upsert_relationship(
    from_label: str,
    from_id_prop: str,
    from_id: str,
    rel_type: str,
    to_label: str,
    to_id_prop: str,
    to_id: str,
    rel_props: dict | None = None,
) -> None:
    rel_set = "SET r += $rel_props" if rel_props else ""
    cypher = f"""
        MATCH (a:{from_label} {{{from_id_prop}: $from_id}})
        MATCH (b:{to_label} {{{to_id_prop}: $to_id}})
        MERGE (a)-[r:{rel_type}]->(b)
        {rel_set}
    """
    await run_write(cypher, {
        "from_id": from_id,
        "to_id": to_id,
        "rel_props": rel_props or {},
    })
