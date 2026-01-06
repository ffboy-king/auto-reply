from telethon import TelegramClient, events
from telethon.tl.types import UserStatusOnline
import asyncio

# --- CONFIGURATION ---
# my.telegram.org se mili hui details yahan daalein
API_ID = 38764626  # Apna API ID yahan likhein
API_HASH = '1935b1ebddd02fdbef1db36957eb4848' 
# ---------------------

client = TelegramClient('professional_session', API_ID, API_HASH)

@client.on(events.NewMessage(incoming=True))
async def auto_reply_handler(event):
    # Sirf Private messages ke liye
    if event.is_private:
        me = await client.get_me()

        # Check: Kya aap (Owner) online hain?
        # Agar aap online nahi hain (Offline/Recent), tabhi reply jayega
        if not isinstance(me.status, UserStatusOnline):
            
            # Professional Message Template
            reply_text = (
                "**Greetings!**\n\n"
                "Thank you for reaching out. I am currently **away or offline**.\n"
                "Your message is important, and I will get back to you as soon as I return.\n\n"
                "For any urgent matters, please leave your specific query below.\n\n"
                "*Best Regards,*\n"
                "Auto-Response System"
            )

            # Wait for 3 seconds to make it look natural
            await asyncio.sleep(3)
            await event.reply(reply_text)

print("✅ Professional Auto-Reply is active...")
client.start()
client.run_until_disconnected()
