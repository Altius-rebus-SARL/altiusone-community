from django.conf import settings


def version_context(request):
    return {"ALTIUSONE_VERSION": settings.ALTIUSONE_VERSION}
