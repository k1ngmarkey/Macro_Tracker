from collections.abc import AsyncIterator

import aiosqlite

from core.db import connect, initialize_database


async def get_db() -> AsyncIterator[aiosqlite.Connection]:
    connection = await connect()
    try:
        await initialize_database(connection)
        await connection.execute("BEGIN")
        yield connection
        await connection.commit()
    except Exception:
        await connection.rollback()
        raise
    finally:
        await connection.close()