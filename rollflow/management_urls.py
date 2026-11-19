from django.urls import path
from accounts import staff_views

urlpatterns = [
    path("", staff_views.dashboard, name="management-dashboard"),
    path("staff/add/", staff_views.staff_edit, name="management-staff-add"),
    path("staff/import/", staff_views.staff_import, name="management-staff-import"),
    path("staff/<int:pk>/edit/", staff_views.staff_edit, name="management-staff-edit"),
    path("staff/<int:pk>/reset/", staff_views.staff_reset, name="management-staff-reset"),
    path("staff/<int:pk>/status/", staff_views.staff_status, name="management-staff-status"),
    path("<str:section>/", staff_views.section, name="management-section"),
]
