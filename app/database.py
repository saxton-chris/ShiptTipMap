from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

engine = create_engine("sqlite:///tip_map.db")
SessionLocal = sessionmaker(bind=engine)
