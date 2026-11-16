"""Testes do comando de dados de demonstração e das regras do Django Admin."""

from io import StringIO

from django.core.exceptions import ValidationError
from django.core.management import CommandError, call_command
from django.test import TestCase
from django.urls import reverse

from oficina.models import Etapa, HistoricoEtapa, OrdemServico, Veiculo

from .fabricas import criar_ordem, criar_usuario, criar_veiculo


class CarregarDadosDemoTests(TestCase):
    def test_cria_cinco_ordens_ficticias_com_historico(self):
        criar_usuario("riccardo.demo")
        saida = StringIO()
        call_command("carregar_dados_demo", stdout=saida)
        self.assertIn("5 ordens fictícias criadas", saida.getvalue())
        self.assertEqual(OrdemServico.objects.count(), 5)
        # Fiat Punto (etapa 3) tem 3 registros: abertura + 2 avanços.
        punto = OrdemServico.objects.get(veiculo__placa="KL678MN")
        self.assertEqual(HistoricoEtapa.objects.filter(ordem=punto).count(), 3)

    def test_recusa_carregar_se_ja_existem_ordens(self):
        usuario = criar_usuario("riccardo.demo")
        criar_ordem(usuario)
        with self.assertRaisesMessage(CommandError, "Já existem ordens"):
            call_command("carregar_dados_demo", stdout=StringIO())

    def test_exige_usuario_existente(self):
        with self.assertRaisesMessage(CommandError, "Crie antes o usuário"):
            call_command("carregar_dados_demo", "--usuario", "inexistente", stdout=StringIO())


class AdminTests(TestCase):
    def setUp(self):
        self.dono = criar_usuario("dono", is_staff=True, is_superuser=True)
        self.client.force_login(self.dono)

    def test_etapa_em_uso_nao_pode_ser_excluida(self):
        ordem = criar_ordem(self.dono)
        url = reverse("admin:oficina_etapa_delete", args=[ordem.etapa_atual.pk])
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_etapa_sem_uso_pode_ser_excluida(self):
        etapa = Etapa.objects.create(nome="Polimento", sequencia=6, responsavel="Davide")
        url = reverse("admin:oficina_etapa_delete", args=[etapa.pk])
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_historico_nao_pode_ser_criado_nem_editado_pelo_admin(self):
        ordem = criar_ordem(self.dono)
        registro = HistoricoEtapa.objects.create(ordem=ordem, etapa_nova=ordem.etapa_atual, usuario=self.dono)
        self.assertEqual(self.client.get(reverse("admin:oficina_historicoetapa_add")).status_code, 403)
        self.client.post(reverse("admin:oficina_historicoetapa_change", args=[registro.pk]), {})
        self.assertEqual(HistoricoEtapa.objects.count(), 1)
        resposta = self.client.get(reverse("admin:oficina_ordemservico_change", args=[ordem.pk]))
        self.assertContains(resposta, "Desmontagem")


class ValidacoesDoModeloTests(TestCase):
    def test_ano_do_veiculo_fora_do_intervalo_e_recusado(self):
        veiculo = criar_veiculo()
        veiculo.ano = 1900
        with self.assertRaises(ValidationError):
            veiculo.full_clean()

    def test_representacoes_em_texto(self):
        usuario = criar_usuario()
        ordem = criar_ordem(usuario)
        self.assertEqual(str(ordem.etapa_atual), "1. Desmontagem")
        self.assertIn("AB123CD", str(ordem.veiculo))
        self.assertEqual(str(ordem.veiculo.cliente), "Marco Bianchi")
        self.assertIn("Ordem #", str(ordem))
        abertura = HistoricoEtapa.objects.create(ordem=ordem, etapa_nova=ordem.etapa_atual, usuario=usuario)
        self.assertIn("Abertura → Desmontagem", str(abertura))
        self.assertIsNone(OrdemServico(status="entregue", prazo_estimado=ordem.prazo_estimado).situacao_prazo())
        self.assertEqual(Veiculo.objects.count(), 1)
