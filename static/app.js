let usuarioActivo = null;
let listaTicketsGlobal = [];
let listaTecnicos = [];

document.addEventListener("DOMContentLoaded", () => {
    const sesionGuardada = localStorage.getItem("smartdesk_user");
    if (sesionGuardada) {
        usuarioActivo = JSON.parse(sesionGuardada);
        mostrarApp();
    }

    // Submit Login
    document.getElementById("formLogin").addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = document.getElementById("btnLogin");
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Ingresando...`;

        const payload = {
            email: document.getElementById("loginEmail").value.trim(),
            password: document.getElementById("loginPassword").value.trim()
        };

        try {
            const resp = await fetch("/api/login", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.detail || "Credenciales incorrectas");
            }

            usuarioActivo = await resp.json();
            localStorage.setItem("smartdesk_user", JSON.stringify(usuarioActivo));
            mostrarApp();
        } catch (error) {
            alert(error.message);
        } finally {
            btn.disabled = false;
            btn.innerText = "Iniciar Sesión";
        }
    });

    // Submit Crear Ticket
    document.getElementById("formCrearTicket").addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = document.getElementById("btnCrearTicket");
        btn.disabled = true;
        btn.innerHTML = `<span class="spinner-border spinner-border-sm"></span> Auto-enrutando con IA...`;

        const ticketData = {
            usuario_id: usuarioActivo.id,
            asunto: document.getElementById("ticketAsunto").value,
            descripcion: document.getElementById("ticketDescripcion").value
        };

        try {
            const resp = await fetch("/api/tickets", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(ticketData)
            });

            if (!resp.ok) throw new Error("Error al registrar incidente");

            document.getElementById("formCrearTicket").reset();
            await cargarTickets();
        } catch (err) {
            alert(err.message);
        } finally {
            btn.disabled = false;
            btn.innerHTML = `<i class="bi bi-stars"></i> Enviar y Auto-Enrutar`;
        }
    });

    // Formulario Nuevo Usuario (Admin)
    document.getElementById("formNuevoUsuario").addEventListener("submit", async (e) => {
        e.preventDefault();
        const btn = document.getElementById("btnGuardarUsuario");
        btn.disabled = true;

        const payload = {
            nombre: document.getElementById("nuevoNombre").value.trim(),
            email: document.getElementById("nuevoEmail").value.trim(),
            password: document.getElementById("nuevoPassword").value.trim(),
            rol: document.getElementById("nuevoRol").value
        };

        try {
            const resp = await fetch("/api/usuarios", {
                method: "POST",
                headers: { "Content-Type": "application/json" },
                body: JSON.stringify(payload)
            });

            if (!resp.ok) {
                const err = await resp.json();
                throw new Error(err.detail || "Error al registrar");
            }

            document.getElementById("formNuevoUsuario").reset();
            await cargarListaPersonal();
            await cargarTecnicos();
            await cargarTickets();
            alert("Usuario registrado con éxito.");
        } catch (err) {
            alert(err.message);
        } finally {
            btn.disabled = false;
        }
    });

    // Filtros
    document.getElementById("filtroTexto").addEventListener("input", renderizarTickets);
    document.getElementById("filtroPrioridad").addEventListener("change", renderizarTickets);
    document.getElementById("filtroEstado").addEventListener("change", renderizarTickets);
    document.getElementById("filtroTecnico").addEventListener("change", renderizarTickets);
});

function completarLogin(email, password) {
    document.getElementById("loginEmail").value = email;
    document.getElementById("loginPassword").value = password;
    document.getElementById("formLogin").requestSubmit();
}

async function mostrarApp() {
    document.getElementById("seccionLogin").classList.add("d-none");
    document.getElementById("seccionApp").classList.remove("d-none");

    document.getElementById("navUsuarioNombre").innerText = usuarioActivo.nombre;
    const badgeRol = document.getElementById("navUsuarioRol");
    badgeRol.innerText = usuarioActivo.rol;

    const btnGestion = document.getElementById("btnGestionPersonal");

    if (usuarioActivo.rol === "ADMIN") {
        badgeRol.className = "badge bg-danger";
        btnGestion.classList.remove("d-none");
        document.getElementById("filtroTecnico").parentElement.classList.remove("d-none");
    } else if (usuarioActivo.rol === "TECNICO") {
        badgeRol.className = "badge bg-warning text-dark";
        btnGestion.classList.add("d-none");
        document.getElementById("filtroTecnico").parentElement.classList.add("d-none");
    } else {
        badgeRol.className = "badge bg-info text-dark";
        btnGestion.classList.add("d-none");
        document.getElementById("filtroTecnico").parentElement.classList.add("d-none");
    }

    const panelRegistro = document.getElementById("panelRegistro");
    const panelTabla = document.getElementById("panelTabla");

    if (usuarioActivo.rol === "SOLICITANTE") {
        panelRegistro.classList.remove("d-none");
        panelTabla.className = "col-lg-9";
    } else {
        panelRegistro.classList.add("d-none");
        panelTabla.className = "col-lg-12";
    }

    if (usuarioActivo.rol === "ADMIN") {
        await cargarTecnicos();
    }

    await cargarTickets();
}

function cerrarSesion() {
    localStorage.removeItem("smartdesk_user");
    usuarioActivo = null;
    listaTicketsGlobal = [];
    document.getElementById("seccionApp").classList.add("d-none");
    document.getElementById("seccionLogin").classList.remove("d-none");
}

async function cargarTecnicos() {
    try {
        const resp = await fetch("/api/tecnicos");
        if (resp.ok) {
            listaTecnicos = await resp.json();
            
            // Poblar el filtro de técnicos del dashboard
            const selectFiltro = document.getElementById("filtroTecnico");
            selectFiltro.innerHTML = `<option value="">Todos los Técnicos</option>` + 
                listaTecnicos.map(t => `<option value="${t.nombre}">${t.nombre}</option>`).join("");
        }
    } catch (err) {
        console.error("Error al obtener técnicos:", err);
    }
}

async function cargarTickets() {
    if (!usuarioActivo) return;
    const tbody = document.getElementById("tbodyTickets");
    try {
        const resp = await fetch(`/api/tickets?user_id=${usuarioActivo.id}`);
        if (!resp.ok) throw new Error("Fallo en la respuesta del servidor");
        listaTicketsGlobal = await resp.json();
        renderizarTickets();
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="7" class="text-center text-danger py-4">Error al cargar datos del servidor.</td></tr>`;
    }
}

