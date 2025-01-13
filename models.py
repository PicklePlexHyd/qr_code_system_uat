from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from datetime import datetime

Base = declarative_base()

# Membership Table
class Membership(Base):
    __tablename__ = 'memberships'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    membership_type = Column(String, nullable=False)
    validity = Column(Date, nullable=False)
    entries_left = Column(Integer, nullable=True)
    qr_code = Column(String, nullable=False)

    scan_history = relationship('ScanHistory', back_populates='membership')

# ScanHistory Table
class ScanHistory(Base):
    __tablename__ = 'scan_history'
    id = Column(Integer, primary_key=True)
    membership_id = Column(Integer, ForeignKey('memberships.id'))
    scan_time = Column(DateTime, default=datetime.utcnow)

    membership = relationship('Membership', back_populates='scan_history')

# Initialize the database
engine = create_engine('sqlite:///app/membership.db')
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()