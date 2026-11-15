"""Modelo de dados do MVP (EP2 – Entidades e atributos principais)."""

import re
from datetime import date

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxLengthValidator, MinValueValidator
from django.db import models, transaction
from django.db.models import Q
from django.utils import timezone

PADRAO_PLACA = re.compile(r"^[A-Z0-9]{1,10}$")
DIAS_ALERTA_PRAZO = 2
LIMITE_DESCRICAO = 500


def normalizar_placa(valor: str) -> str:
    """Remove espaços e hífens e converte para maiúsculas (evita duplicidades)."""
    return re.sub(r"[\s\-]", "", valor or "").upper()


def validar_placa(valor: str) -> None:
    if not PADRAO_PLACA.match(valor or ""):
        raise ValidationError(
            "Placa inválida: use apenas letras e números, com até 10 caracteres.",
            code="placa_invalida",
        )


class Etapa(models.Model):
    """Etapas do processo da oficina, editáveis pelo Django Admin."""

    nome = models.CharField(max_length=60, unique=True)
    sequencia = models.PositiveSmallIntegerField(unique=True, validators=[MinValueValidator(1)])
    responsavel = models.CharField(max_length=100)
    ativa = models.BooleanField(default=True)

    class Meta:
        ordering = ["sequencia"]
        verbose_name = "etapa"
        verbose_name_plural = "etapas"

    def __str__(self) -> str:
        return f"{self.sequencia}. {self.nome}"

    def proxima(self):
        return Etapa.objects.filter(ativa=True, sequencia__gt=self.sequencia).order_by("sequencia").first()

    @classmethod
    def primeira(cls):
        return cls.objects.filter(ativa=True).order_by("sequencia").first()


class Cliente(models.Model):
    nome = models.CharField(max_length=100)
    telefone = models.CharField(max_length=20)
    email = models.EmailField(blank=True)
    data_cadastro = models.DateField(auto_now_add=True)

    class Meta:
        ordering = ["nome"]

    def __str__(self) -> str:
        return self.nome


class Veiculo(models.Model):
    placa = models.CharField(max_length=10, unique=True, validators=[validar_placa])
    marca = models.CharField(max_length=40)
    modelo = models.CharField(max_length=60)
    cor = models.CharField(max_length=30)
    ano = models.PositiveSmallIntegerField(null=True, blank=True)
    cliente = models.ForeignKey(Cliente, on_delete=models.PROTECT, related_name="veiculos")

    class Meta:
        ordering = ["placa"]
        verbose_name = "veículo"
        verbose_name_plural = "veículos"

    def __str__(self) -> str:
        return f"{self.marca} {self.modelo} – {self.placa}"

    def clean(self):
        self.placa = normalizar_placa(self.placa)
        if self.ano is not None:
            limite = timezone.localdate().year + 1
            if not 1950 <= self.ano <= limite:
                raise ValidationError({"ano": f"Ano inválido: informe um ano entre 1950 e {limite}."})

    def save(self, *args, **kwargs):
        self.placa = normalizar_placa(self.placa)
        super().save(*args, **kwargs)


