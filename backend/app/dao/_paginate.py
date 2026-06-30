"""通用分页 helper。

设计:
- 接收一条已构造好 WHERE/ORDER BY 但尚未 OFFSET/LIMIT 的 Select 语句
- 自动 clamp page(>=1) 与 size(1..100,默认 20)
- 一次 COUNT(*) + 一次 LIMIT/OFFSET 查询
- 返回 {items: list[ORM], count: int, page: int, size: int}
- 调用方负责 rows -> dict 的序列化(如现有 _to_dict())
"""
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession


async def paginate(
    session: AsyncSession,
    stmt,
    page: int = 1,
    size: int = 20,
) -> dict:
    if page < 1:
        page = 1
    if size < 1 or size > 100:
        size = 20

    # 用 subquery 复用 WHERE(不重复写一份 count_stmt)
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await session.execute(count_stmt)).scalar() or 0

    data_stmt = stmt.offset((page - 1) * size).limit(size)
    result = await session.execute(data_stmt)
    rows = result.scalars().all()

    return {
        "items": list(rows),
        "count": int(total),
        "page": page,
        "size": size,
    }
