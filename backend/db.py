import os
import datetime
from sqlalchemy import create_engine, Column, Integer, String, Date, Time, Text, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, sessionmaker, relationship
from dotenv import load_dotenv

load_dotenv()

# We default to a local SQLite database for easy development/testing if no PostgreSQL/MySQL URL is provided,
# but we fully support Postgres and MySQL via the DATABASE_URL environment variable.
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./crm.db")

engine = create_engine(
    DATABASE_URL, 
    # SQLite-specific configuration, ignored by other databases
    connect_args={"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, index=True)
    hcp_name = Column(String(255), nullable=False)
    interaction_type = Column(String(100))
    date = Column(Date)
    time = Column(Time)
    attendees = Column(Text)
    topics_discussed = Column(Text)
    sentiment = Column(String(50))
    outcomes = Column(Text)
    follow_up_actions = Column(Text)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    materials = relationship("MaterialShared", back_populates="interaction", cascade="all, delete-orphan")
    samples = relationship("SampleDistributed", back_populates="interaction", cascade="all, delete-orphan")

class MaterialShared(Base):
    __tablename__ = "materials_shared"

    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id", ondelete="CASCADE"))
    material_name = Column(String(255), nullable=False)

    interaction = relationship("Interaction", back_populates="materials")

class SampleDistributed(Base):
    __tablename__ = "samples_distributed"

    id = Column(Integer, primary_key=True, index=True)
    interaction_id = Column(Integer, ForeignKey("interactions.id", ondelete="CASCADE"))
    sample_name = Column(String(255), nullable=False)

    interaction = relationship("Interaction", back_populates="samples")

# Create tables in SQLite or if they do not exist
def init_db():
    Base.metadata.create_all(bind=engine)

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

def save_interaction(form_data: dict) -> tuple[bool, str]:
    db = SessionLocal()
    try:
        # Convert date and time strings to date/time objects
        date_obj = None
        if form_data.get("date"):
            try:
                date_obj = datetime.datetime.strptime(form_data["date"], "%Y-%m-%d").date()
            except ValueError:
                pass
        
        time_obj = None
        if form_data.get("time"):
            try:
                t_str = form_data["time"]
                if len(t_str.split(":")) == 2:
                    time_obj = datetime.datetime.strptime(t_str, "%H:%M").time()
                else:
                    time_obj = datetime.datetime.strptime(t_str, "%H:%M:%S").time()
            except ValueError:
                pass

        interaction = Interaction(
            hcp_name=form_data.get("hcp_name", "Unknown HCP"),
            interaction_type=form_data.get("interaction_type", "Meeting"),
            date=date_obj,
            time=time_obj,
            attendees=form_data.get("attendees", ""),
            topics_discussed=form_data.get("topics_discussed", ""),
            sentiment=form_data.get("sentiment", "Neutral"),
            outcomes=form_data.get("outcomes", ""),
            follow_up_actions=form_data.get("follow_up_actions", "")
        )
        db.add(interaction)
        db.flush() # Populate the ID of the interaction
        
        # Add materials
        for mat in form_data.get("materials_shared", []):
            if mat:
                material = MaterialShared(interaction_id=interaction.id, material_name=mat)
                db.add(material)
            
        # Add samples
        for sam in form_data.get("samples_distributed", []):
            if sam:
                sample = SampleDistributed(interaction_id=interaction.id, sample_name=sam)
                db.add(sample)
            
        db.commit()
        return True, f"Interaction with {interaction.hcp_name} successfully saved to database with ID {interaction.id}."
    except Exception as e:
        db.rollback()
        return False, f"Failed to save interaction to database: {str(e)}"
    finally:
        db.close()
