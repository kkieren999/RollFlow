from django.urls import include, path
from accounts.admin import admin_site
from accounts.views import portal_login, teacher, sign_out

urlpatterns = [
    path("", portal_login, name="teacher-login"),
    path("login/", portal_login),
    path("admin-login/", portal_login, {"mode": "admin"}, name="admin-login"),
    path("teacher/", teacher, name="teacher"),
    path("logout/", sign_out, name="logout"),
    path("manage/", include("rollflow.management_urls")),
    path("admin/", admin_site.urls),
]
