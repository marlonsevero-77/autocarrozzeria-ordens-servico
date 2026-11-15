"""Testes de integração do avanço de etapa e do painel com alertas (RF03, RF04, RF05)."""

from datetime import timedelta

from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from oficina.models import Etapa, HistoricoEtapa, OrdemServico

from .fabricas import criar_ordem, criar_usuario, criar_veiculo


class AvancoEtapaTests(TestCase):
    def setUp(self):
        self.usuario = criar_usuario()
        self.client.force_login(self.usuario)
        self.ordem = criar_ordem(self.usuario, etapa=Etapa.objects.get(nome="Fundo e massa"))
        self.url = reverse("oficina:avancar_etapa", args=[self.ordem.pk])

    def test_avanca_para_a_proxima_etapa_com_responsavel_e_historico(self):
        resposta = self.client.post(self.url, follow=True)
        self.ordem.refresh_from_db()
        self.assertEqual(self.ordem.etapa_atual.nome, "Mascaramento e pintura")
        self.assertContains(resposta, "avançou para Mascaramento e pintura – responsável: Davide")
        historico = HistoricoEtapa.objects.get(ordem=self.ordem)
        self.assertEqual(historico.etapa_anterior.nome, "Fundo e massa")
        self.assertEqual(historico.usuario, self.usuario)

    def test_cada_avanco_gera_exatamente_um_registro(self):
        self.client.post(self.url)
        self.client.post(self.url)
        self.assertEqual(HistoricoEtapa.objects.filter(ordem=self.ordem).count(), 2)

    def test_ultima_etapa_marca_como_entregue_e_sai_do_painel(self):
        self.ordem.etapa_atual = Etapa.objects.get(nome="Revisão e montagem")
        self.ordem.save()
        resposta = self.client.post(self.url, follow=True)
        self.ordem.refresh_from_db()
        self.assertEqual(self.ordem.status, OrdemServico.Status.ENTREGUE)
        self.assertIsNotNone(self.ordem.data_entrega)
        self.assertContains(resposta, "foi marcado como entregue")
        self.assertNotContains(resposta, 'aria-label="Fiat Panda, placa AB123CD"')

    def test_ordem_entregue_nao_muda_de_etapa(self):
        self.ordem.etapa_atual = Etapa.objects.get(nome="Revisão e montagem")
        self.ordem.save()
        self.client.post(self.url)
        resposta = self.client.post(self.url, follow=True)
        self.assertContains(resposta, "já foi entregue")
        self.assertEqual(HistoricoEtapa.objects.filter(ordem=self.ordem).count(), 1)

    def test_avanco_por_get_e_recusado(self):
        self.assertEqual(self.client.get(self.url).status_code, 405)

    def test_avanco_sem_login_redireciona_e_nao_altera(self):
        self.client.logout()
        resposta = self.client.post(self.url)
        self.assertEqual(resposta.status_code, 302)
        self.ordem.refresh_from_db()
        self.assertEqual(self.ordem.etapa_atual.nome, "Fundo e massa")

    def test_avanco_sem_token_csrf_e_recusado(self):
        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        self.assertEqual(cliente.post(self.url).status_code, 403)

    def test_ordem_inexistente_retorna_404(self):
        resposta = self.client.post(reverse("oficina:avancar_etapa", args=[99999]))
        self.assertEqual(resposta.status_code, 404)


class PainelAlertasTests(TestCase):
    def setUp(self):
        self.usuario = criar_usuario()
        self.client.force_login(self.usuario)

    def test_alertas_com_texto_e_icone(self):
        criar_ordem(self.usuario, veiculo=criar_veiculo("KL678MN", "Elena Russo"), dias_prazo=2)
        atrasada = criar_ordem(self.usuario, veiculo=criar_veiculo("EF789GH", "Luca Ferri"), dias_prazo=5)
        # Força um prazo vencido ajustando entrada e prazo para o passado.
        hoje = timezone.localdate()
        OrdemServico.objects.filter(pk=atrasada.pk).update(
            data_entrada=hoje - timedelta(days=10), prazo_estimado=hoje - timedelta(days=1)
        )
        resposta = self.client.get(reverse("oficina:painel"))
        self.assertContains(resposta, "bi-clock-fill", count=2)  # legenda + cartão
        self.assertContains(resposta, "Perto do prazo", count=2)
        self.assertContains(resposta, "Atrasado", count=2)
        self.assertContains(resposta, "1 dia de atraso")

    def test_sem_alerta_quando_prazo_distante(self):
        criar_ordem(self.usuario, dias_prazo=10)
        resposta = self.client.get(reverse("oficina:painel"))
        self.assertContains(resposta, "Perto do prazo", count=1)  # apenas a legenda

    def test_painel_usa_numero_fixo_de_consultas(self):
        for i, placa in enumerate(["AA111AA", "BB222BB", "CC333CC", "DD444DD", "EE555EE"]):
            criar_ordem(self.usuario, veiculo=criar_veiculo(placa, f"Cliente {i}"))
        with self.assertNumQueries(4):
            # sessão, usuário, etapas e ordens com veículo/cliente/etapa
            self.client.get(reverse("oficina:painel"))
