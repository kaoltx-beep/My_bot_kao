PLUGIN_NAME = "check_battery"


def execute():
    import device_actions
    return device_actions.check_battery()
