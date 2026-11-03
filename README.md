# SmartDesk AI — Plataforma Inteligente de Mesa de Ayuda TI
 
> **Proyecto Final — Análisis de Sistemas II **  
> **Universidad Mariano Gálvez de Guatemala**  
> Facultad de Ingeniería en Sistemas de Información y Ciencias de la Computación  
 
---
 
## Descripción del Proyecto
 
**SmartDesk AI** es un sistema integral de mesa de ayuda técnica (*Help Desk*) diseñado para automatizar el triaje, clasificación y enrutamiento operativo de incidentes de TI en organizaciones.
 
La plataforma integra modelos de lenguaje de gran escala (**Google Gemini**) mediante llamadas estructuradas en formato JSON. Al registrarse un incidente, el sistema analiza el contexto semántico, asigna una categoría técnica (*Hardware, Software, Redes, Accesos, Soporte General*), determina su nivel de criticidad (*Baja, Media, Alta, Crítica*), genera una pauta diagnóstica para el soporte de Nivel 2 y preasigna automáticamente al técnico más idóneo evaluando su historial de resolución y su carga activa de trabajo.
 
---
 
## Características Principales
 
- **Control de Acceso Basado en Roles (RBAC):**
  - **Solicitante:** creación de reportes técnicos, seguimiento en tiempo real del estado (*Abierto*, *En Proceso*, *Resuelto*) y visualización del técnico responsable asignado.
  - **Técnico de Soporte:** vista personalizada con los incidentes asignados a su cargo, acceso al diagnóstico generado por la IA y transición de estados del ciclo de vida del ticket.
  - **Administrador de TI:** monitoreo global de la mesa de ayuda con filtros reactivos (por texto, prioridad, estado y técnico), reasignación manual de responsables y módulo completo de gestión de personal (altas y bajas de usuarios).
- **Auto-Enrutamiento Inteligente:** algoritmo heurístico que cruza la categoría inferida por la IA con el historial de incidentes resueltos por cada técnico y su volumen de tickets activos.
- **Asistencia Diagnóstica N2:** formateo estructurado con viñetas (**Causa probable**, **Diagnóstico**, **Acción recomendada**) y botón interactivo para lectura ágil.
- **Tolerancia a Fallos y Resiliencia:** redundancia multimodelo (`gemini-2.5-flash`, `gemini-1.5-flash`, `gemini-1.5-pro`) con reintentos controlados y degradación elegante (*fallback*) amigable, sin exponer códigos de error crudos (como HTTP 503).
- **Persistencia Relacional Transaccional:** almacenamiento local consistente mediante SQLite y SQLAlchemy ORM.
---
 
## Eje Obligatorio de Ciberseguridad
 
El sistema incorpora tres controles defensivos alineados a los requerimientos de la cátedra:
 
1. **Gestión Aislada de Credenciales:** la clave `GEMINI_API_KEY` se consume exclusivamente en tiempo de ejecución a través de variables de entorno (`.env`), archivo que se encuentra estrictamente excluido del repositorio mediante `.gitignore`.
2. **Sanitización Activa contra Prompt Injection:** el backend implementa filtros basados en expresiones regulares que interceptan patrones de evasión (ej. `"ignore previous instructions"`, `"dame la api_key"`), sustituyéndolos por etiquetas neutralizadas `[BLOQUEADO]` antes de interactuar con el modelo de IA.
3. **Protección de Datos y Cuentas:** las contraseñas de los usuarios se almacenan en la base de datos aplicando un algoritmo de resumen criptográfico irreversible (**SHA-256**).
---
 
## Pila Tecnológica
 
| Capa | Tecnologías |
|------|-------------|
| **Backend** | Python 3.10+, FastAPI, Uvicorn (servidor ASGI), SQLAlchemy ORM, Pydantic V2 |
| **Inteligencia Artificial** | SDK oficial `google-genai` (Google Gemini Flash & Pro API) |
| **Frontend** | HTML5, JavaScript moderno (Fetch API asíncrono), Bootstrap 5 y Bootstrap Icons |
| **Pruebas Automatizadas** | Pytest, HTTPX |
| **Base de Datos** | SQLite (archivo local `tickets.db`) |
 
---
 
## Estructura del Repositorio
 
```text
smartdesk-ai/
├── .env.example          # Plantilla pública de variables de entorno
├── .gitignore            # Exclusión de entornos virtuales, base de datos y .env
├── requirements.txt      # Lista de dependencias del proyecto
├── main.py               # API REST, controladores, RBAC y lógica de auto-enrutamiento
├── database.py           # Conexión SQLAlchemy, modelos ORM (User, Ticket) y semilla
├── ai_service.py         # Módulo de integración con Gemini, sanitización y fallback
├── test_app.py           # Suite de pruebas automatizadas (6 pruebas unitarias)
└── static/
    ├── index.html        # Vistas de autenticación y paneles interactivos por rol
    └── app.js            # Lógica cliente, consumo de endpoints y filtros reactivos
```
 
---
 
## Instrucciones de Instalación y Despliegue Local
 
Sigue estos pasos en tu terminal (PowerShell o Bash) para clonar y ejecutar el proyecto desde cero.
 
### 1. Clonar el repositorio
 
```bash
git clone https://github.com/KimJCC/SmartDesk-AI.git
cd SmartDesk-AI
```
 
### 2. Configurar el entorno virtual
 
**En Windows (PowerShell):**
 
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```
 
**En Linux / macOS:**
 
```bash
python3 -m venv venv
source venv/bin/activate
```
 
### 3. Instalar las dependencias
 
```bash
pip install -r requirements.txt
```
 
### 4. Configurar las variables de entorno
 
Crea un archivo llamado `.env` en la raíz del proyecto tomando como base el archivo `.env.example`:
 
```env
GEMINI_API_KEY=tu_api_key_de_google_aqui
DATABASE_URL=sqlite:///./tickets.db
```
 
> **Nota:** obtén tu API Key gratuita en [Google AI Studio](https://aistudio.google.com/app/apikey).
 
### 5. Iniciar la aplicación
 
```bash
uvicorn main:app --reload
```
 
La aplicación web se ejecutará en: **http://127.0.0.1:8000**
 
---
 
## 🔑 Credenciales de Acceso para Pruebas
 
El sistema inicializa automáticamente una base de datos con cuentas demo para cada rol:
 
| Rol | Correo Electrónico | Contraseña | Permisos Principales |
|-----|--------------------|------------|----------------------|
| **Administrador** | `admin@smartdesk.gt` | `admin123` | Panel global, reasignación, gestión de personal (altas/bajas) |
| **Técnico TI** | `carlos@smartdesk.gt` | `tec123` | Gestión de tickets asignados, cambio de estado, sugerencias N2 |
| **Técnico TI** | `maria@smartdesk.gt` | `tec123` | Gestión de tickets asignados, cambio de estado, sugerencias N2 |
| **Solicitante** | `kimberly@smartdesk.gt` | `user123` | Registro de incidentes, seguimiento de estado y técnico |
 
> **Nota:** la interfaz de login cuenta además con botones de acceso rápido de un solo clic para alternar entre roles.
