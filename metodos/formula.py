import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
import base64
import re
from sympy import symbols, sympify, SympifyError
from typing import List, Tuple, Dict, Optional
import warnings

# Configuración de warnings
warnings.filterwarnings("ignore", category=RuntimeWarning)


class SimplexSolver:
    """Clase optimizada para resolver problemas de programación lineal usando el método Simplex."""

    def __init__(
        self, tolerancia: float = 1e-6, max_iter: int = 1000, verbose: bool = False
    ):
        self.tolerancia = tolerancia
        self.max_iter = max_iter
        self.verbose = verbose

    def resolver_problema(self, simplex_problem) -> Dict:
        """
        Resuelve un problema de programación lineal.

        Args:
            simplex_problem: Instancia del modelo ProblemaSimplex

        Returns:
            dict: Resultados con solución, valor óptimo, iteraciones y gráfico
        """
        try:
            # Validación inicial
            if not simplex_problem.objetivo or not simplex_problem.restricciones:
                raise ValueError("Objetivo y restricciones no pueden estar vacíos")

            # 1. Parsear el problema
            c, A, b, desigualdades = self._parsear_problema(
                simplex_problem.objetivo,
                simplex_problem.restricciones,
                simplex_problem.variables_decision,
            )

            # 2. Convertir a arrays numpy optimizados
            c = np.array(c, dtype=np.float64)
            A = np.array(A, dtype=np.float64)
            b = np.array(b, dtype=np.float64)

            # 3. Validar dimensiones
            self._validar_dimensiones(c, A, b)

            # 4. Ejecutar Simplex
            resultado = self._ejecutar_simplex(
                c, A, b, desigualdades, simplex_problem.tipo_optimizacion
            )

            # 5. Generar gráfico si es 2D
            if len(c) == 2:
                resultado["grafico"] = self._generar_grafico(
                    c,
                    A,
                    b,
                    desigualdades,
                    simplex_problem.tipo_optimizacion,
                    resultado["solucion"],
                    resultado["valor_optimo"],
                )
            else:
                resultado["grafico"] = None

            return resultado

        except Exception as e:
            return {
                "error": str(e),
                "solucion": None,
                "valor_optimo": None,
                "iteraciones": 0,
                "pasos": [],
                "tabla_final": None,
                "grafico": None,
            }

    def _preprocesar_expresion(self, expr: str, num_vars: int) -> str:
        """Versión corregida del preprocesamiento de expresiones"""
        try:
            # Paso 1: Eliminar espacios y convertir potencias
            expr_limpia = expr.replace(" ", "").replace("^", "**")

            # Paso 2: Manejar coeficientes implícitos (como 'x1' -> '1*x1')
            expr_limpia = re.sub(
                r"(^|\+|-)(x\d+)", lambda m: f"{m.group(1)}1*{m.group(2)}", expr_limpia
            )

            # Paso 3: Agregar multiplicación entre coeficientes y variables
            for i in range(
                num_vars, 0, -1
            ):  # Procesar de mayor a menor (x11 antes que x1)
                var = f"x{i}"
                # Reemplazar patrones como 3x1 -> 3*x1
                expr_limpia = re.sub(
                    r"(\d)({})(\D|$)".format(var), r"\1*\2\3", expr_limpia
                )
                # Manejar variables solas al inicio [+-]x1 -> [+-]1*x1
                expr_limpia = re.sub(
                    r"(^|[+\-*/])({})(\D|$)".format(var), r"\g<1>1*\2\3", expr_limpia
                )

            # Paso 4: Normalizar formato de variables (X1 -> x1)
            expr_limpia = expr_limpia.lower()

            if self.verbose:
                print(f"Expresión preprocesada: {expr_limpia}")

            return expr_limpia
        except Exception as e:
            raise ValueError(f"Error al preprocesar expresión: {str(e)}")

    def _parsear_problema(
        self, objetivo: str, restricciones: str, num_vars: int
    ) -> Tuple:
        """Parsea el problema en texto a matrices numéricas con validación robusta."""
        if num_vars < 1:
            raise ValueError("Debe haber al menos 1 variable de decisión")
        if num_vars > 20:
            raise ValueError("El número máximo de variables es 20")

        try:
            # Preprocesar función objetivo
            objetivo_limpio = self._preprocesar_expresion(objetivo, num_vars)

            # Crear variables simbólicas
            vars = symbols([f"x{i}" for i in range(1, num_vars + 1)])

            # Parsear función objetivo
            try:
                expr_obj = sympify(
                    objetivo_limpio,
                    locals={f"x{i}": vars[i - 1] for i in range(1, num_vars + 1)},
                )
            except SympifyError:
                raise ValueError(
                    "Formato de función objetivo inválido. Use formato como '3*x1 + 2*x2' o '3x1 + 2x2'"
                )

            c = [
                float(expr_obj.coeff(vars[i])) if vars[i] in expr_obj.args else 0.0
                for i in range(num_vars)
            ]

            # Parsear restricciones
            A, b, desigualdades = [], [], []
            restr_list = [r.strip() for r in restricciones.split(";") if r.strip()]

            if not restr_list:
                raise ValueError("Debe proporcionar al menos una restricción")

            for restr in restr_list:
                try:
                    # Normalizar la restricción
                    restr_limpia = self._preprocesar_expresion(restr, num_vars)

                    # Dividir en LHS y RHS
                    if "<=" in restr_limpia:
                        lhs, rhs = restr_limpia.split("<=", 1)
                        desigualdad = "<="
                    elif ">=" in restr_limpia:
                        lhs, rhs = restr_limpia.split(">=", 1)
                        desigualdad = ">="
                    elif "=" in restr_limpia:
                        lhs, rhs = restr_limpia.split("=", 1)
                        desigualdad = "="
                    else:
                        raise ValueError(f"Restricción mal formada: {restr}")

                    expr_restr = sympify(
                        lhs,
                        locals={f"x{i}": vars[i - 1] for i in range(1, num_vars + 1)},
                    )

                    fila_A = [
                        (
                            float(expr_restr.coeff(vars[i]))
                            if vars[i] in expr_restr.args
                            else 0.0
                        )
                        for i in range(num_vars)
                    ]

                    A.append(fila_A)
                    b.append(float(rhs.strip()))
                    desigualdades.append(desigualdad)

                except Exception as e:
                    raise ValueError(f"Error en restricción '{restr}': {str(e)}")

            return c, A, b, desigualdades

        except Exception as e:
            raise ValueError(f"Error al parsear el problema: {str(e)}")

    def _validar_dimensiones(self, c: np.ndarray, A: np.ndarray, b: np.ndarray):
        """Valida las dimensiones de las matrices de entrada."""
        if A.shape[0] != len(b):
            raise ValueError(
                "Número de restricciones no coincide con términos independientes"
            )
        if A.shape[1] != len(c):
            raise ValueError(
                "Número de variables en restricciones no coincide con función objetivo"
            )

    def _ejecutar_simplex(
        self,
        c: np.ndarray,
        A: np.ndarray,
        b: np.ndarray,
        desigualdades: List[str],
        tipo_optimizacion: str,
    ) -> Dict:
        """Implementación optimizada del algoritmo Simplex."""
        # Convertir a problema de maximización
        if tipo_optimizacion == "minimizar":
            c = -c.copy()

        num_vars = len(c)
        num_restr = len(b)

        # 1. Inicializar tabla
        tabla, variables_basicas = self._inicializar_tabla(c, A, b, desigualdades)
        pasos = [
            {
                "titulo": "Tabla inicial",
                "tabla": tabla.copy().tolist(),
                "variables_basicas": variables_basicas.copy(),
                "explicacion": "Tabla inicial con variables de holgura/exceso/artificiales",
            }
        ]

        # 2. Fase I (si hay restricciones >= o =)
        if any(d in [">=", "="] for d in desigualdades):
            if self.verbose:
                print("\nIniciando Fase I...")
            tabla, variables_basicas, pasos_faseI = self._fase_I(
                tabla, variables_basicas, num_vars
            )
            pasos.extend(pasos_faseI)

            # Verificar factibilidad
            if not np.allclose(tabla[-1, -1], 0, atol=self.tolerancia):
                raise ValueError("El problema no tiene solución factible")

        # 3. Fase II (optimización)
        if self.verbose:
            print("\nIniciando Fase II...")
        iteracion = 0
        while iteracion < self.max_iter:
            iteracion += 1

            # Verificar optimalidad
            if self._es_optimo(tabla):
                if self.verbose:
                    print(f"Solución óptima encontrada en {iteracion} iteraciones")
                break

            # Seleccionar pivote
            col_pivote = self._seleccionar_columna_pivote(tabla)
            fila_pivote = self._seleccionar_fila_pivote(tabla, col_pivote)

            if fila_pivote == -1:
                raise ValueError("El problema es no acotado")

            # Actualizar variables básicas
            variables_basicas[fila_pivote] = col_pivote

            # Operación de pivote
            self._pivotear(tabla, fila_pivote, col_pivote)

            if self.verbose:
                print(
                    f"Iteración {iteracion}: Pivote en fila {fila_pivote}, columna {col_pivote}"
                )

            pasos.append(
                {
                    "titulo": f"Iteración {iteracion}",
                    "tabla": tabla.copy().tolist(),
                    "variables_basicas": variables_basicas.copy(),
                    "pivote": {"fila": fila_pivote, "columna": col_pivote},
                    "explicacion": f"Pivote en fila {fila_pivote}, columna {col_pivote}",
                }
            )

        # Verificar convergencia
        if iteracion >= self.max_iter:
            warnings.warn(
                "Máximo número de iteraciones alcanzado. Solución puede no ser óptima."
            )

        # Extraer resultados
        solucion = self._extraer_solucion(tabla, variables_basicas, num_vars)
        valor_optimo = tabla[-1, -1]

        if tipo_optimizacion == "minimizar":
            valor_optimo = -valor_optimo

        return {
            "solucion": solucion,
            "valor_optimo": float(valor_optimo),
            "iteraciones": iteracion,
            "pasos": pasos,
            "tabla_final": tabla.tolist(),
        }

    def _inicializar_tabla(
        self, c: np.ndarray, A: np.ndarray, b: np.ndarray, desigualdades: List[str]
    ) -> Tuple[np.ndarray, List[int]]:
        """Inicializa la tabla Simplex y lleva registro de variables básicas."""
        num_vars = len(c)
        num_restr = len(b)

        # Contar variables de holgura/exceso/artificiales
        num_holgura = sum(1 for d in desigualdades if d in ["<=", ">="])
        num_artificiales = sum(1 for d in desigualdades if d in [">=", "="])

        # Dimensiones de la tabla
        n_cols = num_vars + num_holgura + num_artificiales + 1  # +1 para RHS
        tabla = np.zeros((num_restr + 1, n_cols))
        variables_basicas = []

        # Llenar coeficientes de restricciones
        idx_holgura = 0
        idx_artificial = 0

        for i in range(num_restr):
            tabla[i, :num_vars] = A[i]

            if desigualdades[i] == "<=":
                # Variable de holgura
                tabla[i, num_vars + idx_holgura] = 1
                variables_basicas.append(num_vars + idx_holgura)
                idx_holgura += 1
            elif desigualdades[i] == ">=":
                # Variable de exceso (-1) y artificial (+1)
                tabla[i, num_vars + idx_holgura] = -1
                tabla[i, num_vars + num_holgura + idx_artificial] = 1
                variables_basicas.append(num_vars + num_holgura + idx_artificial)
                idx_holgura += 1
                idx_artificial += 1
            elif desigualdades[i] == "=":
                # Variable artificial
                tabla[i, num_vars + num_holgura + idx_artificial] = 1
                variables_basicas.append(num_vars + num_holgura + idx_artificial)
                idx_artificial += 1

            tabla[i, -1] = b[i]

        # Función objetivo original (para Fase II)
        tabla[-1, :num_vars] = -c  # Negativo porque maximizamos

        # Para Fase I (si hay artificiales)
        if num_artificiales > 0:
            # Crear función objetivo de Fase I (minimizar suma de variables artificiales)
            tabla_aux = tabla.copy()
            tabla_aux[-1, :] = 0
            for i in range(num_restr):
                if desigualdades[i] in [">=", "="]:
                    # Restar filas con variables artificiales para obtener 0 en columna
                    tabla_aux[-1] -= tabla_aux[i]
            return tabla_aux, variables_basicas
        else:
            return tabla, variables_basicas

    def _fase_I(
        self, tabla: np.ndarray, variables_basicas: List[int], num_vars: int
    ) -> Tuple[np.ndarray, List[int], List[Dict]]:
        """Implementación de la Fase I para problemas con restricciones >= o =."""
        pasos = []
        iteracion = 0

        while iteracion < self.max_iter:
            iteracion += 1

            if self._es_optimo_faseI(tabla):
                if self.verbose:
                    print(f"Fase I completada en {iteracion} iteraciones")
                break

            col_pivote = self._seleccionar_columna_pivote(tabla)
            fila_pivote = self._seleccionar_fila_pivote(tabla, col_pivote)

            if fila_pivote == -1:
                raise ValueError("Problema no factible (Fase I no acotada)")

            variables_basicas[fila_pivote] = col_pivote
            self._pivotear(tabla, fila_pivote, col_pivote)

            if self.verbose:
                print(
                    f"Fase I - Iteración {iteracion}: Pivote en fila {fila_pivote}, columna {col_pivote}"
                )

            pasos.append(
                {
                    "titulo": f"Fase I - Iteración {iteracion}",
                    "tabla": tabla.copy().tolist(),
                    "variables_basicas": variables_basicas.copy(),
                    "pivote": {"fila": fila_pivote, "columna": col_pivote},
                    "explicacion": "Pivote en Fase I para eliminar variables artificiales",
                }
            )

        # Eliminar columnas de variables artificiales para Fase II
        mask = [
            i
            for i in range(tabla.shape[1])
            if i not in variables_basicas
            or i < num_vars
            or tabla[-1, i] >= -self.tolerancia
        ]
        tabla = tabla[:, mask]

        # Actualizar variables básicas
        variables_basicas = [i for i in variables_basicas if i in mask]

        return tabla, variables_basicas, pasos

    def _es_optimo(self, tabla: np.ndarray) -> bool:
        """Determina si la solución actual es óptima."""
        return np.all(tabla[-1, :-1] >= -self.tolerancia)

    def _es_optimo_faseI(self, tabla: np.ndarray) -> bool:
        """Determina si la Fase I ha terminado."""
        return np.all(tabla[-1, :-1] >= -self.tolerancia)

    def _seleccionar_columna_pivote(self, tabla: np.ndarray) -> int:
        """Selecciona la variable entrante usando la regla de Bland para evitar ciclado."""
        # Regla de Bland: selecciona la primera variable con coeficiente negativo
        for j in range(tabla.shape[1] - 1):
            if tabla[-1, j] < -self.tolerancia:
                return j
        return -1

    def _seleccionar_fila_pivote(self, tabla: np.ndarray, col_pivote: int) -> int:
        """Selecciona la variable saliente usando la regla de la razón mínima."""
        ratios = []
        for i in range(tabla.shape[0] - 1):
            if tabla[i, col_pivote] > self.tolerancia:
                ratio = tabla[i, -1] / tabla[i, col_pivote]
                ratios.append(ratio if ratio >= 0 else np.inf)
            else:
                ratios.append(np.inf)

        if all(np.isinf(r) for r in ratios):
            return -1

        # Regla de Bland: selecciona la fila con índice más pequeño en caso de empate
        min_ratio = min(ratios)
        candidatos = [
            i for i, r in enumerate(ratios) if abs(r - min_ratio) < self.tolerancia
        ]
        return min(candidatos)

    def _pivotear(self, tabla: np.ndarray, fila_pivote: int, col_pivote: int):
        """Operación de pivote optimizada con operaciones vectorizadas."""
        pivote_val = tabla[fila_pivote, col_pivote]
        tabla[fila_pivote] /= pivote_val

        mask = np.ones(tabla.shape[0], dtype=bool)
        mask[fila_pivote] = False
        factores = tabla[mask, col_pivote, np.newaxis]

        tabla[mask] -= factores * tabla[fila_pivote]

    def _extraer_solucion(
        self, tabla: np.ndarray, variables_basicas: List[int], num_vars: int
    ) -> List[float]:
        """Extrae la solución de la tabla final."""
        solucion = [0.0] * num_vars

        for i, j in enumerate(variables_basicas):
            if j < num_vars:
                solucion[j] = tabla[i, -1]

        return solucion

    def _generar_grafico(
        self,
        c: np.ndarray,
        A: np.ndarray,
        b: np.ndarray,
        desigualdades: List[str],
        tipo_optimizacion: str,
        solucion: List[float],
        valor_optimo: float,
    ) -> str:
        """Genera un gráfico de la región factible para problemas 2D."""
        plt.figure(figsize=(10, 8))
        plt.grid(True, linestyle="--", alpha=0.7)

        # Configurar ejes
        x_vals = np.linspace(0, max(b) * 1.5, 500)
        plt.xlim(0, max(b) * 1.5)
        plt.ylim(0, max(b) * 1.5)
        plt.xlabel("$x_1$", fontsize=12)
        plt.ylabel("$x_2$", fontsize=12)

        # Graficar restricciones
        for i, (a1, a2) in enumerate(A):
            bi = b[i]
            des = desigualdades[i]

            if a2 != 0:
                y = (bi - a1 * x_vals) / a2
                label = f"{a1:.2f}x₁ + {a2:.2f}x₂ {des} {bi:.2f}"
                plt.plot(x_vals, y, label=label, linewidth=2)

                # Sombrear región factible
                if des == "<=":
                    plt.fill_between(x_vals, 0, y, alpha=0.1)
                elif des == ">=":
                    plt.fill_between(x_vals, y, plt.ylim()[1], alpha=0.1)
            else:
                # Restricción vertical (x1 = constante)
                x_val = bi / a1
                plt.axvline(x=x_val, label=f"{a1:.2f}x₁ {des} {bi:.2f}", linewidth=2)

                if des == "<=":
                    plt.fill_betweenx([0, plt.ylim()[1]], 0, x_val, alpha=0.1)
                elif des == ">=":
                    plt.fill_betweenx(
                        [0, plt.ylim()[1]], x_val, plt.xlim()[1], alpha=0.1
                    )

        # Graficar solución óptima
        if solucion and len(solucion) == 2:
            x_opt, y_opt = solucion
            plt.plot(
                x_opt,
                y_opt,
                "ro",
                markersize=10,
                label=f"Solución óptima: ({x_opt:.2f}, {y_opt:.2f})",
            )

        # Graficar función objetivo
        if len(c) == 2 and c[1] != 0:
            z = valor_optimo
            y_obj = (z - c[0] * x_vals) / c[1]
            plt.plot(
                x_vals,
                y_obj,
                "k--",
                linewidth=2,
                label=f"Función Objetivo (Z = {z:.2f})",
            )

        plt.legend(loc="upper right", bbox_to_anchor=(1.35, 1))
        plt.title(
            f"Región Factible - {'Maximización' if tipo_optimizacion == 'maximizar' else 'Minimización'}"
        )

        # Convertir a base64
        buffer = BytesIO()
        plt.savefig(buffer, format="png", bbox_inches="tight", dpi=100)
        buffer.seek(0)
        img_base64 = base64.b64encode(buffer.read()).decode("utf-8")
        plt.close()

        return img_base64


# Función de conveniencia para mantener compatibilidad
def resolver_simplex(simplex_problem):
    solver = SimplexSolver(
        tolerancia=float(simplex_problem.tolerancia),
        max_iter=int(simplex_problem.max_iteraciones),
        verbose=False,
    )
    resultado = solver.resolver_problema(simplex_problem)

    # Formatear los pasos correctamente
    if "pasos" in resultado:
        resultado["pasos"] = [
            {
                "titulo": paso.get("titulo", f"Iteración {idx}"),
                "tabla": (
                    paso["tabla"].tolist()
                    if hasattr(paso["tabla"], "tolist")
                    else paso["tabla"]
                ),
                "explicacion": paso.get("explicacion", ""),
                "variables_basicas": paso.get("variables_basicas", []),
            }
            for idx, paso in enumerate(resultado["pasos"])
        ]

    return resultado
