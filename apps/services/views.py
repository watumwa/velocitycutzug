import logging

from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.shortcuts import get_object_or_404, redirect, render

from apps.accounts.permissions import role_required

from .catalog import CATALOG_SERVICE_NAME_SET, SERVICE_CATALOG, sync_service_catalog
from .forms import CustomServiceForm, ServiceForm
from .models import Service

logger = logging.getLogger(__name__)


@login_required
@role_required("admin")
def service_list(request):
    services = list(Service.objects.all())
    service_lookup = {}
    extra_services = []

    for service in services:
        if service.name in CATALOG_SERVICE_NAME_SET and service.name not in service_lookup:
            service_lookup[service.name] = service
        else:
            extra_services.append(service)

    extra_services.sort(key=lambda service: service.name)
    service_sections = []
    total_services = 0
    active_services = 0
    priced_services = 0

    for title, service_names in SERVICE_CATALOG:
        section_entries = []
        section_active = 0
        section_priced = 0

        for service_name in service_names:
            service = service_lookup.get(service_name)
            if service is None:
                continue

            is_priced = bool(service.price)
            section_entries.append(
                {
                    "service": service,
                    "is_priced": is_priced,
                }
            )
            total_services += 1
            section_active += int(service.is_active)
            section_priced += int(is_priced)

        active_services += section_active
        priced_services += section_priced
        service_sections.append(
            {
                "title": title,
                "services": section_entries,
                "service_count": len(section_entries),
                "active_count": section_active,
                "priced_count": section_priced,
                "unpriced_count": len(section_entries) - section_priced,
            }
        )

    return render(
        request,
        "services/list.html",
        {
            "service_sections": service_sections,
            "extra_services": extra_services,
            "total_services": total_services,
            "active_services": active_services,
            "priced_services": priced_services,
            "unpriced_services": total_services - priced_services,
            "custom_service_count": len(extra_services),
        },
    )


from apps.core.modal import is_modal, modal_success, render_modal


@login_required
@role_required("admin")
def service_create(request):
    form = CustomServiceForm(request.POST or None, request.FILES or None)
    if form.is_valid():
        try:
            service = form.save()
        except Exception:
            logger.exception("Service creation failed")
            form.add_error(None, "Service could not be saved. Check the price, name, and photo format.")
        else:
            if is_modal(request):
                return modal_success(f"{service.name} was added successfully.")
            messages.success(request, f"{service.name} was added successfully.")
            return redirect("services:list")
    ctx = {"form": form, "service": form.instance, "title": "Add Service", "is_create": True, "is_catalog_service": False}
    if is_modal(request):
        return render_modal(request, "services/form.html", ctx)
    return render(request, "services/form.html", ctx)


@login_required
@role_required("admin")
def service_update(request, pk):
    service = get_object_or_404(Service, pk=pk)
    is_catalog_service = service.name in CATALOG_SERVICE_NAME_SET
    form_class = ServiceForm if is_catalog_service else CustomServiceForm
    form = form_class(request.POST or None, request.FILES or None, instance=service)
    if form.is_valid():
        try:
            form.save()
        except Exception:
            logger.exception("Service update failed for service id=%s", service.pk)
            form.add_error(None, "Service could not be updated. Check the price, name, and photo format.")
        else:
            if is_modal(request):
                return modal_success("Service updated successfully.")
            messages.success(request, "Service updated successfully.")
            return redirect("services:list")
    ctx = {"form": form, "service": service, "title": f"Edit {service.name}", "is_create": False, "is_catalog_service": is_catalog_service}
    if is_modal(request):
        return render_modal(request, "services/form.html", ctx)
    return render(request, "services/form.html", ctx)
