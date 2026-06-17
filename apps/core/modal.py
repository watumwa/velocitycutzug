from django.http import HttpResponse
from django.template.loader import render_to_string


def is_modal(request):
    return request.headers.get("X-Modal") == "1"


def modal_success(message):
    # A small 200 response is more reliable on shared hosting/proxies than 204.
    response = HttpResponse("", status=200)
    response["X-Modal-Success"] = message
    return response


def render_modal(request, template, context, status=200):
    """Render a _partial version of the template (strips base.html layout)."""
    # Derive partial template name: customers/form.html → customers/_form.html
    parts = template.rsplit("/", 1)
    partial = parts[0] + "/_" + parts[1] if len(parts) == 2 else "_" + template
    html = render_to_string(partial, context, request=request)
    return HttpResponse(html, status=status)
