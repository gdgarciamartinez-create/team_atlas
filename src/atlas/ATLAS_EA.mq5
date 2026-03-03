#property strict
#include <Trade/Trade.mqh>
CTrade trade;

input string ATLAS_URL = "http://127.0.0.1:8001/api/mt5/signal";
input bool EXECUTE_TRADES = true;     // true = DEMO execute, false = solo alertas
input int POLL_SECONDS = 2;

datetime lastPoll = 0;

string GetJsonValue(string json, string key) {
   // parser ultra simple (demo). Gemini puede mejorar con JSON lib.
   int p = StringFind(json, "\"" + key + "\"");
   if(p < 0) return "";
   p = StringFind(json, ":", p);
   if(p < 0) return "";
   int q = StringFind(json, ",", p);
   int r = StringFind(json, "}", p);
   int end = (q > 0 && q < r) ? q : r;
   string v = StringSubstr(json, p+1, end-(p+1));
   v = StringTrim(v);
   v = StringReplace(v, "\"", "");
   return v;
}

void OnTick() {
   if(TimeCurrent() - lastPoll < POLL_SECONDS) return;
   lastPoll = TimeCurrent();

   char result[];
   string headers;
   int timeout = 2000;

   int res = WebRequest("GET", ATLAS_URL, "", timeout, NULL, 0, result, headers);
   if(res == -1) {
      Print("WebRequest failed. Add URL to MT5 allowlist: Tools -> Options -> Expert Advisors");
      return;
   }

   string json = CharArrayToString(result);
   string action = GetJsonValue(json, "action");
   if(action != "ENTRY") return;

   // very simple extraction (Gemini puede parsear payload completo)
   string symbol = GetJsonValue(json, "symbol"); // puede venir vacío por parser simple
   if(symbol == "") symbol = _Symbol;

   Alert("ATLAS ENTRY SIGNAL received for ", symbol);

   if(!EXECUTE_TRADES) return;

   // Demo execute: Market order minimal (Gemini ajusta SL/TP/lot con payload real)
   trade.SetExpertMagicNumber(79079);

   // Ejemplo: buy/sell por dirección
   string direction = GetJsonValue(json, "direction");
   double lot = 0.10;

   if(direction == "UP") {
      trade.Buy(lot, symbol);
   } else {
      trade.Sell(lot, symbol);
   }
}
