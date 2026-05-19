import asyncio
import os
from dotenv import load_dotenv
from telegram import Bot
from db import get_unsummarized_messages, mark_as_summarized
from personas import Persona2_Analyst, Persona3_RiskManager, Persona4_ChiefEditor

load_dotenv('.env.local')

BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
MY_CHAT_ID = os.getenv('TELEGRAM_MY_CHAT_ID')

bot = Bot(token=BOT_TOKEN)

async def run_daily_summary():
    print("일간 요약 파이프라인 시작...")
    
    # 1. DB에서 요약되지 않은 유효 메시지 가져오기
    messages = get_unsummarized_messages()
    
    if not messages:
        print("새로운 메시지가 없습니다. 요약을 건너뜁니다.")
        return
        
    print(f"총 {len(messages)}개의 메시지를 요약합니다.")
    
    # 2. Persona 2: Analyst 분석
    print("Persona 2 (Analyst) 분석 중...")
    analyst_report = await Persona2_Analyst.process(messages)
    
    # 3. Persona 3: Risk Manager 검토
    print("Persona 3 (Risk Manager) 검토 중...")
    risk_report = await Persona3_RiskManager.process(analyst_report)
    
    # 4. Persona 4: Chief Editor 최종 편집
    print("Persona 4 (Chief Editor) 최종 브리핑 작성 중...")
    final_report = await Persona4_ChiefEditor.process(analyst_report, risk_report)
    
    # 5. 사용자에게 전송
    print("개인 텔레그램 봇으로 전송 중...")
    try:
        # 메시지가 너무 길면 텔레그램 제한(4096자)에 걸릴 수 있으므로, 필요시 분할 전송 로직 추가 가능
        await bot.send_message(chat_id=MY_CHAT_ID, text=final_report, parse_mode='Markdown')
        print("전송 완료!")
        
        # 6. 처리된 메시지 상태 업데이트
        message_ids = [m['id'] for m in messages]
        mark_as_summarized(message_ids)
        print("DB 업데이트 완료.")
        
    except Exception as e:
        print(f"요약 리포트 전송 중 오류 발생: {e}")

if __name__ == '__main__':
    asyncio.run(run_daily_summary())