// ----------------- Gestión de Personal (Admin) -----------------
async function cargarListaPersonal() {
    const tbody = document.getElementById("tbodyPersonal");
    try {
        const resp = await fetch("/api/usuarios");
        const usuarios = await resp.json();

        tbody.innerHTML = usuarios.map(u => {
            const esMismoAdmin = u.id === usuarioActivo.id;
            const btnEliminar = esMismoAdmin 
                ? `<span class="badge bg-secondary">Tú</span>` 
                : `<button class="btn btn-outline-danger btn-sm py-0 px-2" onclick="eliminarUsuario(${u.id}, '${u.nombre}')"><i class="bi bi-trash"></i></button>`;

            return `
                <tr>
                    <td>${u.id}</td>
                    <td class="fw-semibold">${u.nombre}</td>
                    <td>${u.email}</td>
                    <td><span class="badge ${u.rol === 'ADMIN' ? 'bg-danger' : (u.rol === 'TECNICO' ? 'bg-warning text-dark' : 'bg-info text-dark')}">${u.rol}</span></td>
                    <td class="text-center">${btnEliminar}</td>
                </tr>
            `;
        }).join("");
    } catch (err) {
        tbody.innerHTML = `<tr><td colspan="5" class="text-danger text-center">Error al cargar usuarios.</td></tr>`;
    }
}

async function eliminarUsuario(id, nombre) {
    if (!confirm(`¿Estás segura de eliminar al usuario "${nombre}"?`)) return;

    try {
        const resp = await fetch(`/api/usuarios/${id}?admin_id=${usuarioActivo.id}`, {
            method: "DELETE"
        });
        if (!resp.ok) {
            const err = await resp.json();
            throw new Error(err.detail || "Error al eliminar");
        }
        await cargarListaPersonal();
        await cargarTecnicos();
        await cargarTickets();
    } catch (err) {
        alert(err.message);
    }
}

// ----------------- Renderizado y Filtros -----------------
function normalizarTexto(txt) {
    return (txt || "").toLowerCase().normalize("NFD").replace(/[\u0300-\u036f]/g, "");
}

function obtenerBadgePrioridad(prioridad) {
    const p = normalizarTexto(prioridad);
    if (p.includes("critica")) return "badge-Critica";
    if (p.includes("alta")) return "badge-Alta";
    if (p.includes("media")) return "badge-Media";
    if (p.includes("baja")) return "badge-Baja";
    return "bg-secondary text-white";
}

function obtenerBadgeEstado(estado) {
    if (estado === "Resuelto") return "background-color: #198754; color: white;";
    if (estado === "En Proceso") return "background-color: #6f42c1; color: white;";
    return "background-color: #0d6efd; color: white;";
}

function formatearSugerencia(texto, ticketId) {
    if (!texto) return `<span class="text-muted small">Sin sugerencia disponible.</span>`;
    let formateado = texto
        .replace(/\*\*(.*?)\*\*/g, '<strong class="text-dark">$1</strong>')
        .replace(/\n/g, '<br>');

    return `
        <div class="sugerencia-box">
            <div id="sug-corta-${ticketId}" class="sugerencia-colapsada">${formateado}</div>
            <button class="btn btn-link btn-toggle-ver text-primary fw-semibold mt-1" onclick="toggleVerSugerencia(${ticketId}, this)">
                Ver más...
            </button>
        </div>
    `;
}

