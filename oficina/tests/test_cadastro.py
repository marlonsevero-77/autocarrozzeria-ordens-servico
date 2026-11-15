"""Testes de integração do cadastro da ordem de serviço (RF02, RNF02)."""

from datetime import timedelta

from django.test import TestCase
from django.urls import reverse
from django.utils import timezone

from oficina.models import HistoricoEtapa, OrdemServico, Veiculo

from .fabricas import criar_ordem, criar_usuario, criar_veiculo


def dados_validos(**alteracoes):
    dados = {
        "acao": "salvar",
        "placa": "AB123CD",
        "marca": "Fiat",
        "modelo": "Panda",
        "cor": "Branca",
        "cliente_nome": "Marco Bianchi",
        "telefone": "+39 000 000 0000",
        "tipo_atendimento": "seguro",
        "descricao_servico": "Reparo do para-choque dianteiro e pintura do capô",
        "prazo_estimado": (timezone.localdate() + timedelta(days=7)).isoformat(),
    }
    dados.update(alteracoes)
    return dados


class CadastroOrdemTests(TestCase):
    def setUp(self):
        self.usuario = criar_usuario()
        self.client.force_login(self.usuario)
        self.url = reverse("oficina:nova_ordem")

    def test_cadastro_exige_login(self):
        self.client.logout()
        resposta = self.client.get(self.url)
        self.assertEqual(resposta.status_code, 302)

    def test_formulario_mostra_rotulos_e_etapa_inicial(self):
        resposta = self.client.get(self.url)
        for texto in ["Placa", "Nome do cliente", "Tipo de atendimento", "Prazo estimado", "Desmontagem"]:
            self.assertContains(resposta, texto)

    def test_cadastro_valido_cria_ordem_na_primeira_etapa_e_historico(self):
        resposta = self.client.post(self.url, dados_validos(), follow=True)
        self.assertContains(resposta, "Ordem cadastrada na etapa Desmontagem")
        ordem = OrdemServico.objects.get()
        self.assertEqual(ordem.etapa_atual.nome, "Desmontagem")
        self.assertEqual(ordem.criado_por, self.usuario)
        self.assertEqual(HistoricoEtapa.objects.filter(ordem=ordem).count(), 1)

    def test_prazo_no_passado_e_recusado_com_mensagem_clara(self):
        ontem = (timezone.localdate() - timedelta(days=1)).isoformat()
        resposta = self.client.post(self.url, dados_validos(prazo_estimado=ontem))
        self.assertContains(resposta, "Prazo inválido: informe uma data igual ou posterior a hoje.")
        self.assertContains(resposta, 'aria-invalid="true"')
        self.assertFalse(OrdemServico.objects.exists())

    def test_campo_obrigatorio_vazio_e_recusado_pelo_servidor(self):
        resposta = self.client.post(self.url, dados_validos(cliente_nome=""))
        self.assertContains(resposta, "A ordem não foi salva")
        self.assertFalse(OrdemServico.objects.exists())

    def test_placa_existente_reaproveita_veiculo_e_cliente(self):
        criar_veiculo(placa="AB123CD")
        self.client.post(self.url, dados_validos(placa="ab 123 cd"))
        self.assertEqual(Veiculo.objects.count(), 1)
        self.assertEqual(OrdemServico.objects.get().veiculo.placa, "AB123CD")

    def test_buscar_placa_preenche_dados_do_veiculo(self):
        criar_veiculo(placa="CD456EF", cliente_nome="Giulia Conti")
        resposta = self.client.post(self.url, {"acao": "buscar", "placa": "cd456ef"})
        self.assertContains(resposta, "Veículo já cadastrado")
        self.assertContains(resposta, 'value="Giulia Conti"')

    def test_segunda_ordem_em_andamento_para_o_mesmo_carro_e_bloqueada(self):
        criar_ordem(self.usuario, veiculo=criar_veiculo(placa="AB123CD"))
        resposta = self.client.post(self.url, dados_validos())
        self.assertContains(resposta, "já tem uma ordem em andamento")
        self.assertEqual(OrdemServico.objects.count(), 1)

    def test_tentativa_de_injecao_sql_na_placa_e_recusada(self):
        resposta = self.client.post(self.url, dados_validos(placa="A' OR 1=1"))
        self.assertContains(resposta, "Placa inválida")
        self.assertFalse(OrdemServico.objects.exists())

    def test_texto_com_script_e_gravado_como_texto_e_exibido_escapado(self):
        self.client.post(self.url, dados_validos(cliente_nome="<script>alert('teste')</script>"))
        resposta = self.client.get(reverse("oficina:painel"))
        self.assertNotContains(resposta, "<script>alert('teste')</script>")
        self.assertContains(resposta, "&lt;script&gt;")

    def test_envio_sem_token_csrf_e_recusado(self):
        from django.test import Client

        cliente = Client(enforce_csrf_checks=True)
        cliente.force_login(self.usuario)
        resposta = cliente.post(self.url, dados_validos())
        self.assertEqual(resposta.status_code, 403)
        self.assertFalse(OrdemServico.objects.exists())
