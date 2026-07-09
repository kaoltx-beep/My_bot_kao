PLUGIN_NAME = "battery"

import device_actions


def execute(context=None):
    return device_actions.check_battery()
