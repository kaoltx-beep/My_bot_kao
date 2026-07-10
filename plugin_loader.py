import os
import importlib


PLUGIN_REGISTRY = {}


def load_plugins():
    global PLUGIN_REGISTRY

    PLUGIN_REGISTRY = {}
    folder = "plugins"

    if not os.path.exists(folder):
        return {}

    for file in os.listdir(folder):
        if file.endswith(".py") and file != "__init__.py":
            try:
                name = file[:-3]
                module = importlib.import_module(f"plugins.{name}")

                if hasattr(module, "METADATA") and hasattr(module, "execute"):
                    plugin_name = module.METADATA["name"]

                    PLUGIN_REGISTRY[plugin_name] = {
                        "execute": module.execute,
                        "metadata": module.METADATA
                    }

            except Exception as e:
                print(f"Plugin load error {file}: {e}")

    return {
        name: data["execute"]
        for name, data in PLUGIN_REGISTRY.items()
    }


def get_plugin_info():
    return {
        name: data["metadata"]
        for name, data in PLUGIN_REGISTRY.items()
    }
