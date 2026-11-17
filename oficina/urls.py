from django.urls import path

from . import views

app_name = "oficina"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("ordens/nova/", views.nova_ordem, name="nova_ordem"),
    path("ordens/<int:pk>/avancar/", views.avancar_etapa, name="avancar_etapa"),
    path("ordens/<int:pk>/desfazer/", views.desfazer_avanco, name="desfazer_avanco"),
]
