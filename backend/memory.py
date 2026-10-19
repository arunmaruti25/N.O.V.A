import aiosqlite
from typing import List, Dict, Any, Optional
from .config import settings

DB_PATH = settings.DATA_DIR / "nova_memory.db"

async def init_db() -> None:
    """Initialize local SQLite memory database."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                category TEXT NOT NULL,
                text TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.commit()

async def save_memory(category: str, text: str) -> Dict[str, Any]:
    """Store persistent context item in SQLite."""
    clean_cat = category.strip() or "Preferences"
    clean_txt = text.strip()
    if not clean_txt:
        return {"success": False, "error": "Memory text cannot be empty."}

    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "INSERT INTO memories (category, text) VALUES (?, ?)",
            (clean_cat, clean_txt),
        )
        await db.commit()
        mem_id = cursor.lastrowid
        return {
            "success": True,
            "id": mem_id,
            "category": clean_cat,
            "text": clean_txt,
        }

async def list_memories(category: Optional[str] = None) -> List[Dict[str, Any]]:
    """List stored memories, optionally filtered by category."""
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        if category and category.lower() != "all":
            cursor = await db.execute(
                "SELECT id, category, text, created_at FROM memories WHERE LOWER(category) = ? ORDER BY id DESC",
                (category.lower(),),
            )
        else:
            cursor = await db.execute(
                "SELECT id, category, text, created_at FROM memories ORDER BY id DESC"
            )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "category": row["category"],
                "text": row["text"],
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

async def retrieve_memories(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """Retrieve memories matching query keywords."""
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        pattern = f"%{query.strip()}%"
        cursor = await db.execute(
            "SELECT id, category, text, created_at FROM memories WHERE text LIKE ? OR category LIKE ? ORDER BY id DESC LIMIT ?",
            (pattern, pattern, limit),
        )
        rows = await cursor.fetchall()
        return [
            {
                "id": row["id"],
                "category": row["category"],
                "text": row["text"],
                "created_at": str(row["created_at"]),
            }
            for row in rows
        ]

async def delete_memory(memory_id: int) -> bool:
    """Delete context item by id."""
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
        await db.commit()
        return cursor.rowcount > 0

