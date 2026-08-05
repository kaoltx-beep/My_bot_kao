import os
import sys
import pathlib
# ensure project root on path
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from run import start_telegram_polling_if_enabled


def main():
    print("--- startup_check ---")
    print("TELEGRAM_TOKEN present:", bool(os.environ.get("TELEGRAM_TOKEN")))
    bot = start_telegram_polling_if_enabled()
    print("start_telegram_polling_if_enabled returned:", type(bot).__name__ if bot else bot)


if __name__ == '__main__':
    main()
