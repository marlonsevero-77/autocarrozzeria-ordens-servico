"""Views do MVP: regras de negócio de cada tela (camada View do MVT)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.http import require_POST

from .forms import NovaOrdemForm
from .models import Etapa, OrdemServico, normalizar_placa


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
    ultima_atualizada = request.session.pop("ultima_ordem_atualizada", None)
    # Próxima etapa calculada uma vez por etapa (evita consultas repetidas ao banco).
    proxima = {atual.pk: seguinte for atual, seguinte in zip(etapas, etapas[1:] + [None])}
    hoje = timezone.localdate()
    for ordem in ordens:
        ordem.alerta = ordem.situacao_prazo(hoje)
        ordem.atraso = ordem.dias_atraso(hoje)
        ordem.proxima = proxima.get(ordem.etapa_atual_id)
        ordem.pode_desfazer = ordem.pk == ultima_atualizada
    colunas = [{"etapa": etapa, "ordens": por_etapa.get(etapa.pk, [])} for etapa in etapas]
    contexto = {
        "colunas": colunas,
        "total": sum(len(c["ordens"]) for c in colunas),
        "ultima_atualizada": ultima_atualizada,
    }
    return render(request, "oficina/painel.html", contexto)


@login_required
def nova_ordem(request):
    """RF02 – cadastro da ordem de serviço."""
    etapa_inicial = Etapa.primeira()

    if request.method == "POST" and request.POST.get("acao") == "buscar":
        # Busca pela placa para reaproveitar veículo e cliente já cadastrados.
        placa = request.POST.get("placa", "")
        iniciais = NovaOrdemForm.dados_iniciais_da_placa(placa)
        if iniciais:
            messages.info(request, "Veículo já cadastrado: dados do veículo e do cliente preenchidos. Confira antes de salvar.")
            form = NovaOrdemForm(initial=iniciais)
        else:
            messages.info(request, "Placa ainda não cadastrada: preencha os dados do veículo e do cliente.")
            form = NovaOrdemForm(initial={"placa": normalizar_placa(placa)})
        return render(request, "oficina/nova_ordem.html", {"form": form, "etapa_inicial": etapa_inicial})

    if request.method == "POST":
        form = NovaOrdemForm(request.POST)
        if form.is_valid():
            try:
                ordem = form.salvar(request.user)
            except ValidationError as erro:
                form.add_error(None, erro)
            else:
                messages.success(
                    request,
                    f"Ordem cadastrada na etapa {ordem.etapa_atual.nome}: "
                    f"{ordem.veiculo.marca} {ordem.veiculo.modelo} {ordem.veiculo.placa}.",
                )
                return redirect("oficina:painel")
    else:
        form = NovaOrdemForm()

    return render(request, "oficina/nova_ordem.html", {"form": form, "etapa_inicial": etapa_inicial})


@login_required
@require_POST
def avancar_etapa(request, pk):
    """RF03 – avança a ordem para a próxima etapa ou marca como entregue."""
    ordem = get_object_or_404(OrdemServico.objects.select_related("veiculo", "etapa_atual"), pk=pk)
    try:
        registro = ordem.avancar_etapa(request.user)
    except ValidationError:
        messages.error(request, "Esta ordem já foi entregue e não pode mudar de etapa.")
        return redirect("oficina:painel")

    carro = f"{ordem.veiculo.marca} {ordem.veiculo.modelo} {ordem.veiculo.placa}"
    if registro.etapa_nova is None:
        messages.success(request, f"{carro} foi marcado como entregue e saiu do painel.")
    else:
        messages.success(
            request,
            f"{carro} avançou para {registro.etapa_nova.nome} – responsável: {registro.etapa_nova.responsavel}.",
        )
    request.session["ultima_ordem_atualizada"] = ordem.pk
    return redirect("oficina:painel")


@login_required
@require_POST
def desfazer_avanco(request, pk):
    """Ajuste da validação: desfaz o último avanço feito por engano."""
    ordem = get_object_or_404(OrdemServico.objects.select_related("veiculo"), pk=pk)
    try:
        registro = ordem.desfazer_ultimo_avanco(request.user)
    except ValidationError:
        messages.error(request, "Não há avanço recente para desfazer nesta ordem.")
        return redirect("oficina:painel")
    messages.success(
        request,
        f"Avanço desfeito: {ordem.veiculo.marca} {ordem.veiculo.modelo} {ordem.veiculo.placa} "
        f"voltou para {registro.etapa_nova.nome}. A correção foi registrada no histórico.",
    )
    return redirect("oficina:painel")
