from rest_framework import serializers
from .models import ProblemaSimplex


class SimplexSerializer(serializers.ModelSerializer):
    class Meta:
        model = ProblemaSimplex
        fields = "__all__"
        read_only_fields = [
            "variables_holgura",
            "tabla_inicial",
            "tabla_final",
            "solucion",
            "grafico_base64",
            "creado",
        ]

    def to_representation(self, instance):
        """Transforma los datos para la respuesta API"""
        representation = super().to_representation(instance)

        # Formatea campos complejos si existen
        if instance.tabla_inicial:
            representation["tabla_inicial"] = instance.tabla_inicial
        if instance.tabla_final:
            representation["tabla_final"] = instance.tabla_final

        return representation
