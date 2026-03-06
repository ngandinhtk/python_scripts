"""
Quan ly lich su hoi thoai - luu vao SQLite (khong can Redis/Docker).
"""
from typing import List, Dict
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from sqlalchemy import Column, String, Text, DateTime, select
from sqlalchemy.sql import func
from app.core.config import settings
from app.core.logging import logger
import uuid

engine = create_async_engine(settings.DATABASE_URL, echo=False)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


class Base(DeclarativeBase):
    pass


class MessageRecord(Base):
    __tablename__ = "messages"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    session_id = Column(String, index=True, nullable=False)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, server_default=func.now())


async def init_db():
    """Tao bang neu chua co (chay khi khoi dong app)."""
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    logger.info("db.initialized", url=settings.DATABASE_URL)


class ConversationMemory:
    MAX_HISTORY = 20

    async def add_message(self, session_id: str, role: str, content: str):
        async with AsyncSessionLocal() as session:
            msg = MessageRecord(session_id=session_id, role=role, content=content)
            session.add(msg)
            await session.commit()
        logger.debug("memory.add", session_id=session_id, role=role)

    async def get_history(self, session_id: str) -> List[Dict[str, str]]:
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(MessageRecord)
                .where(MessageRecord.session_id == session_id)
                .order_by(MessageRecord.created_at.desc())
                .limit(self.MAX_HISTORY)
            )
            records = result.scalars().all()
        return [{"role": r.role, "content": r.content} for r in reversed(records)]

    async def clear(self, session_id: str):
        from sqlalchemy import delete
        async with AsyncSessionLocal() as session:
            await session.execute(
                delete(MessageRecord).where(MessageRecord.session_id == session_id)
            )
            await session.commit()
        logger.info("memory.cleared", session_id=session_id)

    async def list_sessions(self) -> List[str]:
        from sqlalchemy import distinct
        async with AsyncSessionLocal() as session:
            result = await session.execute(
                select(distinct(MessageRecord.session_id))
            )
            return list(result.scalars().all())


memory_service = ConversationMemory()