function toggleVerSugerencia(ticketId, btn) {
    const contenedor = document.getElementById(`sug-corta-${ticketId}`);
    if (contenedor.classList.contains("sugerencia-colapsada")) {
        contenedor.classList.remove("sugerencia-colapsada");
        btn.innerText = "Ver menos";
    } else {
        contenedor.classList.add("sugerencia-colapsada");
        btn.innerText = "Ver más...";
    }
}

function renderizarTickets() {
    const tbody = document.getElementById("tbodyTickets");
    const fTexto = normalizarTexto(document.getElementById("filtroTexto").value);
    const fPrioridad = normalizarTexto(document.getElementById("filtroPrioridad").value);
    const fEstado = document.getElementById("filtroEstado").value;
    const fTecnico = document.getElementById("filtroTecnico").value;

    const filtrados = listaTicketsGlobal.filter(t => {
        const matchTexto = normalizarTexto(t.asunto).includes(fTexto) || 
                           normalizarTexto(t.usuario_nombre).includes(fTexto);
        const matchPrioridad = fPrioridad === "" || normalizarTexto(t.prioridad_ia).includes(fPrioridad);
        const matchEstado = fEstado === "" || (t.estado === fEstado);
        const matchTecnico = fTecnico === "" || (t.tecnico_nombre === fTecnico);
        return matchTexto && matchPrioridad && matchEstado && matchTecnico;
    });

    if (filtrados.length === 0) {
        let mensaje = "No se encontraron incidentes registrados.";
        if (usuarioActivo.rol === "TECNICO") {
            mensaje = "No tienes incidentes asignados actualmente.";
        }
        tbody.innerHTML = `<tr><td colspan="7" class="text-center py-4 text-muted">${mensaje}</td></tr>`;
        return;
    }

    tbody.innerHTML = filtrados.map(t => {
        let celdaTecnico = "";
        if (usuarioActivo.rol === "ADMIN") {
            const opcionesTecnicos = (listaTecnicos || []).map(tec => 
                `<option value="${tec.id}" ${t.tecnico_asignado_id === tec.id ? "selected" : ""}>${tec.nombre}</option>`
            ).join("");

            celdaTecnico = `
                <select class="form-select form-select-sm" onchange="asignarTecnico(${t.id}, this.value)">
                    <option value="">-- Sin Asignar --</option>
                    ${opcionesTecnicos}
                </select>
            `;
        } else {
            const esAsignado = t.tecnico_nombre && t.tecnico_nombre !== "Sin Asignar";
            celdaTecnico = `<span class="badge ${esAsignado ? 'bg-primary' : 'bg-secondary'}">${t.tecnico_nombre}</span>`;
        }

        let celdaEstado = "";
        if (usuarioActivo.rol === "TECNICO" || usuarioActivo.rol === "ADMIN") {
            celdaEstado = `
                <select class="form-select form-select-sm" onchange="cambiarEstado(${t.id}, this.value)">
                    <option value="Abierto" ${t.estado === "Abierto" ? "selected" : ""}>🔵 Abierto</option>
                    <option value="En Proceso" ${t.estado === "En Proceso" ? "selected" : ""}>🟣 En Proceso</option>
                    <option value="Resuelto" ${t.estado === "Resuelto" ? "selected" : ""}>🟢 Resuelto</option>
                </select>
            `;
        } else {
            celdaEstado = `<span class="badge" style="${obtenerBadgeEstado(t.estado)}">${t.estado}</span>`;
        }

        return `
            <tr>
                <td class="fw-bold text-muted">${t.id}</td>
                <td>
                    <div class="fw-bold text-dark">${t.asunto}</div>
                    <small class="text-muted">${t.usuario_nombre}</small>
                </td>
                <td><span class="badge bg-secondary">${t.categoria_ia}</span></td>
                <td><span class="badge ${obtenerBadgePrioridad(t.prioridad_ia)}">${t.prioridad_ia}</span></td>
                <td>${formatearSugerencia(t.sugerencia_ia, t.id)}</td>
                <td>${celdaTecnico}</td>
                <td>${celdaEstado}</td>
            </tr>
        `;
    }).join("");
}

async function cambiarEstado(ticketId, nuevoEstado) {
    try {
        const resp = await fetch(`/api/tickets/${ticketId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ estado: nuevoEstado })
        });
        if (!resp.ok) throw new Error("No se pudo actualizar el estado");
        await cargarTickets();
    } catch (err) {
        alert("Error: " + err.message);
    }
}

async function asignarTecnico(ticketId, tecnicoId) {
    try {
        const payload = { tecnico_asignado_id: tecnicoId ? parseInt(tecnicoId) : null };
        const resp = await fetch(`/api/tickets/${ticketId}`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(payload)
        });
        if (!resp.ok) throw new Error("No se pudo asignar el técnico");
        await cargarTickets();
    } catch (err) {
        alert("Error: " + err.message);
    }
}