"""Views do MVP: regras de negócio de cada tela (camada View do MVT)."""

from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from .models import Etapa, OrdemServico


@login_required
def painel(request):
    """RF04 – painel com as ordens em andamento, organizadas por etapa."""
    ordens = (
        OrdemServico.objects.filter(status=OrdemServico.Status.EM_ANDAMENTO)
        .select_related("veiculo__cliente", "etapa_atual")
        .order_by("prazo_estimado", "id")
    )
    etapas = list(Etapa.objects.filter(ativa=True).order_by("sequencia"))
    por_etapa = {etapa.pk: [] for etapa in etapas}
    for ordem in ordens:
        por_etapa.setdefault(ordem.etapa_atual_id, []).append(ordem)
    colunas = [{"etapa": etapa, "ordens": por_etapa.get(etapa.pk, [])} for etapa in etapas]
    contexto = {"colunas": colunas, "total": sum(len(c["ordens"]) for c in colunas)}
    return render(request, "oficina/painel.html", contexto)
