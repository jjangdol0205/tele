import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv('.env.local')

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# 안정적이고 강력한 최신 2.5 Pro 모델 사용
model = genai.GenerativeModel('gemini-2.5-pro')

class Persona1_Filter:
    @staticmethod
    async def process(text: str) -> tuple[bool, bool, str]:
        """
        텍스트를 분석하여 다음을 반환합니다:
        (유효한_투자정보인지, 긴급_속보인지, 정제된_텍스트)
        """
        prompt = f"""
당신은 최고의 거시경제(Macro) 애널리스트를 보좌하는 '정보 필터링 요원'입니다.
다음 텔레그램 메시지가 '의미 있는 거시경제(Macro) 분석 글이나 지표 자료'인지 판단하세요.

[유효한 정보 (is_valid: true) 기준]
- 금리, 인플레이션, 고용지표, 중앙은행(Fed 등) 정책 방향
- 환율, 채권 금리, 원자재 등 글로벌 자산군 동향
- 글로벌 경제 시황 및 매크로 관점의 투자 인사이트

[무시해야 할 정보 (is_valid: false) 기준]
- 특정 개별 기업(종목)의 실적, 호재/악재, 증권사 종목 리포트, 차트 분석 (개별 기업/종목 관련 내용은 무조건 거릅니다)
- 단순 인사말, 스팸, 밈(meme), 무의미한 대화

또한, 이 정보가 '당장 투자자가 실시간으로 알아야 할 초특급 매크로 속보(예: CPI 예상치 크게 하회, 금리 기습 인하 등)'라면 is_urgent를 true로 설정하세요.

메시지:
\"\"\"
{text}
\"\"\"

출력은 반드시 다음 JSON 포맷만 반환하세요:
{{
  "is_valid": true/false,
  "is_urgent": true/false,
  "cleaned_text": "원문에서 노이즈를 제거하고 매크로 핵심만 간결하게 다듬은 텍스트 (is_valid가 false라면 비워두세요)"
}}
"""
        try:
            response = model.generate_content(prompt)
            result_text = response.text.strip()
            
            # 간단한 JSON 파싱 (실제 배포시엔 JSON 파서와 예외처리 강화 필요)
            import json
            
            # 마크다운 백틱 제거
            if result_text.startswith("```json"):
                result_text = result_text[7:-3]
            elif result_text.startswith("```"):
                result_text = result_text[3:-3]
                
            data = json.loads(result_text)
            return data.get("is_valid", False), data.get("is_urgent", False), data.get("cleaned_text", text)
        except Exception as e:
            print(f"Persona 1 처리 오류: {e}")
            # 에러 발생시 기본적으로 보수적으로 처리 (버리지 않고 저장하되 긴급은 아님)
            return True, False, text

class Persona2_Analyst:
    @staticmethod
    async def process(messages: list) -> str:
        """수집된 메시지들을 분석하여 투자 아이디어 도출"""
        if not messages:
            return "분석할 데이터가 없습니다."
            
        combined_text = "\n\n".join([f"- [{m['channel_name']}] {m['content']}" for m in messages])
        
        prompt = f"""
당신은 월스트리트 최고의 '거시경제 분석가(Macro Analyst)'입니다.
오늘 수집된 다음 매크로 정보들을 읽고, 글로벌 자산 시장에 미치는 긍정적인 시그널이나 주요 트렌드를 추출하세요.

수집된 정보:
{combined_text}

출력 포맷 (마크다운):
## 🧠 매크로 분석가 뷰
- **[주요 지표/정책]**: 현황 및 자산 시장(주식/채권/환율)에 미치는 긍정적 영향
- **[글로벌 경제 트렌드]**: 거시적 관점의 투자 아이디어
"""
        response = model.generate_content(prompt)
        return response.text

class Persona3_RiskManager:
    @staticmethod
    async def process(analyst_report: str) -> str:
        """분석가의 리포트를 비판적으로 검토"""
        prompt = f"""
당신은 보수적이고 꼼꼼한 '매크로 리스크 관리자(Risk Manager)'입니다.
다음 거시경제 분석가의 뷰를 읽고, 비판적인 시각에서 숨겨진 매크로 리스크(인플레이션 재발, 경기 침체, 지정학적 위기 등)를 지적하세요.

분석가 뷰:
{analyst_report}

출력 포맷 (마크다운):
## 🛡️ 매크로 리스크 검토
- **[주요 리스크 요인]**: (비판적 의견 및 잠재적 시장 충격)
"""
        response = model.generate_content(prompt)
        return response.text

class Persona4_ChiefEditor:
    @staticmethod
    async def process(analyst_report: str, risk_report: str) -> str:
        """최종 요약 리포트 작성"""
        prompt = f"""
당신은 글로벌 헤지펀드의 '투자 전략 편집장(Chief Editor)'입니다.
아래 분석가의 뷰와 리스크 관리자의 뷰를 종합하여, 매크로 투자자가 5분 만에 읽을 수 있는 **'오늘의 글로벌 매크로 브리핑'**을 작성하세요.
직관적이고 깔끔한 마크다운 형식을 사용하세요.

[매크로 분석가 뷰]
{analyst_report}

[리스크 관리자 뷰]
{risk_report}

출력 포맷 예시:
# 🌍 오늘의 글로벌 매크로 브리핑

## 📈 주요 매크로 동향 (기회 요인)
(내용)

## 📉 시장 하방 리스크 (주의 요인)
(내용)

## 💡 편집장 자산배분 전략
(주식, 채권, 현금 등 자산군 비중 조절에 대한 요약)
"""
        response = model.generate_content(prompt)
        return response.text
