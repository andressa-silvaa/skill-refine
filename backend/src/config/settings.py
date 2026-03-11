"""Django settings - composed from settings_modules."""
from __future__ import annotations

from config.settings_modules.base import *  # noqa: F401, F403
from config.settings_modules.security import *  # noqa: F401, F403
from config.settings_modules.auth import *  # noqa: F401, F403
from config.settings_modules.email import *  # noqa: F401, F403
from config.settings_modules.ai import *  # noqa: F401, F403
from config.settings_modules.pdf import *  # noqa: F401, F403
from config.settings_modules.celery import *  # noqa: F401, F403
from config.settings_modules.drf import *  # noqa: F401, F403
