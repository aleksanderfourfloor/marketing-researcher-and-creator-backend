"""Competitor model."""
from sqlalchemy import Column, Integer, String, Text, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Competitor(Base):
    __tablename__ = "competitors"

    id = Column(Integer, primary_key=True, autoincrement=True)
    name = Column(String(255), nullable=False, index=True)
    website_url = Column(String(512), nullable=True)
    twitter_url = Column(String(512), nullable=True)
    instagram_url = Column(String(512), nullable=True)
    facebook_url = Column(String(512), nullable=True)
    reddit_url = Column(String(512), nullable=True)
    discord_url = Column(String(512), nullable=True)
    industry = Column(String(255), nullable=True, index=True)
    description = Column(Text, nullable=True)
    logo_url = Column(String(512), nullable=True)
    status = Column(String(32), nullable=False, default="active", index=True)  # active | inactive
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    analysis_links = relationship("AnalysisCompetitor", back_populates="competitor", cascade="all, delete-orphan")
    news_mentions = relationship("NewsMention", back_populates="competitor", cascade="all, delete-orphan")
    web_content = relationship("WebContent", back_populates="competitor", cascade="all, delete-orphan")
    market_presence = relationship("MarketPresence", back_populates="competitor", cascade="all, delete-orphan")
    features = relationship("Feature", back_populates="competitor", cascade="all, delete-orphan")
    pricing_data = relationship("PricingData", back_populates="competitor", cascade="all, delete-orphan")
