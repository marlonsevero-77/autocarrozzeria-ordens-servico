from django.urls import path

from . import views

app_name = "oficina"

urlpatterns = [
    path("", views.painel, name="painel"),
]
