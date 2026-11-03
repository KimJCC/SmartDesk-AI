from fastapi import FastAPI, Depends, HTTPException, Query
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, EmailStr, Field, ConfigDict
from typing import List, Optional

from database import init_db, get_db, Ticket, User, hashear_password
from ai_service import clasificar_ticket_ia, sanitizar_texto

app = FastAPI(title="SmartDesk AI - Gestión Inteligente de Tickets")

# Inicializar Base de Datos con modelos y usuarios de prueba[cite: 2]
init_db()

# Archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# ----------------- Esquemas Pydantic -----------------

class UserCreateSchema(BaseModel):
    nombre: str = Field(..., min_length=2, max_length=100)
    email: EmailStr
    password: str = Field(..., min_length=4)
    rol: str = Field(..., pattern="^(ADMIN|TECNICO|SOLICITANTE)$")

class LoginSchema(BaseModel):
    email: EmailStr
    password: str

class UserResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    nombre: str
    email: str
    rol: str

class TicketCreateSchema(BaseModel):
    usuario_id: int
    asunto: str = Field(..., min_length=3, max_length=200)
    descripcion: str = Field(..., min_length=5, max_length=2000)

class TicketUpdateSchema(BaseModel):
    estado: Optional[str] = Field(None, pattern="^(Abierto|En Proceso|Resuelto)$")
    tecnico_asignado_id: Optional[int] = None

class TicketResponseSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    usuario_id: Optional[int] = None
    tecnico_asignado_id: Optional[int] = None
    tecnico_nombre: Optional[str] = "Sin Asignar"
    usuario_nombre: str
    usuario_email: str
    asunto: str
    descripcion: str
    categoria_ia: str
    prioridad_ia: str
    sugerencia_ia: str
    estado: str

# ----------------- Función de Auto-Enrutamiento Inteligente -----------------

def calcular_tecnico_optimo(categoria: str, db: Session) -> Optional[User]:
    """
    Selecciona al mejor técnico disponible evaluando:
    1. Especialidad histórica (tickets resueltos en esa categoría).
    2. Carga operativa actual (tickets en estado 'Abierto' o 'En Proceso').
    """
    tecnicos = db.query(User).filter(User.rol == "TECNICO").all()
    if not tecnicos:
        return None

    mejor_tecnico = None
    mejor_puntuacion = -9999

    for tec in tecnicos:
        # Experiencia en la categoría
        resueltos_categoria = db.query(Ticket).filter(
            Ticket.tecnico_asignado_id == tec.id,
            Ticket.categoria_ia == categoria,
            Ticket.estado == "Resuelto"
        ).count()

        # Carga activa actual (penaliza si está saturado)
        carga_activa = db.query(Ticket).filter(
            Ticket.tecnico_asignado_id == tec.id,
            Ticket.estado.in_(["Abierto", "En Proceso"])
        ).count()

        # Puntuación de idoneidad: +2 por cada resuelto en el área, -1 por cada pendiente
        puntuacion = (resueltos_categoria * 2) - carga_activa

        if puntuacion > mejor_puntuacion:
            mejor_puntuacion = puntuacion
            mejor_tecnico = tec

    return mejor_tecnico or tecnicos[0]

# ----------------- Endpoints -----------------

@app.get("/")
def read_root():
    return FileResponse("static/index.html")

@app.post("/api/login", response_model=UserResponseSchema)
def login(credentials: LoginSchema, db: Session = Depends(get_db)):
    pwd_hash = hashear_password(credentials.password)
    user = db.query(User).filter(User.email == credentials.email, User.password_hash == pwd_hash).first()
    if not user:
        raise HTTPException(status_code=401, detail="Correo o contraseña incorrectos")
    return user

@app.get("/api/tecnicos", response_model=List[UserResponseSchema])
def listar_tecnicos(db: Session = Depends(get_db)):
    return db.query(User).filter(User.rol == "TECNICO").all()

