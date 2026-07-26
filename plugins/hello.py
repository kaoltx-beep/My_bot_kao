def execute_hello(command):
    if command.lower() == 'สวัสดีจาร์วิส':
        return 'สวัสดี นายท่าน'
    else:
        if command.lower().startswith('สวัสดี'):
            var = command.lower()
            var = var[5:]
            return 'สวัสดี ' + var.upper() + ' นายท่าน'
    return ''