import os
import json
import time # Added for sleep
import sys
from dotenv import load_dotenv

# Load dependencies
# Imports moved to inside class for lazy loading
# import google.generativeai as genai
# from langchain_openai import ChatOpenAI
# from langchain_core.prompts import PromptTemplate
# from langchain_core.output_parsers import StrOutputParser

# Ollama/LocalBrain removed — system uses Gemini AI only
# local_brain.py kept as stub for backward compatibility

# Import News Fetcher (Always)
try:
    sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../internet_gathering")))
    from news_fetcher import NewsFetcher
except ImportError:
    print("Warning: Could not import NewsFetcher.")
    class NewsFetcher: # Mock fallback to prevent crash
        def get_latest_headlines(self): return []

# Load environment variables
load_dotenv(dotenv_path=os.path.abspath(os.path.join(os.path.dirname(__file__), "../../Shared_Data/configs/.env")))

class SpidyBrain:
    def __init__(self, mode="hybrid"):
        """
        Initialize the Spidy Brain.
        :param mode: 'hybrid' (uses both), 'fast' (Gemini Flash), 'smart' (GPT-4o)
        """
        self.mode = mode
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.google_api_key = os.getenv("GOOGLE_API_KEY")

        # Initialize LLMs
        self.llm_gpt = None
        self.openai_client = None
        if self.openai_api_key:
            from langchain_openai import ChatOpenAI
            from openai import OpenAI
            self.llm_gpt = ChatOpenAI(model="gpt-4o", temperature=0)
            self.openai_client = OpenAI(api_key=self.openai_api_key)
        
        # Configure Gemini directly
        self.gemini_models = {}
        if self.google_api_key:
            try:
                import google.generativeai as genai
                genai.configure(api_key=self.google_api_key)
                # Primary: Fastest
                self.gemini_models["flash"] = genai.GenerativeModel('gemini-1.5-flash-latest')
                # Backup: More Capable / Different Quota
                self.gemini_models["pro"] = genai.GenerativeModel('gemini-1.5-pro-latest')
            except ImportError:
                 sys.stderr.write("[WARN] Google GenAI Library not found. Install `google-generativeai`.\n")
            except Exception as e:
                 sys.stderr.write(f"[WARN] Failed to initialize Gemini: {e}\n")
        
        self.news_fetcher = NewsFetcher()

        # Warn if no AI backend at all
        if not self.llm_gpt and not self.gemini_models:
            sys.stderr.write("[WARN] No API Keys found. Set GOOGLE_API_KEY or OPENAI_API_KEY in .env\n")

    def _generate_with_retry(self, prompt_text, image=None, model_mode="turbo"):
        """
        Attempts to generate content with fallback logic.
        UPGRADE 5: model_mode='turbo' uses Flash first; 'deep' skips to Pro first.
        """
        # Ordered list of models based on mode
        if model_mode == "deep":
            model_order = ["pro", "flash"]
        else:
            model_order = ["flash", "pro"]

        for model_key in model_order:
            if model_key in self.gemini_models:
                try:
                    if image:
                        response = self.gemini_models[model_key].generate_content([prompt_text, image])
                    else:
                        response = self.gemini_models[model_key].generate_content(prompt_text)
                    return response.text
                except Exception as e:
                    if "429" in str(e) or "ResourceExhausted" in str(e):
                        sys.stderr.write(f"[WARN] Gemini {model_key} Rate Limit (429). Trying next...\n")
                    else:
                        sys.stderr.write(f"[WARN] Gemini {model_key} Error: {e}\n")

        # 2. Last Resort: GPT if available
        if self.llm_gpt:
             try:
                from langchain_core.prompts import PromptTemplate
                from langchain_core.output_parsers import StrOutputParser
                
                if image:
                     prompt_text += "\n[Image attached — GPT Vision not configured]"
                
                prompt = PromptTemplate.from_template(prompt_text)
                chain = prompt | self.llm_gpt | StrOutputParser()
                return chain.invoke({})
             except Exception as e:
                 sys.stderr.write(f"[WARN] GPT Error: {e}\n")

        sys.stderr.write("[ERROR] All AI backends exhausted. Set GOOGLE_API_KEY in .env\n")
        return None

    def _get_system_prompt(self, persona="cyberpunk", user_query=""):
        """Returns the system prompt based on the selected persona."""
        
        base_instructions = """
                INSTRUCTIONS:
                1. Classify the user's intent into one of the categories below.
                2. For 'CHAT' and 'TRADING_UPDATE', provide a DETAIL-RICH, HELPFUL response.
                3. NEVER be rude or dismissive. Be helpful first.
                4. USE MARKDOWN (Bold, Lists, Code Blocks) to make your output beautiful.
                5. SUGGEST A VISUAL THEME based on the conversation context.
        """
        
        categories = """
                CATEGORIES:
                1. 'AUTOMATION': User wants to open apps, send messages, or control the PC.
                2. 'SCAN_SCREEN': User asks to "read", "scan", or "look at" the screen.
                3. 'VOICE': User mentions "speak", "listen", or voice commands.
                4. 'TRADING_UPDATE': Questions about stocks, crypto, MT5, or strategy.
                5. 'GENERATE_IMAGE': User asks to "generate", "create", "draw" an image/picture/logo.
                6. 'CHAT': General questions, coding help, conversational OR describing an attached image.
                
                Query: {user_query}
                
                FORMAT RULES:
                - If Category is 'CHAT': 'details' should be your full, well-formatted answer.
                - If Category is 'AUTOMATION': 'details' should be the specific action (e.g., "open spotify").
                - If Category is 'GENERATE_IMAGE': 'details' should be the VISUAL PROMPT (e.g., "cyberpunk spider logo").
                - **CRITICAL**: If the user purely describes a visual scene (e.g., "a red car", "sunset over ocean") WITHOUT asking a question, assume intent is 'GENERATE_IMAGE'.
                - RETURN JSON ONLY: {{"intent": "CATEGORY", "details": "response_or_info", "action_needed": "true/false", "theme": "suggested_theme"}}
        """

        if persona == "corporate":
            intro = """
                You are Spidy, a top-tier Financial Analyst and Executive Assistant.
                ROLE: Professional, Concise, Business-oriented.
                TONE: Formal, Data-driven, Polite. No slang.
            """
        elif persona == "nature":
            intro = """
                You are Spidy, a peaceful AI connected to the natural world.
                ROLE: Calm, Grounded, Organic.
                TONE: Soothing, Metaphorical (using nature analogies), Gentle.
            """
        elif persona == "retro":
            intro = """
                You are Spidy, a 90s Hacker/Gamer AI.
                ROLE: Radical, Nostalgic, pop-culture savvy.
                TONE: Energetic, using 90s slang (Rad, Tubular), referencing retro tech.
            """
        elif persona == "minimal":
             intro = """
                You are Spidy.
                ROLE: Pure Logic Engine.
                TONE: Robotic, Extremely Concise, Direct. No filler.
            """
        else: # Default Cyberpunk
            intro = """
                You are Spidy, a highly advanced AI system with a Cyberpunk personality. 
                ROLE: You are an expert assistant for Automation, Trading, and General Knowledge.
                TONE: Professional, Witty, Intelligent, and "Cool". Use "🕷️" occasionally.
            """

        return f"{intro}\n{base_instructions}\n{categories}".format(user_query=user_query)

    def decide_intent(self, user_query, image_data=None, persona="cyberpunk", model_mode="turbo"):
        """Classifies intent using available models with fallback.
        UPGRADE 5: model_mode is forwarded to _generate_with_retry.
        """
        
        # Process Image if present
        processed_image = None
        if image_data:
            print(f"[DEBUG] Received image data of length: {len(image_data)}")
            try:
                import base64
                import io
                from PIL import Image
                
                # Remove header if present (e.g., "data:image/jpeg;base64,")
                if "base64," in image_data:
                    image_data = image_data.split("base64,")[1]
                
                image_bytes = base64.b64decode(image_data)
                processed_image = Image.open(io.BytesIO(image_bytes))
                print("[DEBUG] Image successfully processed into PIL Object")
            except Exception as e:
                sys.stderr.write(f"[ERROR] Failed to process image: {e}\n")
                return {"intent": "CHAT", "details": f"Error: Failed to process attached image. ({str(e)})", "action_needed": "false"}
        else:
            print("[DEBUG] No image data received in decide_intent")

        # Prepare Prompt based on presence of image
        if processed_image:
             print("[DEBUG] Using Image Analysis Prompt")
             prompt_text = f"""
                You are Spidy.
                INSTRUCTION: Analyze the attached image in detail.
                User Query: {user_query}
                Persona: {persona} (Adopt this persona for the analysis).
                
                If the user asks to describe it, provide a detailed description.
                If the user asks a specific question about it, answer that question.
                
                RETURN JSON format generally for consistency, but prioritize the 'details' field with your analysis.
                FORMAT: {{"intent": "CHAT", "details": "YOUR IMPRESSIVE ANALYSIS HERE", "action_needed": "false", "theme": "{persona}"}}
             """
        else:
            print(f"[DEBUG] Using Standard Text Prompt with Persona: {persona}")
            
            # --- CONTEXT INJECTION START ---
            market_context = ""
            if "market" in user_query.lower() or "price" in user_query.lower() or "eurusd" in user_query.lower() or "trend" in user_query.lower():
                 market_context = self._fetch_market_context()
                 if market_context:
                     market_context = f"\n\n[REAL-TIME MARKET DATA]:\n{market_context}\n\n"
                 
                 news_context = self._fetch_news_context()
                 if news_context:
                      if not market_context: market_context = ""
                      market_context += f"\n[GLOBAL NEWS SENTIMENT]:\n{news_context}\n\n"
                      
                      # --- AUTO-SYNC SENTIMENT TO BRIDGE ---
                      try:
                          # Simple keyword analysis of the context to find aggregate sentiment
                          # In a real system, the LLM should decide this, but for now we do a quick heuristic check
                          # passed from the news_fetcher headers
                          agg_sentiment = "NEUTRAL"
                          if "(positive)" in news_context: agg_sentiment = "BULLISH"
                          elif "(negative)" in news_context: agg_sentiment = "BEARISH"
                          
                          # Push to Bridge
                          import requests
                          mt5_url = os.getenv("MT5_SERVER_URL", "http://localhost:8000")
                          requests.post(f"{mt5_url}/set_sentiment", json={"sentiment": agg_sentiment}, timeout=1)
                      except:
                          pass
                      # -------------------------------------
            # --- CONTEXT INJECTION END ---

            prompt_text = self._get_system_prompt(persona, user_query) + market_context
        
        # --- HEURISTIC OVERRIDE START ---
        decision = None
        
        # Force GENERATE_IMAGE if keywords are present, skipping LLM uncertainty
        uq_lower = user_query.lower()
        if ("generate" in uq_lower or "create" in uq_lower or "draw" in uq_lower) and ("image" in uq_lower or "picture" in uq_lower or "photo" in uq_lower):
            print("[DEBUG] Heuristic Override: Detected Image Generation Request")
            decision = {"intent": "GENERATE_IMAGE", "details": user_query, "action_needed": "true", "theme": persona}
        # --- HEURISTIC OVERRIDE END ---

        if not decision:
            try:
                # UPGRADE 5: Pass model_mode so turbo → Flash, deep → Pro
                response_text = self._generate_with_retry(prompt_text, image=processed_image, model_mode=model_mode)
                
                if not response_text:
                    # Total Failure -> Mock
                    decision = self._mock_decision(user_query)
                else:
                    # Improved JSON Extraction
                    import re
                    # Match content between first { and last } (DOTALL to span newlines)
                    match = re.search(r'\{.*\}', response_text, re.DOTALL)
                    
                    if match:
                         clean_json_str = match.group(0)
                         try:
                             decision = json.loads(clean_json_str)
                         except json.JSONDecodeError:
                             sys.stderr.write(f"[WARN] JSON decode failed even after regex extraction.\n")
                             # Fallback
                             decision = {"intent": "CHAT", "details": response_text, "action_needed": "false", "theme": "cyberpunk"}
                    else:
                         # No JSON structure found
                         decision = {"intent": "CHAT", "details": response_text, "action_needed": "false", "theme": "cyberpunk"}
                
            except Exception as e:
                sys.stderr.write(f"Intent Decision Failed completely: {e}\n")
                # If all else fails, use the raw query as details or mock
                decision = {"intent": "CHAT", "details": str(e) if str(e) else user_query, "action_needed": "false", "theme": "cyberpunk"}

        # --- AUTO-EXECUTE AUTOMATION ---
        print(f"[DEBUG] DECIDED INTENT: {decision.get('intent')}")
        intent = decision.get("intent")
        if intent == "AUTOMATION":
            self._execute_automation(decision.get("details"))
            decision["execution_status"] = "Triggered App Launcher"
        elif intent == "SCAN_SCREEN":
            self._execute_vision()
            decision["execution_status"] = "Triggered Vision Scanner"
        elif intent == "VOICE":
            self._execute_voice(decision.get("details"))
            decision["execution_status"] = "Triggered Voice Module"
        elif intent == "TRADING_UPDATE":
            result_msg = self._execute_trading(decision.get("details"))
            decision["execution_status"] = result_msg
            # Trading usually implies corporate or cyber
            if decision.get("theme") == "cyberpunk": 
                 decision["theme"] = "corporate"
        elif intent == "GENERATE_IMAGE":
            prompt = decision.get("details", user_query)
            try:
                # Use Pollinations.ai (Cloud) - Fast & Reliable
                import urllib.parse
                encoded_prompt = urllib.parse.quote(prompt)
                # Switch to FLUX model for Photorealism & Sharpness. 
                # Native 1024x1024 prevents upscaling blur. 'nologo' & 'enhance' kept.
                image_url = f"https://image.pollinations.ai/prompt/{encoded_prompt}?model=flux&width=1024&height=1024&nologo=true&enhance=true"
                
                decision["details"] = image_url
                decision["alt"] = prompt
                decision["execution_status"] = "Generated Image (Pollinations Cloud)"
            except Exception as e:
                sys.stderr.write(f"[ERROR] Image Generation Crashed: {e}\n")
                decision["details"] = f"Image Generation Failed: {e}"
                decision["execution_status"] = "Generation Error"
            
        return decision

    def listen_to_user(self):
        """Directly triggers the listening mode."""
        return self._execute_voice(None)

    def _execute_trading(self, details):
        """Sends a trade signal to the MT5 Bridge."""
        try:
            import requests
            mt5_url = os.getenv("MT5_SERVER_URL", "http://localhost:8000")
            bridge_headers = {"X-API-KEY": os.getenv("SPIDY_API_KEY", "spidy_secure_123")}
            
            details_str = str(details).lower()
            
            # Check for "CLOSE ALL" or "TAKE PROFIT" intent
            if "close all" in details_str or "take profit" in details_str or "take all profit" in details_str or "secure profit" in details_str or "secure my profit" in details_str:
                profitable_only = "profit" in details_str or "secure" in details_str # If they say "take profit", only close wealthy ones
                
                payload = {"profitable_only": profitable_only}
                try:
                    response = requests.post(f"{mt5_url}/close_all_trades", json=payload, headers=bridge_headers)
                    if response.status_code == 200:
                        data = response.json()
                        return f"Executed Close All. Closed {data.get('closed', 0)} trades."
                    else:
                        return f"Close All Error: {response.text}"
                except Exception as e:
                      return f"Connection Failed: {e}"

            # Check for "TIGHTEN STOPS" or "REDUCE RISK"
            if "tighten" in details_str or "reduce risk" in details_str or "guard profit" in details_str:
                try:
                    response = requests.post(f"{mt5_url}/tighten_stops", headers=bridge_headers)
                    if response.status_code == 200:
                        return "Profit Guardian Activated: Stops Tightened to 1.2x ATR."
                    else:
                        return f"Error Tightening Stops: {response.text}"
                except Exception as e:
                    return f"Connection Failed: {e}"
            
            # Check for "RESET RISK"
            if "reset risk" in details_str or "normal stops" in details_str:
                try:
                    requests.post(f"{mt5_url}/reset_stops", headers=bridge_headers)
                    return "Risk settings reset to Standard (2.0x ATR)."
                except:
                    return "Failed to reset risk."

            # Check for SENTIMENT / BIAS
            if "sentiment" in details_str or "market mood" in details_str or "bias" in details_str:
                new_sentiment = "NEUTRAL"
                if "bull" in details_str or "long" in details_str: new_sentiment = "BULLISH"
                elif "bear" in details_str or "short" in details_str: new_sentiment = "BEARISH"
                
                try:
                    payload = {"sentiment": new_sentiment}
                    response = requests.post(f"{mt5_url}/set_sentiment", json=payload, headers=bridge_headers)
                    if response.status_code == 200:
                        return f"Sentiment Updated to {new_sentiment}."
                    else:
                        return f"Sentiment Error: {response.text}"
                except Exception as e:
                    return f"Connection Failed: {e}"

            # Improved Parsing Logic using Regex
            import re
            
            # Default
            action = "ORDER"
            symbol = "EURUSD"
            volume = 0.01

            # Detect Action
            if "buy" in details_str: action = "BUY"
            elif "sell" in details_str: action = "SELL"
            
            # Detect Symbol (Looking for patterns like EURUSD, XAUUSD of 6 chars)
            # Simple heuristic: Look for common pairs or 6-letter uppercase words in the original details (not lower)
            # But here details_str is lower. Let's use the raw details if possible, but details_str is fine for known list.
            common_pairs = ["eurusd", "gbpusd", "usdjpy", "xauusd", "btcusd", "ethusd", "audusd", "usdcad", "sp500", "nas100", "us30"]
            for pair in common_pairs:
                if pair in details_str:
                    symbol = pair.upper()
                    break
            
            # Detect Volume (0.01, 0.1, 1.0 etc)
            # Regex for float
            vol_match = re.search(r'\b0\.\d+\b|\b1\.\d+\b', details_str)
            if vol_match:
                try:
                    volume = float(vol_match.group())
                except:
                    pass
            
            payload = {"action": action, "symbol": symbol, "volume": volume, "details": details}
            
            try:
                response = requests.post(f"{mt5_url}/trade", json=payload, headers=bridge_headers)
                if response.status_code == 200:
                    return f"Trade Signal Sent: {response.json()}"
                else:
                    return f"Trade Error: {response.text}"
            except requests.exceptions.ConnectionError:
                return "Trade Error: MT5 Bridge not running."
                
        except Exception as e:
            return f"Trade Execution Failed: {e}"

    def _execute_automation(self, details):
        """Calls the launcher.py script."""
        try:
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                                       "../../Trading_Backend/automation_engine/app_control/launcher.py"))
            import subprocess
            subprocess.Popen([sys.executable, script_path, details])
        except Exception as e:
            sys.stderr.write(f"Failed to execute automation: {e}\n")

    def _execute_vision(self):
        """Calls the ocr_scanner.py script and returns the detected text."""
        try:
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                                       "../../Trading_Backend/automation_engine/screen_vision/ocr_scanner.py"))
            import subprocess
            result = subprocess.run([sys.executable, script_path], capture_output=True, text=True)
            
            output_data = {}
            try:
                output_data = json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                sys.stderr.write(f"Vision Raw Output (Error Parsing): {result.stdout}\\n")
                return "Error: Could not parse vision output."
            
            if output_data.get("status") == "success":
                text = output_data.get("text", "")
                sys.stderr.write(f"Vision Output: {text[:100]}...\\n")
                return text
            else:
                return f"Vision Error: {output_data.get('message')}"

        except Exception as e:
            sys.stderr.write(f"Failed to execute vision: {e}\\n")
            return str(e)



    def _execute_voice(self, details):
        """Calls the voice_handler.py script."""
        try:
            script_path = os.path.abspath(os.path.join(os.path.dirname(__file__), 
                                                       "../../Trading_Backend/automation_engine/voice_module/voice_handler.py"))
            import subprocess
            cmd = [sys.executable, script_path]
            
            if details and "speak" in str(details).lower():
                pass 
                
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            output_data = {}
            try:
                output_data = json.loads(result.stdout.strip())
            except json.JSONDecodeError:
                # print(f"Voice Raw Output (Error Parsing): {result.stdout}")
                return "Error parsing voice output."

            if output_data.get("status") == "success":
                transcribed = output_data.get("transcribed_text", "")
                sys.stderr.write(f"Voice Heard: {transcribed}\\n")
                return transcribed
            elif output_data.get("status") == "no_input":
                return "No voice input detected."
            else:
                return f"Voice Error: {output_data.get('message')}"

        except Exception as e:
            sys.stderr.write(f"Failed to execute voice: {e}\\n")
            return str(e)

    def _mock_decision(self, query):
        """Mock logic for testing without keys"""
        query = query.lower()
        if "scan" in query:
            self._execute_vision()
            return {"intent": "SCAN_SCREEN", "details": query, "execution_status": "Triggered Vision (Mock)"}
        elif "listen" in query or "voice" in query:
            self._execute_voice(query)
            return {"intent": "VOICE", "details": query, "execution_status": "Triggered Voice (Mock)"}
        elif "open" in query or "send" in query:
            # Execute even in mock mode
            self._execute_automation(query)
            return {"intent": "AUTOMATION", "details": query, "execution_status": "Triggered Automation (Mock)"}
        elif "trade" in query or "market" in query or "strategy" in query:
            return {"intent": "TRADING_UPDATE", "details": query}
        elif "generate" in query or "image" in query or "draw" in query:
             return {"intent": "CHAT", "details": "I cannot generate images in Mock mode. Please provide an API key.", "action_needed": "false"}
        else:
            return {"intent": "CHAT", "details": query}

    def _fetch_market_context(self):
        """Fetches last 30 candles summary from Bridge for AI Context."""
        try:
             import requests
             mt5_url = os.getenv("MT5_SERVER_URL", "http://localhost:8000")
             # We need a new endpoint on Bridge for this, or use the analysis logic. 
             # Since we haven't built a dedicated /candles endpoint yet, let's use /status which has 'analysis' 
             # OR ideally, the bridge should expose a digest.
             # For now, let's try to get status.
             
             resp = requests.get(f"{mt5_url}/status", timeout=2)
             if resp.status_code == 200:
                 data = resp.json()
                 analysis = data.get("analysis", {})
                 status = data.get("market_status", "UNKNOWN")
                 
                 context = f"Market Status: {status}\n"
                 if analysis:
                     context += f"Symbol: {analysis.get('symbol')}\n"
                     context += f"Last RSI: {analysis.get('rsi')} (Overbought > 70, Oversold < 30)\n"
                     context += f"Trend Sentiment: {analysis.get('trend')}\n"
                     context += f"Last Price: {analysis.get('last_price')}\n"
                 
                 risk = data.get("risk_settings", {})
                 if risk:
                     context += f"Risk Mode: {risk.get('mode')} (Multiplier: {risk.get('atr_multiplier')})\n"
                     context += f"Latest ATR: {data.get('latest_atr', 'N/A')}\n"
                 
                 # if we had a /history or /candles endpoint, we would add formatted candles here.
                 return context
        except:
             return None
        return None

    def _fetch_news_context(self):
        """Fetches news headlines."""
        try:
             headlines = self.news_fetcher.get_latest_headlines()
             if headlines:
                 summary = ""
                 for h in headlines[:3]: # Top 3
                     summary += f"- {h['title']} ({h['sentiment']})\n"
                 return summary
        except Exception as e:
            return None
        return None

if __name__ == "__main__":
    # Test execution
    if len(sys.argv) > 1:
        user_input = sys.argv[1]
    else:
        user_input = "Open Whatsapp and send hello to John"
    
    brain = SpidyBrain()
    decision = brain.decide_intent(user_input)
    print(json.dumps(decision, indent=2))
