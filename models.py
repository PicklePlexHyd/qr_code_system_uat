from sqlalchemy import create_engine, Column, Integer, String, Date
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

Base = declarative_base()

class Membership(Base):
    __tablename__ = 'memberships'
    id = Column(Integer, primary_key=True)
    name = Column(String, nullable=False)
    membership_type = Column(String, nullable=False)  # Membership/Xpress/Season Pass
    validity = Column(Date, nullable=False)
    entries_left = Column(Integer, nullable=True)  # Only for passes
    qr_code = Column(String, nullable=False)

# Database connection
DATABASE_URL = 'sqlite:///memberships.db'
engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)
Session = sessionmaker(bind=engine)
session = Session()
