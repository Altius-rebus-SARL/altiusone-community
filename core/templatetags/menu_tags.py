from django import template

register = template.Library()


@register.simple_tag(takes_context=True)
def active(context, pattern):
    """
    Retourne 'active' si l'URL courante correspond au pattern.
    Pattern: 'namespace:prefix' (ex: 'tva:operation' match 'operation-list', 'operation-create', etc.)
    """
    request = context.get("request")
    if not request or not request.resolver_match:
        return ""

    current_name = request.resolver_match.url_name or ""
    current_namespace = request.resolver_match.namespace or ""

    if ":" in pattern:
        ns, prefix = pattern.split(":", 1)
        # Vérifier le namespace
        if current_namespace != ns:
            return ""
        # Match: prefix exact ou prefix-xxx
        if current_name == prefix or current_name.startswith(prefix + "-"):
            return "active"
    else:
        # Sans namespace
        if current_name == pattern or current_name.startswith(pattern + "-"):
            return "active"

    return ""


@register.simple_tag(takes_context=True)
def menu_open(context, *patterns):
    """Retourne 'show' si l'URL courante correspond à un des patterns"""
    request = context.get("request")
    if not request or not request.resolver_match:
        return ""

    current_name = request.resolver_match.url_name or ""
    current_namespace = request.resolver_match.namespace or ""

    for pattern in patterns:
        if ":" in pattern:
            ns, prefix = pattern.split(":", 1)
            if current_namespace != ns:
                continue
            if current_name == prefix or current_name.startswith(prefix + "-"):
                return "show"
        else:
            if current_name == pattern or current_name.startswith(pattern + "-"):
                return "show"

    return ""


@register.simple_tag(takes_context=True)
def menu_expanded(context, *patterns):
    """Retourne 'true' si le menu doit être expanded"""
    request = context.get("request")
    if not request or not request.resolver_match:
        return "false"

    current_name = request.resolver_match.url_name or ""
    current_namespace = request.resolver_match.namespace or ""

    for pattern in patterns:
        if ":" in pattern:
            ns, prefix = pattern.split(":", 1)
            if current_namespace != ns:
                continue
            if current_name == prefix or current_name.startswith(prefix + "-"):
                return "true"
        else:
            if current_name == pattern or current_name.startswith(pattern + "-"):
                return "true"

    return "false"
