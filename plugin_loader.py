import os
import importlib


PLUGINS = {}


def load_plugins():

    plugin_folder = "plugins"

    for file in os.listdir(plugin_folder):

        if file.endswith(".py") and file != "__init__.py":

            name = file[:-3]

            module = importlib.import_module(
                f"plugins.{name}"
            )

            if hasattr(module, "PLUGIN_NAME"):

                PLUGINS[module.PLUGIN_NAME] = module


    return PLUGINS


def get_plugin(name):

    return PLUGINS.get(name)
