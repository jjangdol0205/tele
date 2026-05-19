import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot, InputMediaPhoto
from db import get_unsummarized_messages, mark_as_summarized
from personas import Persona2_Analyst, Persona3_RiskManager, Persona4_ChiefEditor

load_dotenv('.env.local')

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MY_CHAT_ID = os.getenv('TELEGRAM_MY_CHAT_ID')

bot = Bot(token=BOT_TOKEN)

async def send_long_message(chat_id, text):
    """텔레그램 메시지 길이 제한(4096자)을 회피하기 위해 분할 전송하는 함수"""
    MAX_LENGTH = 4000
    
    if len(text) <= MAX_LENGTH:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode='Markdown')
        return

    # 줄바꿈 기준으로 최대한 안전하게 자르기
    paragraphs = text.split('\n\n')
    chunk = ""
    
    for p in paragraphs:
        if len(chunk) + len(p) + 2 > MAX_LENGTH:
            if chunk:
                await bot.send_message(chat_id=chat_id, text=chunk, parse_mode='Markdown')
            chunk = p
        else:
            if chunk:
                chunk += "\n\n" + p
            else:
                chunk = p
                
    if chunk:
        await bot.send_message(chat_id=chat_id, text=chunk, parse_mode='Markdown')

async def send_media_files(messages):
    """DB에 저장된 미디어(출처 사진)들을 전송하는 함수"""
    for msg in messages:
        media_path = msg.get('media_path')
        link = msg.get('link')
        if media_path and os.path.exists(media_path):
            try:
                caption = f"📸 출처 사진: {link}"
                with open(media_path, 'rb') as f:
                    await bot.send_photo(chat_id=MY_CHAT_ID, photo=f, caption=caption)
            except Exception as e:
                print(f"사진 전송 오류 ({media_path}): {e}")

async def run_daily_summary():
    print("일간 요약 파이프라인 시작...")
    
    messages = get_unsummarized_messages()
    
    if not messages:
        print("새로운 메시지가 없습니다. 요약을 건너뜁니다.")
        return
        
    print(f"총 {len(messages)}개의 메시지를 요약합니다.")
    
    print("Persona 2 (Analyst) 분석 중...")
    analyst_report = await Persona2_Analyst.process(messages)
    
    print("Persona 3 (Risk Manager) 검토 중...")
    risk_report = await Persona3_RiskManager.process(analyst_report)
    
    print("Persona 4 (Chief Editor) 최종 브리핑 작성 중...")
    final_report = await Persona4_ChiefEditor.process(analyst_report, risk_report)
    
    print("개인 텔레그램 봇으로 전송 중...")
    try:
        # 분할 전송
        await send_long_message(MY_CHAT_ID, final_report)
        
        # 원본 사진 전송
        print("원본 사진 전송 중...")
        await send_media_files(messages)
        
        print("전송 완료!")
        
        message_ids = [m['id'] for m in messages]
        mark_as_summarized(message_ids)
        print("DB 업데이트 완료.")
        
    except Exception as e:
        print(f"요약 리포트 전송 중 오류 발생: {e}")

if __name__ == '__main__':
    asyncio.run(run_daily_summary())
