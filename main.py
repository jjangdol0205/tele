import asyncio
import os
from dotenv import load_dotenv
from telethon import TelegramClient, events
from db import init_db, save_message, get_recent_messages
from personas import Persona1_Filter, Persona5_QnAAgent
from telegram import Bot
from telegram.ext import Application, MessageHandler, filters
from summary_job import run_daily_summary
from apscheduler.schedulers.asyncio import AsyncIOScheduler

# 환경변수 로드
load_dotenv('.env.local')

API_ID = os.getenv('TELEGRAM_API_ID')
API_HASH = os.getenv('TELEGRAM_API_HASH')
BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MY_CHAT_ID = os.getenv('TELEGRAM_MY_CHAT_ID')

# 미디어 다운로드 폴더 생성
if not os.path.exists('downloads'):
    os.makedirs('downloads')

async def main():
    print("텔레그램 투자 정보 요약 에이전트 시작...")
    # DB 초기화
    init_db()
    
    # 봇(수신 및 발신용) 초기화 - python-telegram-bot 유지
    bot = Bot(token=BOT_TOKEN)
    
    async def handle_user_message(update):
        if not update.message or not update.message.chat or update.message.chat.type != 'private':
            return
            
        user_text = update.message.text
        if not user_text:
            return
            
        print(f"[사용자 QnA] 질문 수신: {user_text}")
        
        # 안내 메시지 전송
        processing_msg = await bot.send_message(
            chat_id=update.message.chat.id,
            text="🔍 최근 매크로 정보를 바탕으로 답변을 작성 중입니다. 잠시만 기다려주세요...",
            reply_to_message_id=update.message.message_id
        )
        
        try:
            # 1. DB에서 최근 메시지 50개 가져오기
            recent_msgs = get_recent_messages(50)
            
            # 2. 페르소나5 (QnA) 실행
            answer = await Persona5_QnAAgent.process(user_text, recent_msgs)
            
            # 3. 답변 전송 (기존 안내 메시지 수정)
            await bot.edit_message_text(
                chat_id=update.message.chat.id,
                message_id=processing_msg.message_id,
                text=answer,
                parse_mode='Markdown'
            )
        except Exception as e:
            print(f"QnA 답변 오류: {e}")
            await bot.edit_message_text(
                chat_id=update.message.chat.id,
                message_id=processing_msg.message_id,
                text="답변을 생성하는 도중 오류가 발생했습니다."
            )

    async def poll_bot():
        offset = None
        while True:
            try:
                updates = await bot.get_updates(offset=offset, timeout=10)
                for update in updates:
                    offset = update.update_id + 1
                    await handle_user_message(update)
            except Exception as e:
                print(f"Polling error: {e}")
            await asyncio.sleep(1)

    
    # 스케줄러 설정 (매일 오후 5시에 요약본 자동 실행)
    scheduler = AsyncIOScheduler()
    scheduler.add_job(run_daily_summary, 'cron', hour=17, minute=0)
    scheduler.start()
    print("오후 5시 자동 요약 스케줄러 가동 완료!")
    
    # Telethon Client 초기화
    client = TelegramClient('userbot_session', API_ID, API_HASH)
    
    async def forward_to_user(message_text, original_link=""):
        try:
            text = f"🚨 [긴급/중요 매크로 알림]\n\n{message_text}\n\n원문: {original_link}"
            await bot.send_message(chat_id=MY_CHAT_ID, text=text)
        except Exception as e:
            print(f"포워딩 실패: {e}")

    @client.on(events.NewMessage(func=lambda e: e.is_channel))
    async def handler(event):
        channel_name = getattr(event.chat, 'title', 'Unknown Channel')
        
        # 특정 채널 제외 (블랙리스트)
        if '김진익' in channel_name:
            return
            
        message_text = event.message.message
        message_id = event.message.id
        
        # 메시지 텍스트가 없어도(사진만 있는 경우) 캡션을 읽어옵니다.
        if not message_text and event.message.media:
            message_text = event.message.text
            
        if not message_text:
            return

        channel_username = getattr(event.chat, 'username', None)
        if channel_username:
            link = f"https://t.me/{channel_username}/{message_id}"
        else:
            link = f"Message ID: {message_id} in {channel_name}"
            
        print(f"[{channel_name}] 새 메시지 수신 (길이: {len(message_text)})")

        is_valid, is_urgent, processed_text = await Persona1_Filter.process(message_text)
        
        if not is_valid:
            print(" -> 스팸/개별종목 등으로 분류되어 무시됨.")
            return

        # 유효한 매크로 정보인 경우 사진이 있다면 다운로드
        media_path = None
        if event.message.media:
            print(" -> 미디어 다운로드 중...")
            try:
                media_path = await event.message.download_media('downloads/')
                print(f" -> 미디어 다운로드 완료: {media_path}")
            except Exception as e:
                print(f" -> 미디어 다운로드 실패: {e}")

        # DB에 저장
        save_message(channel_name, processed_text, link, media_path)
        print(" -> 유효한 정보로 DB 저장 완료.")

        if is_urgent:
            print(" -> 🔥 긴급 속보 감지! 즉시 포워딩 진행.")
            await forward_to_user(processed_text, link)
            
    # Userbot 및 Bot 시작
    await client.start()
    print("Userbot 및 QnA 봇 로그인 완료. 메시지 감지 중...")
    
    # 계속 실행 (텔레그램 이벤트와 스케줄러 모두 백그라운드에서 동작)
    await asyncio.gather(
        client.run_until_disconnected(),
        poll_bot()
    )

if __name__ == '__main__':
    asyncio.run(main())
