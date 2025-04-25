import os


class BaseGenerator:
    def __init__(self, app_name: str, platforms: list, models: list = None):
        self.app_name = app_name
        self.platforms = platforms
        self.platforms.append("base")
        self.models = models if models else [app_name]

    def generate(self):
        pass

    def generate_class_name(self, name):
        words = name.split("_")
        return "".join([word.capitalize() for word in words])

    def write_to_file(self, path, file_name, script):
        with open(f"{path}/{file_name}.py", "w") as f:
            f.write(script)

    def create_python_folder(self, folder_name, path=None):
        if path:
            path = f"{path}/{folder_name}"
        else:
            path = f"{folder_name}"
        os.makedirs(f"{path}", exist_ok=True)
        # add __init__.py file
        with open(f"{path}/__init__.py", "w") as f:
            f.write("")
