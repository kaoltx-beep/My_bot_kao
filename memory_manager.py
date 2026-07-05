memory = []

def save_memory(user, bot):
    memory.append((user, bot))
    if len(memory) > 20:
        memory.pop(0)

def get_memory(limit=5):
    return memory[-limit:]