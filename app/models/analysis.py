"""Analysis run and junction table models."""
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class AnalysisRun(Base):
    __tablename__ = "analysis_runs"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    status = Column(String(32), nullable=False, default="pending", index=True)  # pending | in_progress | completed | failed
    parameters = Column(JSON, nullable=True)  # e.g. {"days_back": 30, "industry": "..."}
    started_at = Column(DateTime(timezone=True), nullable=True)
    completed_at = Column(DateTime(timezone=True), nullable=True)
    created_by = Column(String(255), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    competitor_links = relationship("AnalysisCompetitor", back_populates="analysis_run", cascade="all, delete-orphan")
    news_mentions = relationship("NewsMention", back_populates="analysis_run", cascade="all, delete-orphan")
    web_content = relationship("WebContent", back_populates="analysis_run", cascade="all, delete-orphan")
    market_presence = relationship("MarketPresence", back_populates="analysis_run", cascade="all, delete-orphan")
    features = relationship("Feature", back_populates="analysis_run", cascade="all, delete-orphan")
    pricing_data = relationship("PricingData", back_populates="analysis_run", cascade="all, delete-orphan")
    insights = relationship("Insight", back_populates="analysis_run", cascade="all, delete-orphan")
    differentiation_opportunities = relationship(
        "DifferentiationOpportunity", back_populates="analysis_run", cascade="all, delete-orphan"
    )


class AnalysisCompetitor(Base):
    __tablename__ = "analysis_competitors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)

    analysis_run = relationship("AnalysisRun", back_populates="competitor_links")
    competitor = relationship("Competitor", back_populates="analysis_links")
