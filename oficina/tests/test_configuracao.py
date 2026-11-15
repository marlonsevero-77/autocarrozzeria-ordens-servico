"""Testes da configuração base do projeto."""

from django.test import TestCase


class ConfiguracaoBaseTests(TestCase):
    def test_admin_exige_login(self):
        resposta = self.client.get("/admin/")
        self.assertEqual(resposta.status_code, 302)
        self.assertIn("/admin/login/", resposta["Location"])

    def test_cabecalho_content_security_policy_presente(self):
        resposta = self.client.get("/admin/login/")
        self.assertIn("Content-Security-Policy", resposta.headers)
        self.assertIn("script-src 'self'", resposta.headers["Content-Security-Policy"])
