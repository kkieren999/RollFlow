from django.urls import path
from accounts import staff_views, student_views

urlpatterns = [
    path("", staff_views.dashboard, name="management-dashboard"),
    path("staff/add/", staff_views.staff_edit, name="management-staff-add"),
    path("staff/import/", staff_views.staff_import, name="management-staff-import"),
    path("staff/<int:pk>/edit/", staff_views.staff_edit, name="management-staff-edit"),
    path("staff/<int:pk>/reset/", staff_views.staff_reset, name="management-staff-reset"),
    path("staff/<int:pk>/status/", staff_views.staff_status, name="management-staff-status"),
    path("students/", student_views.directory, name="management-student-directory"),
    path("students/add/", student_views.edit, name="management-student-add"),
    path("students/import/", student_views.import_students, name="management-student-import"),
    path("students/template/", student_views.sample_csv, name="management-student-template"),
    path("students/<int:pk>/", student_views.detail, name="management-student-detail"),
    path("students/<int:pk>/edit/", student_views.edit, name="management-student-edit"),
    path("students/<int:pk>/photo/", student_views.photo, name="management-student-photo"),
    path("students/<int:pk>/photo/upload/", student_views.photo_upload, name="management-student-photo-upload"),
    path("students/<int:pk>/photo/remove/", student_views.photo_remove, name="management-student-photo-remove"),
    path("<str:section>/", staff_views.section, name="management-section"),
]
