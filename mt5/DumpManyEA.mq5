//+------------------------------------------------------------------+
//| Dump M15 bars for a list of symbols so the locked model can be    |
//| screened on instruments we do not have Dukascopy history for.     |
//| Diagnostic / research only.                                       |
//+------------------------------------------------------------------+
#property version "1.00"
#property strict

input string   Symbols  = "";                      // blank = every Market Watch symbol
input datetime FromTime = D'2015.01.01 00:00';
input datetime ToTime   = D'2026.09.07 00:00';
input int      MinBars  = 20000;                   // skip anything thinner than this

void DumpOne(string sym)
  {
   if(!SymbolSelect(sym, true)) return;
   MqlRates r[];
   int n = CopyRates(sym, PERIOD_M15, FromTime, ToTime, r);
   if(n < MinBars) { PrintFormat("SKIP %s only %d bars", sym, n); return; }
   string safe = sym;
   StringReplace(safe, ".", "_"); StringReplace(safe, "/", "_"); StringReplace(safe, "#", "_");
   int h = FileOpen("M15_" + safe + ".csv", FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) return;
   int dg = (int)SymbolInfoInteger(sym, SYMBOL_DIGITS);
   FileWrite(h, "t", "o", "h", "l", "c", "spread");
   for(int i = 0; i < n; i++)
      FileWrite(h, TimeToString(r[i].time, TIME_DATE | TIME_SECONDS),
                DoubleToString(r[i].open, dg), DoubleToString(r[i].high, dg),
                DoubleToString(r[i].low, dg), DoubleToString(r[i].close, dg),
                IntegerToString(r[i].spread));
   FileClose(h);
   PrintFormat("OK %s %d bars digits=%d point=%.8f", sym, n, dg, SymbolInfoDouble(sym, SYMBOL_POINT));
  }

int OnInit()
  {
   if(StringLen(Symbols) > 0)
     {
      string parts[];
      int k = StringSplit(Symbols, ',', parts);
      for(int i = 0; i < k; i++) { StringTrimLeft(parts[i]); StringTrimRight(parts[i]); DumpOne(parts[i]); }
     }
   else
     {
      int total = SymbolsTotal(false);
      PrintFormat("scanning %d broker symbols", total);
      for(int i = 0; i < total; i++) DumpOne(SymbolName(i, false));
     }
   Print("DUMP DONE");
   return INIT_SUCCEEDED;
  }
void OnTick() {}
