"""Testes de integração do login, logout e controle de acesso (RF01, RNF01)."""

from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .fabricas import SENHA_TESTE, criar_usuario


class LoginTests(TestCase):
    def setUp(self):
        self.usuario = criar_usuario()

    def test_painel_exige_login(self):
        resposta = self.client.get(reverse("oficina:painel"))
        self.assertRedirects(resposta, f"{reverse('login')}?next=/")

    def test_login_valido_abre_o_painel(self):
        resposta = self.client.post(
            reverse("login"), {"username": "riccardo.demo", "password": SENHA_TESTE}, follow=True
        )
        self.assertContains(resposta, "Painel de serviços")

    def test_login_invalido_mostra_mensagem_generica(self):
        resposta = self.client.post(reverse("login"), {"username": "riccardo.demo", "password": "errada"})
        self.assertEqual(resposta.status_code, 200)
        self.assertContains(resposta, "Usuário ou senha inválidos")
        self.assertNotContains(resposta, "Painel de serviços")

    def test_bloqueio_apos_cinco_tentativas_erradas(self):
        for _ in range(5):
            self.client.post(reverse("login"), {"username": "riccardo.demo", "password": "errada"})
        resposta = self.client.post(reverse("login"), {"username": "riccardo.demo", "password": SENHA_TESTE})
        self.assertEqual(resposta.status_code, 429)
        self.assertContains(resposta, "Acesso bloqueado por 15 minutos", status_code=429)

    def test_senha_armazenada_somente_como_hash_pbkdf2(self):
        senha = get_user_model().objects.get(pk=self.usuario.pk).password
        self.assertTrue(senha.startswith("pbkdf2_sha256$"))
        self.assertNotIn(SENHA_TESTE, senha)

    def test_logout_exige_post_e_encerra_a_sessao(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse("logout")).status_code, 405)
        self.client.post(reverse("logout"))
        resposta = self.client.get(reverse("oficina:painel"))
        self.assertEqual(resposta.status_code, 302)

    def test_usuario_sem_is_staff_nao_acessa_o_admin(self):
        self.client.force_login(self.usuario)
        resposta = self.client.get("/admin/")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/admin/login/", resposta["Location"])


class PainelTests(TestCase):
    def test_painel_mostra_as_cinco_etapas_e_responsaveis(self):
        self.client.force_login(criar_usuario())
        resposta = self.client.get(reverse("oficina:painel"))
        for texto in ["Desmontagem", "Fundo e massa", "Filippo e Riccardo", "Revisão e montagem"]:
            self.assertContains(resposta, texto)


class MostrarSenhaTests(TestCase):
    def test_tela_de_login_tem_botao_acessivel_para_mostrar_a_senha(self):
        resposta = self.client.get(reverse("login"))
        self.assertContains(resposta, 'aria-label="Mostrar senha"')
        self.assertContains(resposta, 'aria-controls="id_password"')
        self.assertContains(resposta, "js/senha.js")
        # O campo continua começando oculto.
        self.assertContains(resposta, 'type="password" name="password"')
