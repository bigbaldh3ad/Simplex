from django import forms
from django.core.validators import MinValueValidator, MaxValueValidator
from .models import ProblemaSimplex
import re


class SimplexForm(forms.ModelForm):
    class Meta:
        model = ProblemaSimplex
        fields = [
            "objetivo",
            "tipo_optimizacion",
            "restricciones",
            "variables_decision",
            "tolerancia",
            "max_iteraciones",
        ]
        widgets = {
            "objetivo": forms.TextInput(
                attrs={
                    "placeholder": "Ej: 3x1 + 2x2 + 5x3",
                    "class": "function-input",
                    "pattern": r"^[0-9xX\+\-\*\/\.\s]+$",  # Corrección aquí: añadido 'r' para raw string
                    "title": "Use solo números, variables (x1, x2), y operadores básicos",
                }
            ),
            "tipo_optimizacion": forms.Select(attrs={"class": "form-control"}),
            "restricciones": forms.Textarea(
                attrs={
                    "placeholder": "Ej: 2x1 + x2 <= 20; x1 + 3x2 <= 30",
                    "rows": 3,
                    "class": "form-control",
                    "title": "Separe restricciones con punto y coma. Use <=, >= o =",
                }
            ),
            "variables_decision": forms.NumberInput(
                attrs={
                    "min": "1",
                    "max": "10",
                    "value": "2",
                    "class": "form-control",
                    "title": "Entre 1 y 10 variables",
                }
            ),
            "tolerancia": forms.NumberInput(
                attrs={
                    "step": "any",
                    "min": "0.000000001",
                    "value": "0.001",
                    "class": "form-control",
                    "title": "Valor mínimo: 0.000000001",
                }
            ),
            "max_iteraciones": forms.NumberInput(
                attrs={
                    "min": "10",
                    "max": "1000",
                    "value": "100",
                    "class": "form-control",
                    "title": "Entre 10 y 1000 iteraciones",
                }
            ),
        }
        help_texts = {
            "objetivo": "Ingrese la función objetivo usando variables como x1, x2, etc. Ej: 3x1 + 2x2 - 4x3",
            "restricciones": "Separe cada restricción con punto y coma (;). Use <=, >= o =. Ej: 2x1 + x2 <= 20; x1 - 3x2 >= 10",
            "variables_decision": "Número de variables en el problema (entre 1 y 10)",
            "tolerancia": "Valor mínimo para considerar un número como cero (≥ 1e-9)",
            "max_iteraciones": "Número máximo de iteraciones permitidas (entre 10 y 1000)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Validadores adicionales para coincidir con el modelo
        self.fields["variables_decision"].validators.extend(
            [MinValueValidator(1), MaxValueValidator(10)]
        )
        self.fields["tolerancia"].validators.append(MinValueValidator(1e-9))
        self.fields["max_iteraciones"].validators.extend(
            [MinValueValidator(10), MaxValueValidator(1000)]
        )

    def clean_objetivo(self):
        objetivo = self.cleaned_data["objetivo"].strip()

        if not objetivo:
            raise forms.ValidationError("La función objetivo no puede estar vacía")

        # Validación mejorada de la función objetivo
        pattern = r"^([+-]?\d*\.?\d*[xX]\d+\s*([+-]\s*\d*\.?\d*[xX]\d+)*\s*([+-]\s*\d*\.?\d+)*\s*)$"
        if not re.fullmatch(pattern, objetivo.replace(" ", "")):
            raise forms.ValidationError(
                "Formato incorrecto. Use términos como: 3x1, -2.5x2, +x3, 10"
            )

        # Verificar que las variables sean consecutivas (x1, x2, ...)
        variables = sorted(int(m[1:]) for m in re.findall(r"[xX]\d+", objetivo))
        if variables and variables != list(range(1, max(variables) + 1)):
            raise forms.ValidationError(
                "Las variables deben ser consecutivas (x1, x2, ...) sin saltos"
            )

        return objetivo

    def clean_restricciones(self):
        restricciones = self.cleaned_data["restricciones"].strip()

        if not restricciones:
            raise forms.ValidationError("Debe ingresar al menos una restricción")

        # Validación mejorada de restricciones
        for i, restr in enumerate(filter(None, restricciones.split(";"))):
            restr = restr.strip()
            if not restr:
                continue

            # Verificar estructura básica
            if not re.match(r"^(.+)(<=|>=|=)(.+)$", restr):
                raise forms.ValidationError(
                    f"Restricción {i+1} mal formada. Use formato: [expresión] [<=|>=|=] [valor]"
                )

            # Verificar caracteres válidos
            if not re.match(r"^[\dxX\+\-\.\*/\s<=>]+$", restr):
                raise forms.ValidationError(
                    f"Restricción {i+1} contiene caracteres no permitidos"
                )

        return restricciones

    def clean(self):
        cleaned_data = super().clean()
        # Validación cruzada entre variables_decision y las usadas en las expresiones
        if "objetivo" in cleaned_data and "variables_decision" in cleaned_data:
            objetivo = cleaned_data["objetivo"]
            num_vars = cleaned_data["variables_decision"]

            # Encontrar la variable más alta usada
            variables = [int(m[1:]) for m in re.findall(r"[xX]\d+", objetivo)]
            max_var = max(variables) if variables else 0

            if max_var > num_vars:
                raise forms.ValidationError(
                    f"Usó x{max_var} pero definió solo {num_vars} variables. "
                    f"Ajuste el número de variables o las expresiones."
                )

        return cleaned_data
