//+------------------------------------------------------------------+
//|                                                  SpidyBridge.mq5 |
//|                                      Copyright 2025, Spidy Team  |
//|                                             https://spidy.ai     |
//+------------------------------------------------------------------+
#property copyright "Copyright 2025, Spidy Team"
#property link      "https://spidy.ai"
#property version   "1.00"
#property strict

// Imports
#include <Trade/Trade.mqh>
#include <Json/Json.mqh> // Assuming a JSON parser is available or we use simple string parsing

// Input Parameters
input string   BridgeURL    = "http://127.0.0.1:8000"; // Python Bridge URL
input int      TimerSeconds = 1;                       // Polling interval

// Global Objects
CTrade         trade;
int            timer_counter = 0;

//+------------------------------------------------------------------+
//| Expert initialization function                                   |
//+------------------------------------------------------------------+
int OnInit()
  {
   // Allow WebRequest
   // Note: User must enable 'Allow WebRequest' in MT5 Options and add localhost
   
   EventSetTimer(TimerSeconds);
   Print("Spidy Bridge Initialized. Connecting to: ", BridgeURL);
   return(INIT_SUCCEEDED);
  }

//+------------------------------------------------------------------+
//| Expert deinitialization function                                 |
//+------------------------------------------------------------------+
void OnDeinit(const int reason)
  {
   EventKillTimer();
   Print("Spidy Bridge Stopped");
  }

//+------------------------------------------------------------------+
//| Expert tick function                                             |
//+------------------------------------------------------------------+
void OnTick()
  {
   // Check market conditions or send tick data every tick if needed
   // For efficiency, we mainly use OnTimer for polling decision
  }

//+------------------------------------------------------------------+
//| Timer function                                                   |
//+------------------------------------------------------------------+
void OnTimer()
  {
   // 1. Prepare Market Data payload (Mock JSON construction for simplicity)
   double ask = SymbolInfoDouble(_Symbol, SYMBOL_ASK);
   double bid = SymbolInfoDouble(_Symbol, SYMBOL_BID);
   
   string payload = StringFormat("{\"symbol\": \"%s\", \"ask\": %G, \"bid\": %G}", _Symbol, ask, bid);
   
   // 2. Send to Bridge and Get Decision
   string response_headers;
   char request_body[];
   char response_body[];
   StringToCharArray(payload, request_body);
   
   int res = WebRequest("POST", BridgeURL + "/trade", NULL, 500, request_body, response_body, response_headers);
   
   if(res == 200)
     {
      string json_response = CharArrayToString(response_body);
      // Print("Bridge Response: ", json_response);
      
      // 3. Simple String Parsing (In real app, use JSON lib)
      if(StringFind(json_response, "BUY") >= 0)
        {
          Print("Spidy says BUY!");
          trade.Buy(0.1, _Symbol, 0, 0, 0, "Spidy AI");
        }
      else if(StringFind(json_response, "SELL") >= 0)
        {
          Print("Spidy says SELL!");
          trade.Sell(0.1, _Symbol, 0, 0, 0, "Spidy AI");
        }
     }
   else
     {
      // Print("Error connecting to bridge: ", res, " Error: ", GetLastError());
      // Suppress spamming errors
     }
  }
//+------------------------------------------------------------------+
