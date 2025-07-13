from django.apps import AppConfig


class PmAutomationConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'pm_automation'
    verbose_name = 'PM Automation'

    def ready(self):
        import pm_automation.signals
