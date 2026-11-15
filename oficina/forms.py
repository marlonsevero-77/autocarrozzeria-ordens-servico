"""Formulários com validação no servidor (RF02, RNF02)."""

from django import forms
from django.core.exceptions import ValidationError
from django.db import IntegrityError, transaction
from django.utils import timezone

from .models import (
    LIMITE_DESCRICAO,
    Cliente,
    Etapa,
    HistoricoEtapa,
    OrdemServico,
    Veiculo,
    normalizar_placa,
    validar_placa,
)


class NovaOrdemForm(forms.Form):
    """Cadastro da ordem de serviço, reaproveitando veículo e cliente pela placa."""

    placa = forms.CharField(
        label="Placa",
        max_length=12,
        help_text="Somente letras e números, sem espaços.",
        widget=forms.TextInput(attrs={"autocomplete": "off", "pattern": "[A-Za-z0-9 \\-]{1,12}"}),
    )
    marca = forms.CharField(label="Marca", max_length=40)
    modelo = forms.CharField(label="Modelo", max_length=60)
    cor = forms.CharField(label="Cor", max_length=30)
    cliente_nome = forms.CharField(label="Nome do cliente", max_length=100)
    telefone = forms.CharField(
        label="Telefone",
        max_length=20,
        widget=forms.TextInput(attrs={"inputmode": "tel", "autocomplete": "off"}),
    )
    tipo_atendimento = forms.ChoiceField(
        label="Tipo de atendimento",
        choices=OrdemServico.TipoAtendimento.choices,
        widget=forms.RadioSelect,
    )
    descricao_servico = forms.CharField(
        label="Descrição do serviço",
        max_length=LIMITE_DESCRICAO,
        help_text=f"Até {LIMITE_DESCRICAO} caracteres.",
        widget=forms.Textarea(attrs={"rows": 3}),
    )
    prazo_estimado = forms.DateField(
        label="Prazo estimado",
        widget=forms.DateInput(attrs={"type": "date"}, format="%Y-%m-%d"),
        error_messages={"invalid": "Data inválida: use o formato dia/mês/ano."},
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for nome, campo in self.fields.items():
            widget = campo.widget
            if not isinstance(widget, forms.RadioSelect):
                widget.attrs.setdefault("class", "form-control")
            if campo.help_text:
                widget.attrs["aria-describedby"] = f"ajuda-{nome}"

    def full_clean(self):
        super().full_clean()
        # Acessibilidade: campos com erro recebem aria-invalid e apontam para a mensagem.
        for nome in self.errors:
            if nome not in self.fields:
                continue
            widget = self.fields[nome].widget
            widget.attrs["aria-invalid"] = "true"
            ids = [f"erro-{nome}"] + ([f"ajuda-{nome}"] if self.fields[nome].help_text else [])
            widget.attrs["aria-describedby"] = " ".join(ids)
            if "class" in widget.attrs:
                widget.attrs["class"] += " is-invalid"

    def clean_placa(self):
        placa = normalizar_placa(self.cleaned_data["placa"])
        try:
            validar_placa(placa)
        except ValidationError:
            raise ValidationError("Placa inválida: use apenas letras e números, com até 10 caracteres.")
        if OrdemServico.objects.filter(veiculo__placa=placa, status=OrdemServico.Status.EM_ANDAMENTO).exists():
            raise ValidationError(
                "Este carro já tem uma ordem em andamento. Avance a etapa no painel em vez de abrir outra ordem."
            )
        return placa

    def clean_prazo_estimado(self):
        prazo = self.cleaned_data["prazo_estimado"]
        if prazo < timezone.localdate():
            raise ValidationError("Prazo inválido: informe uma data igual ou posterior a hoje.")
        return prazo

    def clean_cliente_nome(self):
        return self.cleaned_data["cliente_nome"].strip()

    @staticmethod
    def dados_iniciais_da_placa(placa: str) -> dict | None:
        """Busca um veículo já cadastrado para preencher o formulário."""
        veiculo = Veiculo.objects.select_related("cliente").filter(placa=normalizar_placa(placa)).first()
        if veiculo is None:
            return None
        return {
            "placa": veiculo.placa,
            "marca": veiculo.marca,
            "modelo": veiculo.modelo,
            "cor": veiculo.cor,
            "cliente_nome": veiculo.cliente.nome,
            "telefone": veiculo.cliente.telefone,
        }

    @transaction.atomic
    def salvar(self, usuario) -> OrdemServico:
        dados = self.cleaned_data
        etapa_inicial = Etapa.primeira()
        if etapa_inicial is None:
            raise ValidationError("Nenhuma etapa ativa cadastrada. Avise os donos da oficina.")

        veiculo = Veiculo.objects.select_related("cliente").filter(placa=dados["placa"]).first()
        if veiculo is None:
            cliente = Cliente.objects.create(nome=dados["cliente_nome"], telefone=dados["telefone"])
            veiculo = Veiculo.objects.create(
                placa=dados["placa"], marca=dados["marca"], modelo=dados["modelo"], cor=dados["cor"], cliente=cliente
            )
        else:
            # Veículo já conhecido: mantém o cadastro e atualiza dados que mudaram.
            for campo in ("marca", "modelo", "cor"):
                setattr(veiculo, campo, dados[campo])
            veiculo.save()
            cliente = veiculo.cliente
            cliente.nome = dados["cliente_nome"]
            cliente.telefone = dados["telefone"]
            cliente.save()

        try:
            with transaction.atomic():
                ordem = OrdemServico.objects.create(
                    veiculo=veiculo,
                    tipo_atendimento=dados["tipo_atendimento"],
                    descricao_servico=dados["descricao_servico"],
                    prazo_estimado=dados["prazo_estimado"],
                    etapa_atual=etapa_inicial,
                    criado_por=usuario,
                )
        except IntegrityError:
            # Duas pessoas cadastrando o mesmo carro ao mesmo tempo.
            raise ValidationError("Este carro já tem uma ordem em andamento.")

        HistoricoEtapa.objects.create(ordem=ordem, etapa_anterior=None, etapa_nova=etapa_inicial, usuario=usuario)
        return ordem
