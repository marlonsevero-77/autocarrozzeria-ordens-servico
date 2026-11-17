"""Testes do ajuste feito a partir da validação: desfazer avanço por engano."""

from django.test import Client, TestCase
from django.urls import reverse

from oficina.models import Etapa, HistoricoEtapa

from .fabricas import criar_ordem, criar_usuario


class DesfazerAvancoTests(TestCase):
    def setUp(self):
        self.usuario = criar_usuario()
        self.client.force_login(self.usuario)
        self.ordem = criar_ordem(self.usuario, etapa=Etapa.objects.get(nome="Fundo e massa"))
        HistoricoEtapa.objects.create(ordem=self.ordem, etapa_nova=self.ordem.etapa_atual, usuario=self.usuario)
        self.url_avancar = reverse("oficina:avancar_etapa", args=[self.ordem.pk])
        self.url_desfazer = reverse("oficina:desfazer_avanco", args=[self.ordem.pk])

    def test_botao_aparece_logo_apos_o_avanco(self):
        resposta = self.client.post(self.url_avancar, follow=True)
        self.assertContains(resposta, "Desfazer avanço")

    def test_botao_nao_aparece_sem_avanco_recente(self):
        resposta = self.client.get(reverse("oficina:painel"))
        self.assertNotContains(resposta, "Desfazer avanço")

    def test_desfazer_volta_para_a_etapa_anterior_e_registra_correcao(self):
        self.client.post(self.url_avancar)
        resposta = self.client.post(self.url_desfazer, follow=True)
        self.ordem.refresh_from_db()
        self.assertEqual(self.ordem.etapa_atual.nome, "Fundo e massa")
        self.assertContains(resposta, "voltou para Fundo e massa")
        correcao = HistoricoEtapa.objects.filter(ordem=self.ordem).latest("id")
        self.assertTrue(correcao.correcao)
        self.assertEqual(correcao.etapa_anterior.nome, "Mascaramento e pintura")
        self.assertEqual(correcao.usuario, self.usuario)
        # O histórico não é apagado: abertura + avanço + correção.
        self.assertEqual(HistoricoEtapa.objects.filter(ordem=self.ordem).count(), 3)

    def test_nao_permite_desfazer_duas_vezes(self):
        self.client.post(self.url_avancar)
        self.client.post(self.url_desfazer)
        resposta = self.client.post(self.url_desfazer, follow=True)
        self.assertContains(resposta, "Não há avanço recente para desfazer")
        self.ordem.refresh_from_db()
        self.assertEqual(self.ordem.etapa_atual.nome, "Fundo e massa")

    def test_nao_permite_desfazer_a_abertura_da_ordem(self):
        resposta = self.client.post(self.url_desfazer, follow=True)
        self.assertContains(resposta, "Não há avanço recente para desfazer")

    def test_ordem_entregue_nao_pode_ser_desfeita_pelo_painel(self):
        self.ordem.etapa_atual = Etapa.objects.get(nome="Revisão e montagem")
        self.ordem.save()
        self.client.post(self.url_avancar)
        resposta = self.client.post(self.url_desfazer, follow=True)
        self.assertContains(resposta, "Não há avanço recente para desfazer")

    def test_desfazer_exige_post_login_e_csrf(self):
        self.client.post(self.url_avancar)
        self.assertEqual(self.client.get(self.url_desfazer).status_code, 405)
        cliente_csrf = Client(enforce_csrf_checks=True)
        cliente_csrf.force_login(self.usuario)
        self.assertEqual(cliente_csrf.post(self.url_desfazer).status_code, 403)
        self.client.logout()
        self.assertEqual(self.client.post(self.url_desfazer).status_code, 302)
        self.ordem.refresh_from_db()
        self.assertEqual(self.ordem.etapa_atual.nome, "Mascaramento e pintura")
