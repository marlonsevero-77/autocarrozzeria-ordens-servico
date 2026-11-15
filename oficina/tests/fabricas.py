"""Funções auxiliares para criar dados fictícios nos testes."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.utils import timezone

from oficina.models import Cliente, Etapa, OrdemServico, Veiculo

SENHA_TESTE = "senha-de-teste-ficticia-123"


def criar_usuario(username="riccardo.demo", **extra):
    return get_user_model().objects.create_user(username=username, password=SENHA_TESTE, first_name="Riccardo", **extra)


def criar_veiculo(placa="AB123CD", cliente_nome="Marco Bianchi"):
    cliente = Cliente.objects.create(nome=cliente_nome, telefone="+39 000 000 0000")
    return Veiculo.objects.create(placa=placa, marca="Fiat", modelo="Panda", cor="Branca", cliente=cliente)


def criar_ordem(usuario, veiculo=None, dias_prazo=7, etapa=None, **extra):
    veiculo = veiculo or criar_veiculo()
    return OrdemServico.objects.create(
        veiculo=veiculo,
        tipo_atendimento=OrdemServico.TipoAtendimento.SEGURO,
        descricao_servico="Reparo do para-choque dianteiro e pintura do capô",
        prazo_estimado=timezone.localdate() + timedelta(days=dias_prazo),
        etapa_atual=etapa or Etapa.primeira(),
        criado_por=usuario,
        **extra,
    )
