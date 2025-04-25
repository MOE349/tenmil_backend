from custom_commands.generators.base_generator import BaseGenerator
from custom_commands.generators.platform_generator import PlatformGenerator
from custom_commands.helpers.constants import PROJECT_NAME


class ModelGenerator(BaseGenerator):
    def generate(self):
        self.write_models_file()

    def write_models_file(self):
        model_script = ''
        for model_name in self.models:
            title_model_name = self.generate_class_name(model_name)
            model_script += f"class {title_model_name}(BaseModel):\n    pass\n\n\n"
        script = (
            f"from {PROJECT_NAME}.base_features.db.base_model import BaseModel\n\n\n"
        ) + model_script
        self.write_to_file(self.app_name, "models", script)
        platform_generator = PlatformGenerator(
            app_name=self.app_name, platforms=self.platforms, models=self.models)
        platform_generator.generate()
