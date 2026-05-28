import asyncio
from app.services.chat_service import chat_service

async def main():
    res = await chat_service.answer("ระบบนี้คืออะไร", None, True)
    print(res.model_dump_json(indent=2))

asyncio.run(main())
