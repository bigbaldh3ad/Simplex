from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView, CreateView, DetailView
from django.urls import reverse_lazy
from django.contrib import messages
from django.shortcuts import redirect
import json
import warnings
import logging
from django.shortcuts import get_object_or_404
from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from .models import ProblemaSimplex


from django.http import HttpResponse
from django.template.loader import render_to_string
from weasyprint import HTML
from .chatgpt_utils import generar_grafica
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework.permissions import IsAuthenticated

from .models import ProblemaSimplex
from .forms import SimplexForm
from .serializers import SimplexSerializer
from .formula import resolver_simplex
from .chatgpt_utils import generar_explicacion_simplex

# Configuración de logging
logger = logging.getLogger(__name__)


class SimplexListView(LoginRequiredMixin, ListView):
    model = ProblemaSimplex
    template_name = "metodo/list_simplex.html"
    context_object_name = "problemas"
    paginate_by = 10

    def get_queryset(self):
        return ProblemaSimplex.objects.filter(usuario=self.request.user).order_by(
            "-creado"
        )


class SimplexCreateView(LoginRequiredMixin, CreateView):
    model = ProblemaSimplex
    form_class = SimplexForm
    template_name = "metodo/add_simplex.html"
    success_url = reverse_lazy("list_simplex")

    def form_valid(self, form):
        form.instance.usuario = self.request.user
        self.object = form.save()

        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                resultado = resolver_simplex(self.object)

                for warning in w:
                    messages.warning(self.request, str(warning.message))

            if resultado.get("error"):
                raise ValueError(resultado["error"])

            if not resultado.get("solucion"):
                raise ValueError("El solver no devolvió una solución válida")

            # Procesamiento de pasos
            pasos = resultado.get("pasos", [])
            pasos_serializables = []
            for paso in pasos:
                paso_serializado = {
                    "titulo": paso.get("titulo", "Paso"),
                    "tabla": (
                        paso["tabla"].tolist()
                        if hasattr(paso["tabla"], "tolist")
                        else paso["tabla"]
                    ),
                    "explicacion": paso.get("explicacion", ""),
                    "variables_basicas": paso.get("variables_basicas", []),
                    "pivote": paso.get("pivote", {}),
                }
                pasos_serializables.append(paso_serializado)

            # Generación de explicación con ChatGPT (versión mejorada)
            explicacion_ia = generar_explicacion_simplex(pasos_serializables)
            if not explicacion_ia:
                logger.warning(
                    "No se pudo generar explicación para el problema ID: %s",
                    self.object.id,
                )
                explicacion_ia = "No se pudo generar la explicación automática."

            # Guardar resultados
            self.object.pasos = pasos_serializables
            self.object.tabla_inicial = json.dumps(pasos[0]["tabla"]) if pasos else None
            self.object.tabla_final = json.dumps(resultado["tabla_final"])

            solucion_data = {
                "variables": resultado["solucion"],
                "valor_optimo": resultado["valor_optimo"],
                "optimalidad": resultado.get("optimalidad", "óptimo"),
                "iteraciones": resultado["iteraciones"],
                "variables_basicas_finales": resultado.get("variables_basicas", []),
            }
            self.object.solucion = json.dumps(solucion_data)
            self.object.grafico_base64 = resultado.get("grafico")
            self.object.variables_holgura = (
                len(resultado["solucion"]) - self.object.variables_decision
            )
            self.object.iteraciones_realizadas = resultado["iteraciones"]

            # Manejo de estados
            if resultado.get("optimalidad") == "no acotado":
                self.object.estado = "no_acotado"
            elif resultado.get("warning"):
                self.object.estado = "advertencia"
                self.object.advertencias = [resultado["warning"]]
            else:
                self.object.estado = "optimo"

            self.object.explicacion_chatgpt = explicacion_ia
            self.object.save()

            messages.success(self.request, "Problema resuelto exitosamente!")
            if resultado.get("warning"):
                messages.warning(self.request, resultado["warning"])

        except ValueError as e:
            logger.error("Error al resolver problema Simplex: %s", str(e))
            self.object.estado = "error"
            self.object.save()
            messages.error(self.request, f"Error al resolver el problema: {str(e)}")
            return self.form_invalid(form)
        except Exception as e:
            logger.exception("Error inesperado al procesar problema Simplex")
            self.object.estado = "error"
            self.object.save()
            messages.error(
                self.request,
                "Ocurrió un error inesperado. Por favor intenta nuevamente.",
            )
            return self.form_invalid(form)

        return redirect(self.get_success_url())


