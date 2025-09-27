import os

from .base import *

# Static files (CSS, JavaScript, Images)
# https://docs.djangoproject.com/en/stable/howto/static-files/

# This setting informs Django of the URI path from which your static files will be served to users
# Here, they will be accessible at your-domain.onrender.com/static/... or yourcustomdomain.com/static/...
STATIC_URL = "/static/"

# This production code might break development mode, so we check whether we're in DEBUG mode
if not DEBUG:  # Tell Django to copy static assets into a path called `staticfiles` (this is specific to Render)
    STATIC_ROOT = os.path.join(BASE_DIR, "staticfiles")
    # Enable the WhiteNoise storage backend, which compresses static files to reduce disk use
    # and renames the files with unique names for each version to support long-term caching
    STATICFILES_STORAGE = "whitenoise.storage.CompressedManifestStaticFilesStorage"

# Extra places for collectstatic to find static files.
STATICFILES_DIRS = [
    os.path.join(BASE_DIR, "static"),
]
