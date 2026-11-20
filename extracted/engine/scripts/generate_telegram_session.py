#!/usr/bin/env python3
"""One-time Telegram login.

Prints a StringSession. Store it as the TELEGRAM_STRING_SESSION secret.
Do not commit it, and do not leave it in your shell history if you can avoid it.

This script is the only step that needs a computer with a browser or a phone.
After the secret is saved, the daily job does not need that computer.
"""

from __future__ import annotations

import asyncio

from telethon import TelegramClient
from telethon.sessions import StringSession


async def main() -> None:
    print("Create an API id and hash at https://my.telegram.org if you do not have them yet.")
    api_id = int(input("Telegram API ID: ").strip())
    api_hash = input("Telegram API hash: ").strip()
    phone = input("Phone number, international format (+60...): ").strip()
    client = TelegramClient(StringSession(), api_id, api_hash)
    await client.start(phone=phone)
    session = client.session.save()
    me = await client.get_me()
    print("\nSigned in as", getattr(me, "username", None) or me.id)
    print("\nTELEGRAM_STRING_SESSION (paste into GitHub Secrets, then close this terminal):\n")
    print(session)
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
