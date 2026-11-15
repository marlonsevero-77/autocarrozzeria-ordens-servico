"""Views do MVP: regras de negócio de cada tela (camada View do MVT)."""

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ValidationError
from django.shortcuts import redirect, render

from .forms import NovaOrdemForm
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
            form = NovaOrdemForm(initial={"placa": placa.upper().strip()})
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
