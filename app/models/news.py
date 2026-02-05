"""News, web content, and market presence models."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class NewsMention(Base):
    __tablename__ = "news_mentions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    title = Column(String(512), nullable=False)
    url = Column(String(1024), nullable=True)
    source = Column(String(255), nullable=True)
    published_date = Column(DateTime(timezone=True), nullable=True)
    content = Column(Text, nullable=True)
    sentiment_score = Column(Float, nullable=True)
    extracted_at = Column(DateTime(timezone=True), server_default=func.now())

    competitor = relationship("Competitor", back_populates="news_mentions")
    analysis_run = relationship("AnalysisRun", back_populates="news_mentions")


class WebContent(Base):
    __tablename__ = "web_content"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    page_type = Column(String(64), nullable=False, index=True)  # homepage | pricing | about | features
    content = Column(JSON, nullable=True)
    extracted_at = Column(DateTime(timezone=True), server_default=func.now())

    competitor = relationship("Competitor", back_populates="web_content")
    analysis_run = relationship("AnalysisRun", back_populates="web_content")


class MarketPresence(Base):
    __tablename__ = "market_presence"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    mention_count = Column(Integer, nullable=True, default=0)
    sentiment_average = Column(Float, nullable=True)
    visibility_score = Column(Float, nullable=True)
    trend_direction = Column(String(32), nullable=True)  # rising | stable | declining
    period_start = Column(DateTime(timezone=True), nullable=True)
    period_end = Column(DateTime(timezone=True), nullable=True)

    competitor = relationship("Competitor", back_populates="market_presence")
    analysis_run = relationship("AnalysisRun", back_populates="market_presence")
