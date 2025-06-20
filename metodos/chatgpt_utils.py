from openai import OpenAI
from django.conf import settings
from django.utils.safestring import mark_safe
from typing import List, Dict, Optional
import logging
import matplotlib.pyplot as plt
import io
import base64

# Configuración de logging
logger = logging.getLogger(__name__)

# Configuración de OpenAI
client = OpenAI(api_key=settings.OPENAI_API_KEY)


def construir_prompt(pasos: List[Dict]) -> str:
    """
    Construye un prompt claro y estructurado para ChatGPT.
    Args:
        pasos: Lista de diccionarios con los pasos del método Simplex.
    Returns:
        str: Prompt formateado.
    """
    if not pasos:
        raise ValueError("La lista de pasos no puede estar vacía")

    pasos_texto = "\n".join(
        f"**Paso {i + 1}**: {paso.get('explicacion', 'Descripción no disponible')}\n"
        f"- Tabla: {paso.get('tabla', 'N/A')}\n"
        f"- Variables básicas: {paso.get('variables_basicas', [])}"
        for i, paso in enumerate(pasos)
    )

    return f"""
Eres un profesor experto en Investigación de Operaciones. Explica el procedimiento del método Simplex 
para el siguiente problema, siguiendo estas instrucciones:

1. **Contexto**: Breve introducción al método (1-2 oraciones).
2. **Explicación por pasos**: Describe qué ocurre en cada paso y por qué es importante.
3. **Conclusión**: Resumen del resultado y su interpretación.

**Datos del problema:**
{pasos_texto}

**Requisitos:**
- Lenguaje claro y didáctico.
- Máximo 500 palabras.
- Destaca los conceptos clave (pivote, variables básicas, optimalidad).
- Usa Markdown para formato (títulos, listas, énfasis).
"""


def generar_explicacion_simplex(pasos: List[Dict]) -> Optional[str]:
    """
    Genera una explicación del método Simplex usando ChatGPT.

    Args:
        pasos: Lista de pasos del método Simplex (debe contener 'explicacion' y 'tabla').

    Returns:
        str: Explicación generada (en Markdown) o None si falla.
    """
    if not pasos:
        logger.warning("Se intentó generar una explicación sin pasos")
        return None

    try:
        prompt = construir_prompt(pasos)

        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=[
                {
                    "role": "system",
                    "content": (
                        "Eres un asistente especializado en matemáticas aplicadas. "
                        "Respuestas claras, técnicas pero accesibles. Usa Markdown."
                    ),
                },
                {"role": "user", "content": prompt},
            ],
            temperature=0.5,
            max_tokens=800,
            top_p=0.9,
            frequency_penalty=0.2,
        )

        explicacion = response.choices[0].message.content
        return mark_safe(explicacion)

    except Exception as e:
        logger.error(f"Error al generar explicación: {str(e)}", exc_info=True)
        return f"⚠️ Error al generar explicación: {str(e)}"



def generar_grafica():
    plt.figure(figsize=(6,4))
    x = [1,2,3,4,5]
    y = [10, 5, 7, 3, 8]
    plt.plot(x, y)
    plt.title('Gráfica de ejemplo')

    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    plt.close()
    buf.seek(0)

    img_base64 = base64.b64encode(buf.read()).decode('utf-8')
    return img_base64