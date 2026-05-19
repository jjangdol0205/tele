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
- 금리, 인플레이션, 고용지표, 연준(Fed) 등 중앙은행 정책 방향
- 환율, 국채 금리, 원자재 등 글로벌 자산군 동향 및 경제 시황
- (중요) 메시지 내에 거시경제(Macro) 관련 내용이 조금이라도 포함되어 있다면 무조건 유효한 정보로 간주합니다!

[무시해야 할 정보 (is_valid: false) 기준]
- "오직" 특정 개별 기업(종목)의 실적, 주가 차트, 인사말, 광고, 스팸만 있는 경우 (이때만 버리세요)

[데이터 정제(cleaned_text) 지시사항]
- 메시지에 매크로(Macro) 정보와 개별 종목 뉴스가 섞여 있다면, 종목 뉴스는 삭제하고 매크로 정보만 추출해서 `cleaned_text`에 담아주세요.
- 전체를 버리지 마세요! 매크로 인사이트가 한 줄이라도 있으면 살려야 합니다.

또한, 이 정보가 '당장 투자자가 실시간으로 알아야 할 초특급 매크로 속보'라면 is_urgent를 true로 설정하세요.

메시지:
\"\"\"
{text}
\"\"\"

출력은 반드시 다음 JSON 포맷만 반환하세요:
{{
  "is_valid": true/false,
  "is_urgent": true/false,
  "cleaned_text": "원문에서 노이즈와 개별 종목 뉴스를 제거하고 매크로 핵심만 남긴 텍스트"
}}
"""
        try:
            response = await model.generate_content_async(prompt)
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
        try:
            response = await model.generate_content_async(prompt)
            return response.text
        except ValueError:
            return "분석 중 안전성 필터에 의해 차단되었거나 응답이 비어있습니다."
        except Exception as e:
            return f"분석 오류 발생: {e}"

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
        try:
            response = await model.generate_content_async(prompt)
            return response.text
        except ValueError:
            return "리스크 검토 중 안전성 필터에 의해 차단되었거나 응답이 비어있습니다."
        except Exception as e:
            return f"리스크 검토 오류 발생: {e}"

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
        try:
            response = await model.generate_content_async(prompt)
            return response.text
        except ValueError:
            return "최종 브리핑 작성 중 안전성 필터에 의해 차단되었거나 응답이 비어있습니다."
        except Exception as e:
            return f"최종 브리핑 오류 발생: {e}"

class Persona5_QnAAgent:
    @staticmethod
    async def process(question: str, messages: list) -> str:
        """사용자의 질문에 대해 수집된 메시지를 바탕으로 답변 생성"""
        if not messages:
            context = "최근 수집된 매크로 정보가 없습니다."
        else:
            context = "\n\n".join([f"- [{m['channel_name']}] {m['content']}" for m in messages])
            
        prompt = f"""
당신은 사용자의 텔레그램 개인 비서이자 친절한 대화 상대입니다.
아래에 제공된 '최근 수집된 텔레그램 메시지' 내용을 바탕으로 사용자의 질문에 편하고 자연스럽게 대답해주세요.

- 반드시 거시경제(Macro) 시황 얘기만 할 필요는 없습니다. 일상적인 질문이나 일반적인 대화에도 친근하게 답해주세요.
- 사용자가 질문한 내용이 제공된 정보(DB) 안에 있다면, 그 내용을 바탕으로 유용하게 대답해주세요.
- 만약 제공된 정보에 없는 내용이라면 "수집된 정보에서는 해당 내용을 찾을 수 없네요"라고 편하게 얘기한 뒤, 당신이 알고 있는 일반적인 지식으로 부드럽게 대화를 이어가면 됩니다.
- 말투는 딱딱한 '전문가'나 '로봇'처럼 하지 말고, 친하고 싹싹한 비서처럼 편안한 어투(해요체 등)를 사용해주세요. 마크다운도 보기 좋게 적절히 써주세요.

[최근 수집된 메시지 정보]
{context}

[사용자 질문]
{question}
"""
        try:
            response = await model.generate_content_async(prompt)
            return response.text
        except ValueError:
            return "안전성 필터에 의해 답변이 차단되었거나 빈 응답을 받았습니다. 다른 질문을 해주세요."
        except Exception as e:
            return f"답변 생성 오류 발생: {e}"
