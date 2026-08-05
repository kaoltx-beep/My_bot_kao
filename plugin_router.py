import plugin_loader


def find_plugin(text):
    text = text.lower()
    plugins = plugin_loader.PLUGINS

    for name, plugin in plugins.items():
        plugin_key = name.lower()

        if plugin_key and plugin_key in text:
            return name

        keywords = []
        if hasattr(plugin, "METADATA"):
            keywords.extend(plugin.METADATA.get("keywords", []))

        if hasattr(plugin, "PLUGIN_NAME"):
            keywords.append(plugin.PLUGIN_NAME)

        for keyword in keywords:
            if keyword and keyword.lower() in text:
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


def list_plugins():
    result = {}

    for name, plugin in plugin_loader.PLUGINS.items():
        if hasattr(plugin, "METADATA"):
            result[name] = plugin.METADATA

    return result


def find_plugin_with_ai(text, ai_function):
    plugin = find_plugin(text)

    if plugin:
        return plugin

    plugins = list_plugins()

    result = ai_function(
        f"""
ข้อความผู้ใช้:
{text}

เลือก Plugin ที่เหมาะสมจากรายการนี้:
{plugins}

ตอบเฉพาะชื่อ Plugin เท่านั้น
"""
    )

    # รองรับกรณี AI ส่งกลับเป็น JSON dict
    if isinstance(result, dict):
        result = result.get("reply", "")

    # กัน error ถ้าไม่ใช่ข้อความ
    if not isinstance(result, str):
        return None

    result = result.strip().lower()

    for name in plugins:
        if name.lower() in result:
            return name

    return None
