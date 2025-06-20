from django.urls import path
from .views import generar_pdf_problema
from django.views.generic import TemplateView
from .views import (
    SimplexListView,
    SimplexCreateView,
    SimplexDetailView,
    SimplexListCreateView,
    SimplexDetailView as SimplexAPIDetailView,  # Alias para evitar conflicto de nombres
)

urlpatterns = [
    # Vista de inicio
    path("", TemplateView.as_view(template_name="metodo/inicio.html"), name="inicio"),
    # Vistas normales (HTML)
    path("simplex/", SimplexListView.as_view(), name="list_simplex"),
    path("simplex/nuevo/", SimplexCreateView.as_view(), name="add_simplex"),
    # Vista detallada (HTML) - Asegúrate de que esta ruta esté antes que las API para prioridad
    path(
        "simplex/<int:pk>/",
        SimplexDetailView.as_view(template_name="metodo/detail_simplex.html"),
        name="detail_simplex",
    ),
    # Vistas API (JSON)
    path("api/simplex/", SimplexListCreateView.as_view(), name="api_simplex_list"),
    path(
        "api/simplex/<int:pk>/",
        SimplexAPIDetailView.as_view(),
        name="api_simplex_detail",
    ),
    
    path('problema/<int:problema_id>/pdf/', generar_pdf_problema, name='generar_pdf_problema'),
]
