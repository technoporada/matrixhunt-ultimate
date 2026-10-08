from sqlalchemy import create_engine, Column, Integer, String, DateTime, Boolean, Text, Index
from sqlalchemy.orm import declarative_base, sessionmaker
from datetime import datetime, timezone

Base = declarative_base()

class Offer(Base):
    __tablename__ = "offers"
    id = Column(Integer, primary_key=True, autoincrement=True)
    title = Column(String(500), nullable=False)
    description = Column(Text, default="")
    url = Column(Text, nullable=False)
    image_url = Column(Text, default="")
    source = Column(String(100), nullable=False)
    category = Column(String(100), default="games")
    price = Column(String(50), default="Free")
    original_price = Column(String(50), default="")
    tags = Column(String(500), default="")
    requires_login = Column(Boolean, default=False)
    has_adfly = Column(Boolean, default=False)
    has_captcha = Column(Boolean, default=False)
    is_adult = Column(Boolean, default=False)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (Index("ix_offers_url", "url", unique=True),)

def init_db(db_path="matrixhunt.db"):
    if not db_path.startswith("sqlite"):
        db_path = f"sqlite:///{db_path}"
    kwargs = {"echo": False}
    if db_path.startswith("sqlite"):
        # SQLAlchemy 2.0 pools SQLite with QueuePool, so concurrent reads
        # grabbed separate connections and contended on the writer lock, giving
        # "database is locked" under load. NullPool + WAL lets readers run
        # alongside the writer, and the busy timeout turns a lost race into a
        # short wait instead of an immediate error.
        from sqlalchemy.pool import NullPool
        kwargs.update(poolclass=NullPool, connect_args={"timeout": 15})
    engine = create_engine(db_path, **kwargs)
    if db_path.startswith("sqlite"):
        with engine.connect() as conn:
            conn.exec_driver_sql("PRAGMA journal_mode=WAL")
            conn.exec_driver_sql("PRAGMA synchronous=NORMAL")
            conn.exec_driver_sql("PRAGMA busy_timeout=15000")
    Base.metadata.create_all(engine)
    return sessionmaker(bind=engine)
