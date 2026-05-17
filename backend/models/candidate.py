import uuid
import enum
from datetime import datetime
from sqlalchemy import Column, String, Boolean, Enum, DateTime, Text
from sqlalchemy.dialects.postgresql import UUID
from database import Base
from sqlalchemy.orm import relationship

class CandidateStatus(str, enum.Enum):
    pending = "pending"
    linkedin_pending = "linkedin_pending"
    scraping = "scraping"
    done = "done"
    failed = "failed"

class Candidate(Base):
    __tablename__ = "candidates"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    name = Column(String, nullable=False)
    email = Column(String, unique=True, nullable=False, index=True)
    github_url = Column(String, nullable=True)
    portfolio_url = Column(String, nullable=True)
    linkedin_connected = Column(Boolean, default=False)
    linkedin_access_token = Column(String, nullable=True)
    status = Column(Enum(CandidateStatus), default=CandidateStatus.pending)
    created_at = Column(DateTime, default=datetime.utcnow)
    state_token = Column(String, nullable=True)
    cv_url = Column(String, nullable=True)
    cv_text = Column(Text, nullable=True)

    profile = relationship("Profile", back_populates="candidate", uselist=False, lazy="selectin")