class SimplexDetailView(LoginRequiredMixin, DetailView):
    model = ProblemaSimplex
    template_name = "metodo/detail_simplex.html"
    context_object_name = "problema"

    def get_queryset(self):
        return ProblemaSimplex.objects.filter(usuario=self.request.user)

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        problema = self.object

        # Procesamiento de solución
        solucion = None
        if problema.solucion:
            try:
                solucion = json.loads(problema.solucion)
            except json.JSONDecodeError as e:
                logger.error(
                    "Error decodificando solución JSON para problema ID %s: %s",
                    problema.id,
                    str(e),
                )
                solucion = None

        # Procesamiento de pasos
        pasos = problema.pasos if problema.pasos else []

        if not pasos and problema.tabla_inicial and problema.tabla_final:
            pasos = [
                {
                    "titulo": "Tabla Inicial",
                    "tabla": json.loads(problema.tabla_inicial),
                    "explicacion": "Tabla inicial del método Simplex",
                },
                {
                    "titulo": "Tabla Final",
                    "tabla": json.loads(problema.tabla_final),
                    "explicacion": "Tabla final con la solución óptima",
                },
            ]

        datos_completos = {
            "solucion": solucion,
            "pasos": pasos,
            "grafica": problema.grafico_base64,
            "es_2d": problema.variables_decision == 2,
            "estado": problema.estado,
            "iteraciones": problema.iteraciones_realizadas,
            "tabla_inicial": (
                json.loads(problema.tabla_inicial) if problema.tabla_inicial else None
            ),
            "tabla_final": (
                json.loads(problema.tabla_final) if problema.tabla_final else None
            ),
        }

        context["datos_completos"] = datos_completos
        context["explicacion_chatgpt"] = problema.explicacion_chatgpt
        return context


class SimplexListCreateView(ListCreateAPIView):
    serializer_class = SimplexSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProblemaSimplex.objects.filter(usuario=self.request.user).order_by(
            "-creado"
        )

    def perform_create(self, serializer):
        problema = serializer.save(usuario=self.request.user)

        try:
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter("always")
                resultado = resolver_simplex(problema)
                if w:
                    problema.advertencias = [str(warn.message) for warn in w]

            if resultado.get("error"):
                problema.estado = "error"
                problema.save()
                raise ValueError(resultado["error"])

            if not resultado.get("solucion"):
                problema.estado = "error"
                problema.save()
                raise ValueError("No se encontró solución válida")

            # Procesamiento de pasos
            pasos = resultado.get("pasos", [])
            pasos_serializables = []
            for paso in pasos:
                paso_serializado = {
                    "titulo": paso.get("titulo", "Paso"),
                    "tabla": (
                        paso["tabla"].tolist()
                        if hasattr(paso["tabla"], "tolist")
                        else paso["tabla"]
                    ),
                    "explicacion": paso.get("explicacion", ""),
                    "variables_basicas": paso.get("variables_basicas", []),
                    "pivote": paso.get("pivote", {}),
                }
                pasos_serializables.append(paso_serializado)

            # Generación de explicación con ChatGPT (versión mejorada)
            explicacion_ia = generar_explicacion_simplex(pasos_serializables)
            if not explicacion_ia:
                logger.warning(
                    "No se pudo generar explicación (API) para problema ID: %s",
                    problema.id,
                )
                explicacion_ia = "No se pudo generar la explicación automática."

            problema.pasos = pasos_serializables
            problema.tabla_inicial = json.dumps(pasos[0]["tabla"]) if pasos else None
            problema.tabla_final = json.dumps(resultado["tabla_final"])

            solucion_data = {
                "variables": resultado["solucion"],
                "valor_optimo": resultado["valor_optimo"],
                "optimalidad": resultado.get("optimalidad", "óptimo"),
                "iteraciones": resultado["iteraciones"],
                "variables_basicas_finales": resultado.get("variables_basicas", []),
            }
            problema.solucion = json.dumps(solucion_data)
            problema.grafico_base64 = resultado.get("grafico")
            problema.variables_holgura = (
                len(resultado["solucion"]) - problema.variables_decision
            )
            problema.iteraciones_realizadas = resultado["iteraciones"]

            # Manejo de estados
            if resultado.get("optimalidad") == "no acotado":
                problema.estado = "no_acotado"
            elif resultado.get("warning"):
                problema.estado = "advertencia"
                problema.advertencias = (problema.advertencias or []) + [
                    resultado["warning"]
                ]
            else:
                problema.estado = "optimo"

            problema.explicacion_chatgpt = explicacion_ia
            problema.save()

        except ValueError as e:
            logger.error("Error en API al resolver problema Simplex: %s", str(e))
            problema.estado = "error"
            problema.save()
            raise
        except Exception as e:
            logger.exception("Error inesperado en API al procesar problema Simplex")
            problema.estado = "error"
            problema.save()
            raise


