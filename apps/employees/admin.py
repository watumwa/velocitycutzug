from django.contrib import admin

from .models import Department, Employee, Role


@admin.register(Role)
class RoleAdmin(admin.ModelAdmin):
    list_display = ("name", "code", "description")
    search_fields = ("name", "code")


@admin.register(Department)
class DepartmentAdmin(admin.ModelAdmin):
    list_display = ("name", "is_active")
    list_filter = ("is_active",)
    search_fields = ("name",)


@admin.register(Employee)
class EmployeeAdmin(admin.ModelAdmin):
    list_display = (
        "name", "role", "department", "phone", "identification_display",
        "commission_type", "commission_value", "is_active", "user", "must_change_password",
    )
    list_filter = ("role", "department", "id_type", "is_active", "must_change_password")
    search_fields = ("name", "phone", "id_number", "national_id", "user__username")
    readonly_fields = ("user",)
    filter_horizontal = ("services",)
