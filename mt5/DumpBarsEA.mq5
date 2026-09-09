//+------------------------------------------------------------------+
//| Dump the broker's own M15 and M1 bars so the research feed and    |
//| the broker feed can be compared bar for bar.  Diagnostic only.    |
//+------------------------------------------------------------------+
#property version "1.00"
#property strict

input string   DumpSymbol = "USTEC";
input datetime FromTime   = D'2022.01.01 00:00';
input datetime ToTime     = D'2026.09.02 00:00';

void Dump(ENUM_TIMEFRAMES tf, string tag)
  {
   MqlRates r[];
   int n = CopyRates(DumpSymbol, tf, FromTime, ToTime, r);
   PrintFormat("%s %s: %d bars", DumpSymbol, tag, n);
   if(n <= 0) return;
   int h = FileOpen(DumpSymbol + "_" + tag + ".csv", FILE_WRITE | FILE_CSV | FILE_ANSI, ',');
   if(h == INVALID_HANDLE) { Print("FileOpen failed ", GetLastError()); return; }
   FileWrite(h, "t", "o", "h", "l", "c");
   for(int i = 0; i < n; i++)
      FileWrite(h, TimeToString(r[i].time, TIME_DATE | TIME_SECONDS),
                DoubleToString(r[i].open, 2), DoubleToString(r[i].high, 2),
                DoubleToString(r[i].low, 2), DoubleToString(r[i].close, 2));
   FileClose(h);
   PrintFormat("wrote %s_%s.csv", DumpSymbol, tag);
  }

int OnInit()
  {
   Dump(PERIOD_M15, "M15");
   Dump(PERIOD_M1,  "M1");
   Print("DUMP DONE");
   return INIT_SUCCEEDED;
  }
void OnTick() {}