@app.post("/api/tickets", response_model=TicketResponseSchema)
def crear_ticket(ticket_in: TicketCreateSchema, db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == ticket_in.usuario_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    asunto_sanitizado = sanitizar_texto(ticket_in.asunto)
    desc_sanitizada = sanitizar_texto(ticket_in.descripcion)

    # Inferencia con IA
    resultado_ia = clasificar_ticket_ia(asunto_sanitizado, desc_sanitizada)

    # Auto-enrutamiento inteligente[cite: 2]
    tecnico_asignado = calcular_tecnico_optimo(resultado_ia["categoria"], db)

    nuevo_ticket = Ticket(
        usuario_id=user.id,
        tecnico_asignado_id=tecnico_asignado.id if tecnico_asignado else None,
        usuario_nombre=user.nombre,
        usuario_email=user.email,
        asunto=asunto_sanitizado,
        descripcion=desc_sanitizada,
        categoria_ia=resultado_ia["categoria"],
        prioridad_ia=resultado_ia["prioridad"],
        sugerencia_ia=resultado_ia["sugerencia"],
        estado="Abierto"
    )
    db.add(nuevo_ticket)
    db.commit()
    db.refresh(nuevo_ticket)
    
    return TicketResponseSchema(
        id=nuevo_ticket.id,
        usuario_id=nuevo_ticket.usuario_id,
        tecnico_asignado_id=nuevo_ticket.tecnico_asignado_id,
        tecnico_nombre=tecnico_asignado.nombre if tecnico_asignado else "Sin Asignar",
        usuario_nombre=nuevo_ticket.usuario_nombre,
        usuario_email=nuevo_ticket.usuario_email,
        asunto=nuevo_ticket.asunto,
        descripcion=nuevo_ticket.descripcion,
        categoria_ia=nuevo_ticket.categoria_ia,
        prioridad_ia=nuevo_ticket.prioridad_ia,
        sugerencia_ia=nuevo_ticket.sugerencia_ia,
        estado=nuevo_ticket.estado
    )

@app.get("/api/tickets", response_model=List[TicketResponseSchema])
def listar_tickets(user_id: int = Query(...), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no identificado")

    if user.rol == "ADMIN":
        tickets = db.query(Ticket).order_by(Ticket.id.desc()).all()
    elif user.rol == "TECNICO":
        tickets = db.query(Ticket).filter(Ticket.tecnico_asignado_id == user.id).order_by(Ticket.id.desc()).all()
    else:  # SOLICITANTE
        tickets = db.query(Ticket).filter(Ticket.usuario_id == user.id).order_by(Ticket.id.desc()).all()

    resultados = []
    for t in tickets:
        nombre_tec = t.tecnico.nombre if t.tecnico else "Sin Asignar"
        resultados.append(
            TicketResponseSchema(
                id=t.id,
                usuario_id=t.usuario_id,
                tecnico_asignado_id=t.tecnico_asignado_id,
                tecnico_nombre=nombre_tec,
                usuario_nombre=t.usuario_nombre,
                usuario_email=t.usuario_email,
                asunto=t.asunto,
                descripcion=t.descripcion,
                categoria_ia=t.categoria_ia,
                prioridad_ia=t.prioridad_ia,
                sugerencia_ia=t.sugerencia_ia,
                estado=t.estado
            )
        )

    return resultados

@app.patch("/api/tickets/{ticket_id}", response_model=TicketResponseSchema)
def actualizar_ticket(ticket_id: int, ticket_up: TicketUpdateSchema, db: Session = Depends(get_db)):
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(status_code=404, detail="Ticket no encontrado")
    
    if ticket_up.estado is not None:
        ticket.estado = ticket_up.estado

    if ticket_up.tecnico_asignado_id is not None:
        ticket.tecnico_asignado_id = ticket_up.tecnico_asignado_id if ticket_up.tecnico_asignado_id != 0 else None
    
    db.commit()
    db.refresh(ticket)
    
    nombre_tec = ticket.tecnico.nombre if ticket.tecnico else "Sin Asignar"
    return TicketResponseSchema(
        id=ticket.id,
        usuario_id=ticket.usuario_id,
        tecnico_asignado_id=ticket.tecnico_asignado_id,
        tecnico_nombre=nombre_tec,
        usuario_nombre=ticket.usuario_nombre,
        usuario_email=ticket.usuario_email,
        asunto=ticket.asunto,
        descripcion=ticket.descripcion,
        categoria_ia=ticket.categoria_ia,
        prioridad_ia=ticket.prioridad_ia,
        sugerencia_ia=ticket.sugerencia_ia,
        estado=ticket.estado
    )
    
@app.get("/api/usuarios", response_model=List[UserResponseSchema])
def listar_todos_usuarios(db: Session = Depends(get_db)):
    """Permite al Admin ver todo el personal registrado."""
    return db.query(User).order_by(User.id.asc()).all()

@app.post("/api/usuarios", response_model=UserResponseSchema)
def crear_usuario(user_in: UserCreateSchema, db: Session = Depends(get_db)):
    """Permite al Admin dar de alta nuevo personal con un rol asignado."""
    usuario_existente = db.query(User).filter(User.email == user_in.email).first()
    if usuario_existente:
        raise HTTPException(status_code=400, detail="El correo ya se encuentra registrado.")
    
    nuevo_usuario = User(
        nombre=user_in.nombre,
        email=user_in.email,
        password_hash=hashear_password(user_in.password),
        rol=user_in.rol
    )
    db.add(nuevo_usuario)
    db.commit()
    db.refresh(nuevo_usuario)
    return nuevo_usuario

@app.delete("/api/usuarios/{usuario_id}")
def eliminar_usuario(usuario_id: int, admin_id: int = Query(...), db: Session = Depends(get_db)):
    """Elimina un usuario y desvincula sus tickets asignados."""
    if usuario_id == admin_id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta de Administrador.")

    usuario = db.query(User).filter(User.id == usuario_id).first()
    if not usuario:
        raise HTTPException(status_code=404, detail="Usuario no encontrado.")

    # Desvincular tickets asignados si era técnico
    db.query(Ticket).filter(Ticket.tecnico_asignado_id == usuario_id).update({"tecnico_asignado_id": None})
    
    db.delete(usuario)
    db.commit()
    return {"mensaje": f"Usuario {usuario.nombre} eliminado correctamente."}