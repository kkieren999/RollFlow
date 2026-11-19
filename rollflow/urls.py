from django.urls import include, path
from accounts.admin import admin_site
from accounts.master_views import master
from accounts.views import portal_login, teacher, sign_out, teacher_timetable

urlpatterns = [
    path("", portal_login, name="teacher-login"),
    path("login/", portal_login),
    path("admin-login/", portal_login, {"mode": "admin"}, name="admin-login"),
    path("teacher/master/", master, name="teacher-master"),
    path("teacher/timetable/", teacher_timetable, name="teacher-timetable"),
    path("teacher/", teacher, name="teacher"),
    path("logout/", sign_out, name="logout"),
    path("manage/", include("rollflow.management_urls")),
    path("admin/", admin_site.urls),
]
