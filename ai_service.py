import os
import json
import re
import time
from google import genai
from google.genai import types
from dotenv import load_dotenv

load_dotenv()

# Carga de credenciales desde variables de entorno seguras[cite: 1, 2]
api_key = os.getenv("GEMINI_API_KEY")
client = genai.Client(api_key=api_key) if api_key else None

def sanitizar_texto(texto: str) -> str:
    """Neutraliza posibles inyecciones de prompt y limpia caracteres de entrada[cite: 1, 2]."""
    patrones_riesgo = [
        r"(?i)ignore previous instructions",
        r"(?i)ignora las instrucciones anteriores",
        r"(?i)system prompt",
        r"(?i)api_key",
        r"(?i)dame la clave"
    ]
    texto_limpio = texto or ""
    for patron in patrones_riesgo:
        texto_limpio = re.sub(patron, "[BLOQUEADO]", texto_limpio)
    return texto_limpio.strip()

def clasificar_ticket_ia(asunto: str, descripcion: str) -> dict:
    """Clasifica el ticket con IA y asegura un fallback amigable en caso de caídas de la API."""
    asunto_limpio = sanitizar_texto(asunto)
    desc_limpia = sanitizar_texto(descripcion)

    mensaje_fallback = (
        "**Causa:** No determinada.\n"
        "**Diagnóstico:** La sugerencia automática no está disponible en este momento por alta demanda del servicio.\n"
        "**Acción:** Se notificó al equipo técnico para evaluación y asignación manual."
    )

    if not client or not api_key:
        return {
            "categoria": "Soporte General",
            "prioridad": "Media",
            "sugerencia": mensaje_fallback
        }

    prompt = f"""
Eres un Ingeniero Especialista de Soporte TI de Nivel 2.
Analiza el siguiente incidente y devuelve ÚNICAMENTE un objeto JSON con exactamente tres claves: "categoria", "prioridad" y "sugerencia".

Reglas estrictas:
- "categoria": Debe ser una de: "Hardware", "Software", "Redes", "Accesos", "Soporte General".
- "prioridad": Debe ser una de: "Baja", "Media", "Alta", "Crítica".
- "sugerencia": Redacta la respuesta en 3 líneas estructuradas con este formato exacto:
  **Causa probable:** [Causa breve]
  **Diagnóstico:** [Procedimiento o comandos de verificación]
  **Acción recomendada:** [Paso correctivo directo]

Incidente:
- Asunto: {asunto_limpio}
- Descripción: {desc_limpia}
"""

    modelos_candidatos = [
        "gemini-2.5-flash",
        "gemini-1.5-flash",
        "gemini-1.5-pro"
    ]

    for modelo in modelos_candidatos:
        for intento in range(2):
            try:
                response = client.models.generate_content(
                    model=modelo,
                    contents=prompt,
                    config=types.GenerateContentConfig(
                        response_mime_type="application/json"
                    )
                )
                
                texto_respuesta = response.text.strip()
                if texto_respuesta.startswith("```json"):
                    texto_respuesta = texto_respuesta[7:]
                if texto_respuesta.startswith("```"):
                    texto_respuesta = texto_respuesta[3:]
                if texto_respuesta.endswith("```"):
                    texto_respuesta = texto_respuesta[:-3]
                
                data = json.loads(texto_respuesta.strip())
                return {
                    "categoria": data.get("categoria", "Soporte General"),
                    "prioridad": data.get("prioridad", "Media"),
                    "sugerencia": data.get("sugerencia", mensaje_fallback)
                }
            except Exception:
                time.sleep(1)

    # Fallback final amigable al usuario (sin códigos de error como 503 expuestos)
    return {
        "categoria": "Sin Clasificar",
        "prioridad": "Media",
        "sugerencia": mensaje_fallback
    }