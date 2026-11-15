"""Carrega dados fictícios para demonstração e testes de usabilidade.

Uso: python manage.py carregar_dados_demo
Nenhum dado real de cliente é usado.
"""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone

from oficina.models import Cliente, Etapa, HistoricoEtapa, OrdemServico, Veiculo

CARROS = [
    # placa, marca, modelo, cor, cliente, etapa, dias até o prazo
    ("CD456EF", "Lancia", "Ypsilon", "Cinza", "Giulia Conti", 1, 11),
    ("GH012IJ", "Alfa Romeo", "Giulietta", "Vermelha", "Sara Greco", 2, 8),
    ("KL678MN", "Fiat", "Punto", "Azul", "Elena Russo", 3, 2),
    ("AB123CD", "Fiat", "Panda", "Branca", "Marco Bianchi", 4, 7),
    ("EF789GH", "Fiat", "500", "Preta", "Luca Ferri", 4, -1),
]


class Command(BaseCommand):
    help = "Cria dados fictícios de demonstração (somente se ainda não houver ordens)."

    def add_arguments(self, parser):
        parser.add_argument("--usuario", default="riccardo.demo", help="Usuário que aparece como autor dos registros.")

    @transaction.atomic
    def handle(self, *args, **opcoes):
        if OrdemServico.objects.exists():
            raise CommandError("Já existem ordens cadastradas. Os dados de demonstração não foram carregados.")
        usuario = get_user_model().objects.filter(username=opcoes["usuario"]).first()
        if usuario is None:
            raise CommandError(f"Crie antes o usuário '{opcoes['usuario']}' (python manage.py createsuperuser ou pelo Admin).")

        hoje = timezone.localdate()
        etapas = {e.sequencia: e for e in Etapa.objects.all()}
        for placa, marca, modelo, cor, nome, sequencia, dias in CARROS:
            cliente = Cliente.objects.create(nome=nome, telefone="+39 000 000 0000")
            veiculo = Veiculo.objects.create(placa=placa, marca=marca, modelo=modelo, cor=cor, cliente=cliente)
            ordem = OrdemServico.objects.create(
                veiculo=veiculo,
                tipo_atendimento=OrdemServico.TipoAtendimento.SEGURO,
                descricao_servico="Reparo de lataria e pintura (dados fictícios de demonstração)",
                data_entrada=hoje - timedelta(days=10),
                prazo_estimado=hoje + timedelta(days=dias),
                etapa_atual=etapas[sequencia],
                criado_por=usuario,
            )
            anterior = None
            for s in range(1, sequencia + 1):
                HistoricoEtapa.objects.create(ordem=ordem, etapa_anterior=anterior, etapa_nova=etapas[s], usuario=usuario)
                anterior = etapas[s]
        self.stdout.write(self.style.SUCCESS(f"{len(CARROS)} ordens fictícias criadas."))
