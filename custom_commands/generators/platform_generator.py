from custom_commands.generators.base_generator import BaseGenerator
from custom_commands.helpers.constants import PROJECT_NAME


class PlatformGenerator(BaseGenerator):
    def generate(self):
        self.create_platforms_folders()

    def create_platforms_folders(self):
        for platform in self.platforms:
            self.create_python_folder(platform, f"{self.app_name}/platforms/")
            path = f"{self.app_name}/platforms/{platform}"
            if platform == "base":
                # add base serializers.py
                self.generate_base_serializer(path)
                # add base views.py
                self.generate_base_view(platform, path)
            else:
                # add platform serializers.py
                self.generate_platform_serializers(platform, path)
                # add platform views.py
                self.generate_platform_views(platform, path)
                # add platform urls.py
                self.generate_platform_urls(platform, path)

    def generate_base_serializer(self, path):
        model_serializer_script = ""
        for model_name in self.models:
            title_model_name = self.generate_class_name(model_name)
            model_serializer_script += (f"class {title_model_name}BaseSerializer(BaseSerializer):\n"
                                        f"    class Meta:\n"
                                        f"        model = {title_model_name}\n"
                                        f"        fields = '__all__'\n\n\n"
                                        )
        script = (
            f"from {PROJECT_NAME}.base_features.serializers.base_serializer import BaseSerializer\n"
            f"from {self.app_name}.models import *\n\n\n"
        ) + model_serializer_script
        self.write_to_file(path, "serializers", script)

    def generate_platform_serializers(self, platform, path):
        model_serializer_script = ""
        for model_name in self.models:
            title_model_name = self.generate_class_name(model_name)
            model_serializer_script += (
                f"class {title_model_name}{self.generate_class_name(platform)}Serializer({title_model_name}BaseSerializer):\n"
                f"    pass\n\n\n"
            )
        script = (
            f"from {self.app_name}.platforms.base.serializers import *\n\n\n"
        ) + model_serializer_script
        self.write_to_file(path, "serializers", script)

    def generate_base_view(self, platform, path):
        model_view_script = ""
        for model_name in self.models:
            title_model_name = self.generate_class_name(model_name)
            model_view_script += (
                f"class {title_model_name}BaseView(BaseAPIView):\n"
                f"    serializer_class = {title_model_name}BaseSerializer\n"
                f"    model_class = {title_model_name}\n\n\n"
            )
        script = (
            f"from {PROJECT_NAME}.base_features.views.base_api_view import BaseAPIView\n"
            f"from {self.app_name}.models import *\n"
            f"from {self.app_name}.platforms.{platform}.serializers import *\n\n\n"
        ) + model_view_script
        self.write_to_file(path, "views", script)

    def generate_platform_views(self, platform, path):
        model_view_script = ""
        for model_name in self.models:
            title_model_name = self.generate_class_name(model_name)
            model_view_script += (
                f"class {title_model_name}{self.generate_class_name(platform)}View({title_model_name}BaseView):\n"
                f"    serializer_class = {title_model_name}{self.generate_class_name(platform)}Serializer\n\n\n"
            )
        script = (
            f"from {self.app_name}.platforms.base.views import *\n"
            f"from {self.app_name}.platforms.{platform}.serializers import *\n\n\n"
        ) + model_view_script
        self.write_to_file(path, "views", script)

    def generate_platform_urls(self, platform, path):
        model_url_script = ""
        for model_name in self.models:
            title_model_name = self.generate_class_name(model_name)
            model_url_script += (
                f"path('{model_name}', {title_model_name}{self.generate_class_name(platform)}View.as_view(), name='{title_model_name}'), \n"
            )
        script = (
            f"from django.urls import path\n"
            f"from {self.app_name}.platforms.{platform}.views import *\n\n\n"
            f"urlpatterns = [\n"
        ) + model_url_script + (
            "\n]"
        )
        self.write_to_file(path, "urls", script)
