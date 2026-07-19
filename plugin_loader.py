import os
import importlib

PLUGINS = {}

def load_plugins():
    folder = "plugins"

    if not os.path.exists(folder):
        return

    for file in os.listdir(folder):
        if file.endswith(".py") and file != "__init__.py":
            name = file[:-3]

            try:
                module = importlib.import_module(f"plugins.{name}")
                PLUGINS[name] = module
            except Exception as e:
                print(f"Plugin {name} error: {e}")

def get_plugin(name):
    return PLUGINS.get(name)

load_plugins()
