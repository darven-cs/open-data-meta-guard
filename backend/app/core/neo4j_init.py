"""Neo4j 约束初始化 — 应用启动时执行。

创建唯一性约束确保实体幂等 MERGE。
"""
from app.core.config import settings
from app.core.db import get_neo4j_driver
from app.core.log import logger


CONSTRAINTS = [
    "CREATE CONSTRAINT publisher_name IF NOT EXISTS "
    "FOR (p:Publisher) REQUIRE p.name IS UNIQUE",
    "CREATE CONSTRAINT theme_name IF NOT EXISTS "
    "FOR (t:Theme) REQUIRE t.name IS UNIQUE",
    "CREATE CONSTRAINT keyword_name IF NOT EXISTS "
    "FOR (k:Keyword) REQUIRE k.name IS UNIQUE",
    "CREATE CONSTRAINT format_name IF NOT EXISTS "
    "FOR (f:Format) REQUIRE f.name IS UNIQUE",
]


async def init_neo4j_constraints() -> None:
    """执行所有唯一性约束（幂等，可重复调用）。"""
    driver = get_neo4j_driver()
    async with driver.session(database=settings.neo4j_database) as session:
        for cypher in CONSTRAINTS:
            try:
                await session.run(cypher)
                logger.debug("[neo4j] constraint ensured: {}", cypher[:60])
            except Exception as e:
                logger.warning("[neo4j] constraint error (non-fatal): {} — {}", cypher[:60], e)
    logger.info("[neo4j] all constraints initialized")
