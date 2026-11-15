from django.urls import path

from . import views

app_name = "oficina"

urlpatterns = [
    path("", views.painel, name="painel"),
    path("ordens/nova/", views.nova_ordem, name="nova_ordem"),
]
