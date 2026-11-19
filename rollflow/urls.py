from django.urls import path
from accounts.admin import admin_site
from accounts.views import portal_login, teacher, sign_out

urlpatterns = [
    path("", portal_login, name="teacher-login"),
    path("login/", portal_login),
    path("admin-login/", portal_login, {"mode": "admin"}, name="admin-login"),
    path("teacher/", teacher, name="teacher"),
    path("logout/", sign_out, name="logout"),
    path("admin/", admin_site.urls),
]
