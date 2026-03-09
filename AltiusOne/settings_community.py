# AltiusOne/settings_community.py
# Version communautaire (AGPL-3.0) — importe les settings complets
# puis désactive les modules propriétaires (Nextcloud, OnlyOffice).

from AltiusOne.settings import *  # noqa: F401, F403

# Désactiver les intégrations propriétaires
NEXTCLOUD_ENABLED = False
ONLYOFFICE_ENABLED = False

# Retirer les apps non-communautaires si présentes
_COMMUNITY_EXCLUDE = set()
INSTALLED_APPS = [app for app in INSTALLED_APPS if app not in _COMMUNITY_EXCLUDE]
