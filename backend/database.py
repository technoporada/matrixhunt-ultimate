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
    # price is what a scraper *assumed*; these three record what was actually
    # measured and where. price_source is None whenever price_claim was not
    # read from the store's own API — the UI shows "nie sprawdzono" for those,
    # which is the whole point. See backend/migrate.py.
    price_claim = Column(Text, default=None)
    price_source = Column(Text, default=None)
    price_checked = Column(DateTime, default=None)
    __table_args__ = (Index("ix_offers_url", "url", unique=True),)

class PriceHistory(Base):
    """One row per (offer, day, price). Lets 'sprawdź zmiany' report that a
    game dropped from 71,99 zł to Free instead of only what exists right now."""
    __tablename__ = "price_history"
    id = Column(Integer, primary_key=True, autoincrement=True)
    offer_id = Column(Integer, nullable=False, index=True)
    price_claim = Column(Text, default=None)
    price_source = Column(Text, default=None)
    seen_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))
    __table_args__ = (Index("ix_price_history_offer_day", "offer_id", "seen_at"),)

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
