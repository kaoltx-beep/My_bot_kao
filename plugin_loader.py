import os
import importlib

PLUGINS = {}


def load_plugins():
    global PLUGINS

    plugin_folder = "plugins"

    for file in os.listdir(plugin_folder):

        if not file.endswith(".py"):
            continue

        if file == "__init__.py":
            continue

        name = file[:-3]

        try:
            module = importlib.import_module(
                f"plugins.{name}"
            )

            if hasattr(module, "METADATA"):
                plugin_name = module.METADATA.get("name")
                if plugin_name:
                    PLUGINS[plugin_name] = module
                    continue

            if hasattr(module, "PLUGIN_NAME"):
                PLUGINS[module.PLUGIN_NAME] = module

        except Exception as e:
            print(
                f"Plugin load error {name}:",
                e
            )

    return PLUGINS



def get_plugin(name):
    return PLUGINS.get(name)



def get_plugin_info():

    result = {}

    for name, plugin in PLUGINS.items():

        if hasattr(plugin, "METADATA"):
            result[name] = plugin.METADATA

    return result
