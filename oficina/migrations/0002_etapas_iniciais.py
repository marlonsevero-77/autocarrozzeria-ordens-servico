"""Cadastra as cinco etapas reais da AutoCarrozzeria Di Girolamo."""

from django.db import migrations

ETAPAS = [
    (1, "Desmontagem", "Giuseppe"),
    (2, "Alinhamento do reparo", "Fabio"),
    (3, "Fundo e massa", "Filippo e Riccardo"),
    (4, "Mascaramento e pintura", "Davide"),
    (5, "Revisão e montagem", "Giuseppe"),
]


def criar_etapas(apps, schema_editor):
    Etapa = apps.get_model("oficina", "Etapa")
    for sequencia, nome, responsavel in ETAPAS:
        Etapa.objects.get_or_create(
            sequencia=sequencia, defaults={"nome": nome, "responsavel": responsavel}
        )


def remover_etapas(apps, schema_editor):
    Etapa = apps.get_model("oficina", "Etapa")
    Etapa.objects.filter(sequencia__in=[s for s, _, _ in ETAPAS]).delete()


class Migration(migrations.Migration):
    dependencies = [("oficina", "0001_modelo_inicial")]
    operations = [migrations.RunPython(criar_etapas, remover_etapas)]
