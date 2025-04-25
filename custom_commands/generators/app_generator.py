from custom_commands.generators.base_generator import BaseGenerator
from custom_commands.generators.model_generator import ModelGenerator


class AppGenerator(BaseGenerator):
    def generate(self):
        # create app main folders
        self.create_python_folder(self.app_name)
        path = f"{self.app_name}/"
        self.create_python_folder("migrations", path)
        self.create_python_folder("platforms", path)

        # create main filesests.py",
        self.write_to_file(self.app_name, "tests", "")
        self.write_apps_file()
        model_generator = ModelGenerator(
            app_name=self.app_name, platforms=self.platforms, models=self.models)
        model_generator.generate()
        self.write_admin_file()

        # create platforms folders
        # self.create_platforms_folders()
    def write_admin_file(self):
        admin_script = ""
        for model_name in self.models:
            title_model_name = self.generate_class_name(model_name)
            admin_script += (
                f"admin.site.register({title_model_name})\n"
            )
        script = (
            f"from {self.app_name}.models import *\n"
            f"from django.contrib import admin\n\n\n"
        ) + admin_script
        self.write_to_file(self.app_name, "admin", script)

    def write_apps_file(self):
        script = (
            f"from django.apps import AppConfig\n\n\n"
            f"class {self.generate_class_name(self.app_name)}Config(AppConfig):\n"
            f"    default_auto_field = 'django.db.models.BigAutoField'\n"
            f"    name = '{self.app_name}'\n"
        )
        self.write_to_file(self.app_name, "apps", script)
