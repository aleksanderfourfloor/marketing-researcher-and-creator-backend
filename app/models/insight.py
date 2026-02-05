"""Features, pricing, insights, and differentiation opportunity models."""
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, Float, JSON
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Feature(Base):
    __tablename__ = "features"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    feature_name = Column(String(255), nullable=False)
    category = Column(String(128), nullable=True)
    description = Column(Text, nullable=True)
    is_available = Column(Integer, nullable=False, default=1)  # 1 = True, 0 = False
    source = Column(String(255), nullable=True)

    competitor = relationship("Competitor", back_populates="features")
    analysis_run = relationship("AnalysisRun", back_populates="features")


class PricingData(Base):
    __tablename__ = "pricing_data"

    id = Column(Integer, primary_key=True, autoincrement=True)
    competitor_id = Column(Integer, ForeignKey("competitors.id", ondelete="CASCADE"), nullable=False, index=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    plan_name = Column(String(255), nullable=True)
    price = Column(Float, nullable=True)
    currency = Column(String(8), nullable=True, default="USD")
    billing_period = Column(String(32), nullable=True)  # monthly | yearly | one-time
    features = Column(JSON, nullable=True)  # list of feature strings
    source = Column(String(255), nullable=True)

    competitor = relationship("Competitor", back_populates="pricing_data")
    analysis_run = relationship("AnalysisRun", back_populates="pricing_data")


class Insight(Base):
    __tablename__ = "insights"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    insight_type = Column(String(64), nullable=False, index=True)  # feature_gap | messaging_angle | market_timing
    category = Column(String(128), nullable=True)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    priority = Column(String(32), nullable=True)  # high | medium | low
    actionable_recommendation = Column(Text, nullable=True)
    supporting_data = Column(JSON, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analysis_run = relationship("AnalysisRun", back_populates="insights")


class DifferentiationOpportunity(Base):
    __tablename__ = "differentiation_opportunities"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_run_id = Column(Integer, ForeignKey("analysis_runs.id", ondelete="CASCADE"), nullable=False, index=True)
    opportunity_type = Column(String(64), nullable=True)
    title = Column(String(512), nullable=False)
    description = Column(Text, nullable=True)
    competitors_affected = Column(JSON, nullable=True)  # list of competitor ids or names
    impact_score = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    analysis_run = relationship("AnalysisRun", back_populates="differentiation_opportunities")
