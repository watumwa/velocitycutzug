from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def page_url(context, page_number):
    request = context.get("request")
    if not request:
        return f"?page={page_number}"
    query = request.GET.copy()
    query["page"] = page_number
    return f"?{query.urlencode()}"
