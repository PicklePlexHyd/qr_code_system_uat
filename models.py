from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime, create_engine
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from datetime import datetime
import os

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

# Database Initialization
# Fetch the DATABASE_URL from the environment variable, default to local SQLite if not found
DATABASE_URL = os.getenv("postgres://u5tcjrchmc5fa3:p24192f96879635b1330d21133a01a2d3777838f27821f755df3849609c9889e1@cfls9h51f4i86c.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/da9iac6pkpkurm", "sqlite:///membership.db")

# Use the correct connection string format for Heroku Postgres
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
