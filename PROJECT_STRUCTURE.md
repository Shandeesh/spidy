# Spidy AI - Project Structure & Roles

This document serves as the master blueprint for the Spidy AI project.

## SHANDEESH THE OWNER 
###  (Backend & Automation)
**Role:** Backend & Automation Developer
**Focus:** Node.js + Python backend, central API, and the Automation Engine (App Control, Screen Scanning).
**Key Responsibilities:**
-   **Automation Engine:** Controlling the OS, opening apps (Insta, WhatsApp), simulating input, and screen reading (OCR).
-   **Backend API:** The central nervous system connecting Frontend, AI Core, and Automation.
-   **Bridge:** Managing the link to the MT5 Trading Bot.

### 👤1 (AI System Architect)
**Role:** AI System Architect
**Focus:** Spidy Core (The Brain), Reasoning, and Strategy.
**Key Responsibilities:**
-   **The Brain:** LangChain/LLM logic processing user intents (voice/text).
-   **Market Intelligence:** Gathering internet data (News, Sentiment).
-   **Strategy Factory:** Analyzing market data to generate "Upgrade Packages" (new JSON configs/strategies) for the MT5 Bot.

### 3 (Frontend & UI)
**Role:** Frontend & UI Developer
**Focus:** Visual Dashboard.
**Key Responsibilities:**
-   **Dashboard:** React/Next.js interface for monitoring Spidy's state, trading logs, and automation status.

### 4 (Security & Data)
**Role:** Cybersecurity & Data Engineer
**Focus:** Security and Compliance.
**Key Res
## Folder Structure

### 📂 Root: `spidy/`

#### 📂 `Trading_Backend/` 
*   `automation_engine/`
    *   `app_control/` (Scripts to open/manage Windows apps)
    *   `input_simulator/` (Keyboard/Mouse control)
    *   `screen_vision/` (OCR, Screenshots)
    *   `voice_module/` (STT / TTS handlers)
*   `social_integrations/`
    *   `whatsapp/`
    *   `instagram/`
*   `backend_api/` (Node.js / FastAPI core)
*   `mt5_bridge/` (Localhost server for MT5 connection)

#### 📂 `AI_Engine/` 
*   `brain/` (Main Agentic Logic)
*   `internet_gathering/`
    *   `news_scraper/`
    *   `market_sentiment/`
*   `strategy_optimizer/` (Logic to produce strategy_update.json)
*   `skills/` (Definitions of capabilities: "Send Message", "Open App")

#### 📂 `Frontend_Dashboard/` 
*   `dashboard_app/` (React/Next.js source)
*   `components/`
*   `public/`

#### 📂 `Security_Module/` 
*   `encryption_utils/`
*   `security_monitor/`
*   `secure_storage/`

#### 📂 `Extension_Module/` 
*   *Placeholder for future modules*

#### 📂 `Shared_Data/` (MongoDB / Files)
*   `configs/` (Current strategies, user preferences)
*   `logs/`
*   `updates_package/` (Where Spidy drops new files for MT5)
