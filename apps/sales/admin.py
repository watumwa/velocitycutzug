from django.contrib import admin

from .models import Sale, SaleItem


class SaleItemInline(admin.TabularInline):
    model = SaleItem
    extra = 0
    fields = (
        "service",
        "employee",
        "price",
        "commission_rate",
        "commission_amount",
        "support_employee",
        "support_commission_amount",
    )
    readonly_fields = (
        "commission_amount",
        "support_commission_amount",
    )


@admin.register(Sale)
class SaleAdmin(admin.ModelAdmin):
    list_display = (
        "created_at",
        "services_display",
        "employee_summary",
        "customer",
        "amount",
        "payment_method",
        "commission_amount",
        "status",
        "approved_by",
        "approved_at",
    )

    list_filter = (
        "status",
        "payment_method",
        "employee",
    )

    search_fields = (
        "employee__name",
        "items__employee__name",
        "items__support_employee__name",
        "items__service__name",
        "customer__name",
        "notes",
    )

    # IMPORTANT:
    # Do not use date_hierarchy on Namecheap/MariaDB shared hosting.
    # It can crash with:
    # ValueError: Database returned an invalid datetime value.
    # date_hierarchy = "created_at"

    inlines = [SaleItemInline]

    actions = [
        "approve_selected_cash",
        "approve_selected_mobile_money",
        "reject_selected",
    ]

    @admin.display(description="Services")
    def services_display(self, obj):
        return obj.service_summary

    @admin.action(description="Approve selected pending sales as Cash")
    def approve_selected_cash(self, request, queryset):
        count = 0

        for sale in queryset:
            sale.approve(request.user, payment_method=Sale.PaymentMethod.CASH)
            count += 1

        self.message_user(
            request,
            f"{count} sale(s) approved as Cash and commission counted.",
        )

    @admin.action(description="Approve selected pending sales as Mobile Money")
    def approve_selected_mobile_money(self, request, queryset):
        count = 0

        for sale in queryset:
            sale.approve(request.user, payment_method=Sale.PaymentMethod.MOBILE_MONEY)
            count += 1

        self.message_user(
            request,
            f"{count} sale(s) approved as Mobile Money and commission counted.",
        )

    @admin.action(description="Reject selected pending sales")
    def reject_selected(self, request, queryset):
        count = 0

        for sale in queryset:
            sale.reject(request.user)
            count += 1

        self.message_user(request, f"{count} sale(s) rejected.")


@admin.register(SaleItem)
class SaleItemAdmin(admin.ModelAdmin):
    list_display = (
        "sale",
        "service",
        "employee",
        "support_employee",
        "price",
        "commission_rate",
        "commission_amount",
        "support_commission_amount",
    )

    list_filter = (
        "service",
        "employee",
        "support_employee",
    )

    search_fields = (
        "service__name",
        "employee__name",
        "support_employee__name",
    )