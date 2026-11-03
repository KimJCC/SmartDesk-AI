import datetime
import hashlib
import os
from dotenv import load_dotenv
from sqlalchemy import Column, Integer, String, Text, DateTime, ForeignKey, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, relationship

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./tickets.db")

engine = create_engine(
    DATABASE_URL, 
    connect_args={"check_same_thread": False} if "sqlite" in DATABASE_URL else {}
)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

def hashear_password(password: str) -> str:
    """Aplica hash SHA-256 para almacenamiento de credenciales."""
    return hashlib.sha256(password.encode("utf-8")).hexdigest()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    nombre = Column(String(100), nullable=False)
    email = Column(String(120), unique=True, index=True, nullable=False)
    password_hash = Column(String(128), nullable=False)
    rol = Column(String(20), nullable=False)  # ADMIN, TECNICO, SOLICITANTE

    # Relaciones
    tickets_solicitados = relationship("Ticket", foreign_keys="Ticket.usuario_id", back_populates="solicitante")
    tickets_asignados = relationship("Ticket", foreign_keys="Ticket.tecnico_asignado_id", back_populates="tecnico")

class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    tecnico_asignado_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    
    usuario_nombre = Column(String(100), nullable=False)
    usuario_email = Column(String(120), nullable=False)
    asunto = Column(String(200), nullable=False)
    descripcion = Column(Text, nullable=False)
    categoria_ia = Column(String(50), default="Pendiente")
    prioridad_ia = Column(String(20), default="Media")
    sugerencia_ia = Column(Text, default="")
    estado = Column(String(20), default="Abierto")  # Abierto, En Proceso, Resuelto
    fecha_creacion = Column(DateTime, default=datetime.datetime.utcnow)

    # Relaciones ORM
    solicitante = relationship("User", foreign_keys=[usuario_id], back_populates="tickets_solicitados")
    tecnico = relationship("User", foreign_keys=[tecnico_asignado_id], back_populates="tickets_asignados")

def init_db():
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        # Cargar usuarios base si la tabla está vacía
        if db.query(User).count() == 0:
            usuarios_iniciales = [
                User(
                    nombre="Administrador TI", 
                    email="admin@smartdesk.gt", 
                    password_hash=hashear_password("admin123"), 
                    rol="ADMIN"
                ),
                User(
                    nombre="Técnico Carlos López", 
                    email="carlos@smartdesk.gt", 
                    password_hash=hashear_password("tec123"), 
                    rol="TECNICO"
                ),
                User(
                    nombre="Técnica María Morales", 
                    email="maria@smartdesk.gt", 
                    password_hash=hashear_password("tec123"), 
                    rol="TECNICO"
                ),
                User(
                    nombre="Kimberly Calel", 
                    email="kimberly@smartdesk.gt", 
                    password_hash=hashear_password("user123"), 
                    rol="SOLICITANTE"
                )
            ]
            db.add_all(usuarios_iniciales)
            db.commit()
    finally:
        db.close()

def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()