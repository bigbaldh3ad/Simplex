from django.db import migrations, models
import django.contrib.postgres.fields
from django.contrib.postgres.operations import CreateExtension


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ("auth", "0012_alter_user_first_name_max_length"),
    ]

    operations = [
        CreateExtension(name="postgis"),
        migrations.CreateModel(
            name="Simplex",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "coef_objetivo",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.FloatField(),
                        help_text="Coeficientes de la función objetivo.",
                        size=None,
                    ),
                ),
                (
                    "matriz_restricciones",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=django.contrib.postgres.fields.ArrayField(
                            base_field=models.FloatField(), size=None
                        ),
                        help_text="Matriz de restricciones.",
                    ),
                ),
                (
                    "vector_b",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.FloatField(),
                        help_text="Lado derecho de las restricciones.",
                    ),
                ),
                (
                    "desigualdades",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.CharField(max_length=2),
                        help_text="Lista de desigualdades ('<=', '>=', '=').",
                    ),
                ),
                (
                    "tipo_problema",
                    models.CharField(
                        choices=[("max", "Maximizar"), ("min", "Minimizar")],
                        default="max",
                        max_length=3,
                    ),
                ),
                ("resultado", models.JSONField(blank=True, null=True)),
                ("creado", models.DateTimeField(auto_now_add=True)),
                ("valor_optimo", models.FloatField(blank=True, null=True)),
                (
                    "solucion",
                    django.contrib.postgres.fields.ArrayField(
                        base_field=models.FloatField(),
                        blank=True,
                        help_text="Solución óptima encontrada.",
                        null=True,
                        size=None,
                    ),
                ),
                (
                    "usuario",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE, to="auth.user"
                    ),
                ),
            ],
            options={
                "verbose_name": "Cálculo Simplex",
                "verbose_name_plural": "Cálculos Simplex",
                "ordering": ["-creado"],
            },
        ),
    ]
