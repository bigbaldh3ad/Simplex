from django.db import models
from django.contrib.auth.models import User
from django.core.validators import (
    MinValueValidator,
    MaxValueValidator,
)  # Importación añadida


class ProblemaSimplex(models.Model):
    TIPO_OPTIMIZACION = [
        ("maximizar", "Maximizar"),
        ("minimizar", "Minimizar"),
    ]

    ESTADO_CHOICES = [
        ("optimo", "Óptimo"),
        ("advertencia", "Advertencia"),
        ("no_acotado", "No acotado"),
        ("infactible", "Infactible"),
        ("error", "Error"),
        ("procesando", "Procesando"),
    ]

    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    objetivo = models.CharField(
        max_length=255, help_text="Función objetivo, ej: 3x1 + 2x2 + 5x3"
    )
    tipo_optimizacion = models.CharField(
        max_length=10,
        choices=TIPO_OPTIMIZACION,
        default="maximizar",
        help_text="Seleccione si desea maximizar o minimizar la función objetivo",
    )
    restricciones = models.TextField(
        help_text="Ingrese las restricciones separadas por punto y coma. Ej: 2x1 + x2 <= 20; x1 + 3x2 <= 30"
    )
    variables_decision = models.PositiveIntegerField(
        default=2,
        help_text="Número de variables de decisión (entre 1 y 10)",
        validators=[
            MinValueValidator(1),
            MaxValueValidator(10),
        ],  # Validadores correctamente implementados
    )
    variables_holgura = models.PositiveIntegerField(
        default=0,
        help_text="Número de variables de holgura (se calcula automáticamente)",
    )
    variables_artificiales = models.PositiveIntegerField(
        default=0,
        help_text="Número de variables artificiales usadas (se calcula automáticamente)",
    )
    tolerancia = models.FloatField(
        default=0.001,
        help_text="Tolerancia para considerar cero",
        validators=[MinValueValidator(1e-10)],
    )
    max_iteraciones = models.IntegerField(
        default=100,
        help_text="Número máximo de iteraciones",
        validators=[MinValueValidator(10), MaxValueValidator(1000)],
    )
    tabla_inicial = models.JSONField(
        blank=True, null=True, help_text="Tabla inicial del simplex"
    )
    tabla_final = models.JSONField(
        blank=True, null=True, help_text="Tabla final del simplex"
    )
    solucion = models.JSONField(
        blank=True, null=True, help_text="Solución encontrada con metadatos"
    )
    grafico_base64 = models.TextField(
        blank=True,
        null=True,
        help_text="Gráfico de la región factible (para problemas 2D)",
    )
    iteraciones_realizadas = models.PositiveIntegerField(
        default=0,
        help_text="Número de iteraciones realizadas para encontrar la solución",
    )
    estado = models.CharField(
        max_length=20,
        choices=ESTADO_CHOICES,
        default="procesando",
        help_text="Estado actual del problema",
    )
    advertencias = models.JSONField(
        blank=True,
        null=True,
        help_text="Advertencias generadas durante el proceso de solución",
    )
    tiempo_resolucion = models.FloatField(
        blank=True, null=True, help_text="Tiempo de resolución en segundos"
    )
    pasos = models.JSONField(
        blank=True,
        null=True,
        help_text="Todos los pasos intermedios del método Simplex",
    )
    explicacion_chatgpt = models.TextField(
        blank=True,
        null=True,
        help_text="Explicación generada automáticamente por ChatGPT del procedimiento simplex",
    )
    creado = models.DateTimeField(auto_now_add=True)
    actualizado = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"{self.tipo_optimizacion.capitalize()} {self.objetivo} - {self.get_estado_display()}"

    class Meta:
        verbose_name = "Problema de Programación Lineal"
        verbose_name_plural = "Problemas de Programación Lineal"
        ordering = ["-creado"]
        indexes = [
            models.Index(fields=["usuario", "creado"]),
            models.Index(fields=["estado"]),
        ]

    def save(self, *args, **kwargs):
        """Método save personalizado para validaciones adicionales"""
        # Validación de restricciones básica
        if not self.restricciones or ";" not in self.restricciones:
            raise ValueError(
                "Debe proporcionar al menos una restricción válida separada por ';'"
            )

        super().save(*args, **kwargs)
