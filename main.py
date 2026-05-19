import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from db import init_db, save_message
from personas import Persona1_Filter
from telegram import Bot

# 환경변수 로드
load_dotenv('.env.local')  # 사용자님 설정에 맞게 .env.local 로딩

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MY_CHAT_ID = os.getenv('TELEGRAM_MY_CHAT_ID')

async def main():
    print("텔레그램 투자 정보 요약 에이전트 시작...")
    # DB 초기화
    init_db()
    
    # 봇 초기화 (async context 내부에서 수행)
    bot = Bot(token=BOT_TOKEN)
    
    # Telethon Client 초기화 (async context 내부에서 수행해야 Python 3.14+ 오류 방지)
    client = TelegramClient('userbot_session', API_ID, API_HASH)
    
    async def forward_to_user(message_text, original_link=""):
        """중요한 메시지를 봇을 통해 사용자에게 즉시 전송"""
        try:
            text = f"🚨 [긴급/중요 알림]\n\n{message_text}\n\n원문: {original_link}"
            await bot.send_message(chat_id=MY_CHAT_ID, text=text)
        except Exception as e:
            print(f"포워딩 실패: {e}")

    @client.on(events.NewMessage(func=lambda e: e.is_channel))
    async def handler(event):
        channel_name = getattr(event.chat, 'title', 'Unknown Channel')
        message_text = event.message.message
        message_id = event.message.id
        
        # 채널의 username이나 id를 통해 메시지 링크 생성 시도
        channel_username = getattr(event.chat, 'username', None)
        if channel_username:
            link = f"https://t.me/{channel_username}/{message_id}"
        else:
            link = f"Message ID: {message_id} in {channel_name}"

        if not message_text:
            return
            
        print(f"[{channel_name}] 새 메시지 수신 (길이: {len(message_text)})")

        # Persona 1: 필터링 및 긴급 판별
        is_valid, is_urgent, processed_text = await Persona1_Filter.process(message_text)
        
        if not is_valid:
            print(" -> 스팸/노이즈로 분류되어 무시됨.")
            return

        # 유효한 정보라면 DB에 저장 (나중에 Persona 2,3,4가 요약할 때 사용)
        save_message(channel_name, processed_text, link)
        print(" -> 유효한 정보로 DB 저장 완료.")

        # 긴급/중요 정보라면 즉시 포워딩
        if is_urgent:
            print(" -> 🔥 긴급/중요 정보 감지! 즉시 포워딩 진행.")
            await forward_to_user(processed_text, link)
            
    # Userbot 시작
    await client.start()
    print("Userbot 로그인 완료. 채널 메시지 감지 중...")
    
    # 계속 실행
    await client.run_until_disconnected()

if __name__ == '__main__':
    asyncio.run(main())
