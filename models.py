from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime, create_engine
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime

Base = declarative_base()

# Membership Table
class Membership(Base):
    __tablename__ = 'memberships'
    id = Column(String, primary_key=True)
    name = Column(String, nullable=False)
    membership_type = Column(String, nullable=False)
    email = Column(String, nullable=False)
    # Removed phone_number column
    validity = Column(Date, nullable=False)
    entries_left = Column(Integer, nullable=True)
    qr_code = Column(String, nullable=False)

    scan_history = relationship('ScanHistory', back_populates='membership')

    def __repr__(self):
        return (
            f"<Membership(id={self.id}, name={self.name}, "
            f"membership_type={self.membership_type}, "
            f"validity={self.validity}, entries_left={self.entries_left}, qr_code={self.qr_code})>"
        )


# ScanHistory Table
class ScanHistory(Base):
    __tablename__ = 'scan_history'
    id = Column(Integer, primary_key=True)
    membership_id = Column(String, ForeignKey('memberships.id'))
    scan_time = Column(DateTime, default=datetime.utcnow)

    membership = relationship('Membership', back_populates='scan_history')

# Database Configuration
DATABASE_URL = "sqlite:////Users/rajkumardandu/Downloads/qr_code_system/membership.db"

# Initialize the database
engine = create_engine(DATABASE_URL, echo=True)  # echo=True enables SQL logging for debugging
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
