import uuid
from datetime import datetime
from sqlalchemy import Column, String, Float, Integer, Text, ForeignKey, DateTime
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.orm import relationship
from sqlalchemy import Text
from database import Base

class Profile(Base):
    __tablename__ = "profiles"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    candidate_id = Column(UUID(as_uuid=True), ForeignKey("candidates.id"), unique=True, nullable=False)
    summary = Column(Text, nullable=True)
    skills = Column(JSONB, nullable=True)
    top_projects = Column(JSONB, nullable=True)
    experience_years = Column(Integer, nullable=True)
    domain_tags = Column(JSONB, nullable=True)
    raw_github_data = Column(JSONB, nullable=True)
    raw_portfolio_text = Column(Text, nullable=True)
    raw_linkedin_data = Column(JSONB, nullable=True)
    generated_at = Column(DateTime, default=datetime.utcnow)
    cv_skills = Column(JSONB, nullable=True)
    cv_experience = Column(JSONB, nullable=True)
    cv_education = Column(JSONB, nullable=True)
    raw_cv_text = Column(Text, nullable=True)

    # Relationships
    candidate = relationship("Candidate", back_populates="profile")

