from django.contrib import admin
from django.contrib.auth import views as auth_views
from django.urls import include, path

admin.site.site_header = "AutoCarrozzeria Di Girolamo – Administração"
admin.site.site_title = "Administração da oficina"
admin.site.index_title = "Etapas, usuários e registros"

urlpatterns = [
    path("entrar/", auth_views.LoginView.as_view(redirect_authenticated_user=True), name="login"),
    path("sair/", auth_views.LogoutView.as_view(), name="logout"),
    path("admin/", admin.site.urls),
    path("", include("oficina.urls")),
]
