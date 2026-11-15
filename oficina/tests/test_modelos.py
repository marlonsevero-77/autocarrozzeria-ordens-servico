"""Testes unitários do modelo de dados."""

from datetime import timedelta

from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.test import TestCase
from django.utils import timezone

from oficina.models import Etapa, OrdemServico, Veiculo, normalizar_placa

from .fabricas import criar_ordem, criar_usuario, criar_veiculo


class EtapasIniciaisTests(TestCase):
    def test_cinco_etapas_da_oficina_cadastradas_em_ordem(self):
        nomes = list(Etapa.objects.order_by("sequencia").values_list("nome", "responsavel"))
        self.assertEqual(
            nomes,
            [
                ("Desmontagem", "Giuseppe"),
                ("Alinhamento do reparo", "Fabio"),
                ("Fundo e massa", "Filippo e Riccardo"),
                ("Mascaramento e pintura", "Davide"),
                ("Revisão e montagem", "Giuseppe"),
            ],
        )

    def test_proxima_ignora_etapas_desativadas(self):
        Etapa.objects.filter(sequencia=2).update(ativa=False)
        self.assertEqual(Etapa.objects.get(sequencia=1).proxima().sequencia, 3)


class VeiculoTests(TestCase):
    def test_placa_normalizada_em_maiusculas_sem_espacos(self):
        self.assertEqual(normalizar_placa(" ab 123-cd "), "AB123CD")
        veiculo = criar_veiculo(placa="ab 123 cd")
        self.assertEqual(veiculo.placa, "AB123CD")

    def test_placa_duplicada_e_recusada(self):
        criar_veiculo(placa="AB123CD")
        with self.assertRaises(IntegrityError), transaction.atomic():
            criar_veiculo(placa="ab123cd")

    def test_placa_com_caracteres_especiais_e_invalida(self):
        veiculo = Veiculo(placa="AB123CD' OR '1'='1", marca="Fiat", modelo="Panda", cor="Branca")
        with self.assertRaises(ValidationError):
            veiculo.full_clean(exclude=["cliente"])


class OrdemServicoTests(TestCase):
    def setUp(self):
        self.usuario = criar_usuario()

    def test_nao_permite_duas_ordens_em_andamento_para_o_mesmo_veiculo(self):
        ordem = criar_ordem(self.usuario)
        with self.assertRaises(IntegrityError), transaction.atomic():
            criar_ordem(self.usuario, veiculo=ordem.veiculo)

    def test_prazo_anterior_a_entrada_e_recusado_pelo_banco(self):
        with self.assertRaises(IntegrityError), transaction.atomic():
            criar_ordem(self.usuario, dias_prazo=-1)

    def test_situacao_prazo(self):
        hoje = timezone.localdate()
        ordem = criar_ordem(self.usuario, dias_prazo=3)
        self.assertIsNone(ordem.situacao_prazo(hoje))
        self.assertEqual(ordem.situacao_prazo(hoje + timedelta(days=1)), "perto")
        self.assertEqual(ordem.situacao_prazo(hoje + timedelta(days=3)), "perto")
        self.assertEqual(ordem.situacao_prazo(hoje + timedelta(days=4)), "atrasado")
        self.assertEqual(ordem.dias_atraso(hoje + timedelta(days=5)), 2)

    def test_ordem_comeca_na_primeira_etapa(self):
        ordem = criar_ordem(self.usuario)
        self.assertEqual(ordem.etapa_atual.nome, "Desmontagem")
        self.assertEqual(ordem.status, OrdemServico.Status.EM_ANDAMENTO)