class OrdemServico(models.Model):
    class TipoAtendimento(models.TextChoices):
        PARTICULAR = "particular", "Particular"
        SEGURO = "seguro", "Seguro"
        TERCEIROS = "terceiros", "Terceiros"

    class Status(models.TextChoices):
        EM_ANDAMENTO = "em_andamento", "Em andamento"
        ENTREGUE = "entregue", "Entregue"

    veiculo = models.ForeignKey(Veiculo, on_delete=models.PROTECT, related_name="ordens")
    tipo_atendimento = models.CharField(max_length=12, choices=TipoAtendimento.choices)
    descricao_servico = models.TextField(validators=[MaxLengthValidator(LIMITE_DESCRICAO)])
    data_entrada = models.DateField(default=timezone.localdate)
    prazo_estimado = models.DateField()
    etapa_atual = models.ForeignKey(Etapa, on_delete=models.PROTECT, related_name="ordens")
    status = models.CharField(max_length=12, choices=Status.choices, default=Status.EM_ANDAMENTO, db_index=True)
    data_entrega = models.DateField(null=True, blank=True)
    criado_por = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="ordens_criadas")
    data_atualizacao = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["prazo_estimado", "id"]
        verbose_name = "ordem de serviço"
        verbose_name_plural = "ordens de serviço"
        constraints = [
            models.UniqueConstraint(
                fields=["veiculo"],
                condition=Q(status="em_andamento"),
                name="uma_ordem_em_andamento_por_veiculo",
                violation_error_message="Este veículo já possui uma ordem de serviço em andamento.",
            ),
            models.CheckConstraint(
                condition=Q(prazo_estimado__gte=models.F("data_entrada")),
                name="prazo_nao_anterior_a_entrada",
                violation_error_message="O prazo não pode ser anterior à data de entrada.",
            ),
            models.CheckConstraint(
                condition=(
                    Q(status="em_andamento", data_entrega__isnull=True)
                    | Q(status="entregue", data_entrega__isnull=False)
                ),
                name="data_entrega_coerente_com_status",
            ),
        ]

    def __str__(self) -> str:
        return f"Ordem #{self.pk} – {self.veiculo}"

    @property
    def entregue(self) -> bool:
        return self.status == self.Status.ENTREGUE

    def situacao_prazo(self, hoje: date | None = None) -> str | None:
        """Retorna 'atrasado', 'perto' ou None (RF05)."""
        if self.entregue:
            return None
        hoje = hoje or timezone.localdate()
        if hoje > self.prazo_estimado:
            return "atrasado"
        if (self.prazo_estimado - hoje).days <= DIAS_ALERTA_PRAZO:
            return "perto"
        return None

    def dias_atraso(self, hoje: date | None = None) -> int:
        hoje = hoje or timezone.localdate()
        return max((hoje - self.prazo_estimado).days, 0)

    @property
    def proxima_etapa(self):
        return None if self.entregue else self.etapa_atual.proxima()

    @transaction.atomic
    def avancar_etapa(self, usuario) -> "HistoricoEtapa":
        """Avança para a próxima etapa ou marca como entregue (RF03).

        Cada chamada gera exatamente um registro no histórico.
        """
        ordem = OrdemServico.objects.select_for_update().get(pk=self.pk)
        if ordem.entregue:
            raise ValidationError("Esta ordem já foi entregue e não pode mudar de etapa.")
        anterior = ordem.etapa_atual
        proxima = anterior.proxima()
        if proxima is None:
            ordem.status = self.Status.ENTREGUE
            ordem.data_entrega = timezone.localdate()
        else:
            ordem.etapa_atual = proxima
        ordem.save()
        registro = HistoricoEtapa.objects.create(
            ordem=ordem, etapa_anterior=anterior, etapa_nova=proxima, usuario=usuario
        )
        self.refresh_from_db()
        return registro


class HistoricoEtapa(models.Model):
    """Registro imutável de cada mudança de etapa.

    etapa_nova vazia significa que a ordem foi marcada como entregue.
    """

    ordem = models.ForeignKey(OrdemServico, on_delete=models.PROTECT, related_name="historico")
    etapa_anterior = models.ForeignKey(
        Etapa, on_delete=models.PROTECT, null=True, blank=True, related_name="+"
    )
    etapa_nova = models.ForeignKey(Etapa, on_delete=models.PROTECT, null=True, blank=True, related_name="+")
    usuario = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.PROTECT, related_name="+")
    data_hora = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["data_hora", "id"]
        verbose_name = "histórico de etapa"
        verbose_name_plural = "histórico de etapas"
        constraints = [
            models.CheckConstraint(
                condition=~Q(etapa_anterior=models.F("etapa_nova")),
                name="etapa_nova_diferente_da_anterior",
            ),
            models.CheckConstraint(
                condition=Q(etapa_anterior__isnull=False) | Q(etapa_nova__isnull=False),
                name="historico_com_alguma_etapa",
            ),
        ]

    def __str__(self) -> str:
        de = self.etapa_anterior.nome if self.etapa_anterior else "Abertura"
        para = self.etapa_nova.nome if self.etapa_nova else "Entregue"
        return f"{self.ordem_id}: {de} → {para}"
