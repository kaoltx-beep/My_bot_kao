import os
import importlib


def load_plugins():
    action_map = {}
    folder = "plugins"

    if not os.path.exists(folder):
        return action_map

    for file in os.listdir(folder):
        if file.endswith(".py") and file != "__init__.py":
            try:
                name = file[:-3]
                module = importlib.import_module(f"plugins.{name}")

                if hasattr(module, "PLUGIN_NAME") and hasattr(module, "execute"):
                    action_map[module.PLUGIN_NAME] = module.execute

            except Exception as e:
                print(f"Plugin load error {file}: {e}")

    return action_map
