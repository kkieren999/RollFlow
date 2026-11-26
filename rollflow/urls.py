from django.urls import include, path
from accounts.admin import admin_site
from accounts.master_views import master
from accounts.views import portal_login, teacher, sign_out, teacher_timetable
from accounts.teacher_week_views import week as teacher_week
from accounts.connected_views import roster as connected_roster
from accounts.school_access_views import workspace, manage_access

from accounts import live_views, security_views

urlpatterns = [
    path("manage/security/templates/", security_views.templates, name="security-templates"),
    path("manage/security/effective/<int:pk>/", security_views.effective, name="security-effective"),
    path("manage/security/history/", security_views.history, name="security-history"),
    path("account/password/", security_views.password, name="security-password"),
    path("live/", live_views.home, name="live-home"),
    path("live/day/", live_views.my_day, name="live-day"),
    path("live/roll/", live_views.mark_roll, name="live-roll"),
    path("live/attendance/", live_views.monitor, name="live-monitor"),
    path("", portal_login, name="teacher-login"),
    path("login/", portal_login),
    path("admin-login/", portal_login, {"mode": "admin"}, name="admin-login"),
    path("teacher/master/", master, name="teacher-master"),
    path("teacher/timetable/", teacher_timetable, name="teacher-timetable"),
    path("teacher/week/", teacher_week, name="teacher-week"),
    path("teacher/", teacher, name="teacher"),
    path("teacher/roster/<str:code>/", connected_roster, name="connected-teacher-roster"),
    path("logout/", sign_out, name="logout"),
    path("workspace/", workspace, name="school-workspace"),
    path("workspace/<str:module>/", workspace, name="school-workspace-module"),
    path("manage/access/", manage_access, name="school-access-manage"),
    path("manage/", include("rollflow.management_urls")),
    path("admin/", admin_site.urls),
]
