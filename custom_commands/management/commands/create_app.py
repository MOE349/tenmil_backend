from django.core.management.base import BaseCommand

from custom_commands.generators.app_generator import AppGenerator


class Command(BaseCommand):
    help = "Creates Maly structured"

    def add_arguments(self, parser):
        parser.add_argument("--app_name", type=str)
        parser.add_argument("--platforms", nargs="+", type=str)
        parser.add_argument("--models", nargs="+", type=str)

    def handle(self, *args, **options):
        app_name = options["app_name"]
        platforms = options["platforms"]
        models = options["models"]
        generator = AppGenerator(app_name, platforms, models)
        generator.generate()
