from django.apps import AppConfig


class ItemsConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "items"
    # Preserve applied migrations and database table names.
    label = "tasks"
    verbose_name = "Items"
