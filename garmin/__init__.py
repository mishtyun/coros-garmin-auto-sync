import os

# garmin_connect.configuration instantiates an env-backed singleton at import
# time and requires GARMIN_CONNECT_EMAIL/PASSWORD. Credentials are per-user now
# (stored in Redis), so satisfy the package import with placeholders. All
# imports of garmin_connect must go through this package.
os.environ.setdefault("GARMIN_CONNECT_EMAIL", "unused")
os.environ.setdefault("GARMIN_CONNECT_PASSWORD", "unused")
