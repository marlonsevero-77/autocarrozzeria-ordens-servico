from django.contrib import admin

from .models import Cliente, Etapa, HistoricoEtapa, OrdemServico, Veiculo


@admin.register(Etapa)
class EtapaAdmin(admin.ModelAdmin):
    list_display = ["sequencia", "nome", "responsavel", "ativa"]
    list_editable = ["responsavel", "ativa"]
    ordering = ["sequencia"]

    def has_delete_permission(self, request, obj=None):
        # Etapas já usadas não são excluídas: apenas desativadas.
        if obj is not None and obj.ordens.exists():
            return False
        return super().has_delete_permission(request, obj)


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ["nome", "telefone", "email", "data_cadastro"]
    search_fields = ["nome"]


@admin.register(Veiculo)
class VeiculoAdmin(admin.ModelAdmin):
    list_display = ["placa", "marca", "modelo", "cor", "cliente"]
    search_fields = ["placa", "modelo"]


class HistoricoInline(admin.TabularInline):
    model = HistoricoEtapa
    extra = 0
    can_delete = False
    readonly_fields = ["etapa_anterior", "etapa_nova", "usuario", "data_hora", "correcao"]

    def has_add_permission(self, request, obj=None):
        return False


@admin.register(OrdemServico)
class OrdemServicoAdmin(admin.ModelAdmin):
    list_display = ["id", "veiculo", "etapa_atual", "status", "prazo_estimado", "data_entrega"]
    list_filter = ["status", "etapa_atual", "tipo_atendimento"]
    search_fields = ["veiculo__placa", "veiculo__cliente__nome"]
    readonly_fields = ["criado_por", "data_atualizacao"]
    inlines = [HistoricoInline]


@admin.register(HistoricoEtapa)
class HistoricoEtapaAdmin(admin.ModelAdmin):
    list_display = ["ordem", "etapa_anterior", "etapa_nova", "usuario", "data_hora", "correcao"]
    list_filter = ["correcao"]
    readonly_fields = ["ordem", "etapa_anterior", "etapa_nova", "usuario", "data_hora", "correcao"]

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False
