from sqlalchemy import Column, Integer, String, Date, ForeignKey, DateTime, create_engine
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.declarative import declarative_base
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

# Manually configure database URL
DATABASE_URL = "postgresql://u5tcjrchmc5fa3:p24192f96879635b1330d21133a01a2d3777838f27821f755df3849609c9889e1@cfls9h51f4i86c.cluster-czrs8kj4isg7.us-east-1.rds.amazonaws.com:5432/da9iac6pkpkurm"

# Initialize the database
engine = create_engine(DATABASE_URL, echo=True)  # echo=True enables SQL logging for debugging
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
