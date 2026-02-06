# AltiusOne/spectacular_hooks.py
"""
Hooks pour drf-spectacular pour gérer les endpoints problématiques.
"""


def preprocess_exclude_problematic(endpoints, **kwargs):
    """
    Filtre les endpoints qui causent des erreurs lors de la génération du schéma.
    """
    # Endpoints à exclure temporairement
    excluded_patterns = [
        '/api/v1/modelforms/introspection/',
        '/api/v1/rapports/',
    ]

    filtered = []
    for (path, path_regex, method, callback) in endpoints:
        exclude = False
        for pattern in excluded_patterns:
            if pattern in path:
                exclude = True
                break
        if not exclude:
            filtered.append((path, path_regex, method, callback))

    return filtered