class SimplexDetailAPIView(RetrieveUpdateDestroyAPIView):
    serializer_class = SimplexSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ProblemaSimplex.objects.filter(usuario=self.request.user)



from io import BytesIO
import base64
import matplotlib.pyplot as plt

def generar_grafico_base64(problema):
    fig, ax = plt.subplots()

    # Este es un ejemplo, reemplaza por lógica real si aplica
    ax.set_title("Gráfica del problema")
    ax.set_xlabel("X")
    ax.set_ylabel("Y")
    ax.plot([0, 1, 2], [0, 2, 1], label="Restricción 1")  # Gráfica de ejemplo
    ax.legend()

    buffer = BytesIO()
    plt.savefig(buffer, format='png', bbox_inches='tight')
    plt.close(fig)
    buffer.seek(0)

    imagen_base64 = base64.b64encode(buffer.getvalue()).decode('utf-8')
    return f'data:image/png;base64,{imagen_base64}'


def generar_pdf_problema(request, problema_id):
    problema = get_object_or_404(ProblemaSimplex, id=problema_id)

    grafico_base64 = generar_grafico_base64(problema)

    # Ejemplo de estructura para 'pasos'
    pasos = [
        {
            'titulo': 'Tabla inicial',
            'explicacion': 'Esta es la tabla inicial del problema.',
            'variables_basicas': ['x1', 'x2'],
            'tabla': problema.tabla_inicial,  # debe ser lista de listas, ej: [[1, 2], [3, 4]]
        },
        {
            'titulo': 'Tabla final',
            'explicacion': 'Resultado final después de iteraciones.',
            'variables_basicas': ['x1', 'x2'],
            'tabla': problema.tabla_final,
        }
    ]

    contexto = {
        'objetivo': problema.objetivo,
        'tipo_optimizacion': problema.get_tipo_optimizacion_display(),
        'restricciones': problema.restricciones.split(';'),
        'explicacion_chatgpt': problema.explicacion_chatgpt or "No hay explicación disponible",
        'grafico_base64': grafico_base64,
        'solucion': problema.solucion,
        'iteraciones': problema.iteraciones_realizadas,
        'estado': problema.get_estado_display(),
        'fecha_creacion': problema.creado,
        'pasos': pasos,  # ¡Asegúrate de pasar esta variable!
    }

    html_string = render_to_string('metodo/pdf_problema.html', contexto)
    pdf = HTML(string=html_string).write_pdf()

    response = HttpResponse(pdf, content_type='application/pdf')
    response['Content-Disposition'] = f'filename="problema_{problema_id}.pdf"'
    return response
