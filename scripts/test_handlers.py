import sys
import pathlib
# ensure project root is on sys.path
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))
from handlers import register_handlers

class MockBot:
    def __init__(self):
        self.msg_handlers=[]
        self.callback_handlers=[]
    def message_handler(self, func=None, **kwargs):
        def decorator(f):
            self.msg_handlers.append(f)
            return f
        return decorator
    def callback_query_handler(self, func=None):
        def decorator(f):
            self.callback_handlers.append(f)
            return f
        return decorator
    def send_message(self, chat_id, text):
        print('SEND', chat_id, text)
    def answer_callback_query(self, id, text):
        print('CALLBACK ANSWER', id, text)
    def edit_message_text(self, text, chat_id, message_id):
        print('EDIT', chat_id, message_id, text)

mb = MockBot()
register_handlers(mb)

class Msg:
    pass

m = Msg()
m.chat = type('C',(),{'id':123})
m.text = 'เช็คแบต'

# call registered handler
mb.msg_handlers[0](m)
import time
# give worker thread time to process
time.sleep(1)
print('done')
