import plugin_loader


def find_plugin(text):
    text = text.lower()

    plugins = plugin_loader.PLUGINS

    for name, plugin in plugins.items():
        if hasattr(plugin, "METADATA"):
            keywords = plugin.METADATA.get("keywords", [])

            for keyword in keywords:
                if keyword.lower() in text:
                    return name

    return None


def execute_plugin(text):
    plugin_name = find_plugin(text)

    if not plugin_name:
        return None

    plugin = plugin_loader.get_plugin(plugin_name)

    if plugin:
        return plugin.execute()

    return None
