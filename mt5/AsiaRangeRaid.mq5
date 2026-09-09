//+------------------------------------------------------------------+
//|  AsiaRangeRaid.mq5                                               |
//|                                                                  |
//|  Asian-range raid, ICT 2022 sequence.  Validated on USATECH      |
//|  (Nasdaq 100 CFD) 2015-01 .. 2026-08, 262 trades:                |
//|      PF 1.420   +67.5R   WR 28.6%   maxDD -15.2R   R/DD 4.44     |
//|      DEV 2015-2023 PF 1.452  |  VAL 2024-2026 PF 1.353           |
//|                                                                  |
//|  ENTRY (nothing here was optimised - it is the plain reading)    |
//|   1. Asian range = high/low of AsiaStart..AsiaEnd, readable only  |
//|      after AsiaEnd.                                              |
//|   2. RAID: an M15 bar trades below the Asian low (long) or above  |
//|      the Asian high (short).  Record that extreme as the stop.    |
//|      Freeze the last confirmed swing high (low) at that moment.   |
//|   3. Within MaxGapBars M15 bars, a DISPLACEMENT bar must close    |
//|      beyond the frozen swing and have body/range >= DispRatio.    |
//|   4. Take the FIRST 3-candle fair value gap inside that leg.      |
//|   5. Resting limit at the gap's CE (50%), valid EntryWindowMin.   |
//|   6. Stop at the raid extreme. No buffer - buffers were tested    |
//|      across nine widths and all made the drawdown worse.          |
//|   7. Target = the NEAREST unswept pool in the trade direction:    |
//|      previous day's high/low, or the opposite Asian extreme.       |
//|   8. Skip unless MinRR <= planned RR <= MaxRR.                     |
//|   9. Skip if (spread+commission) / stop > CostRiskMax.             |
//|                                                                  |
//|  EXIT (the only part that was added after the loss analysis)      |
//|  10. Stop to BREAK-EVEN once price reaches BreakEvenAtR.           |
//|  11. Target CAPPED at CapTargetR.                                  |
//|  12. SOFT EXIT: SoftExitMin minutes after the fill, if price is    |
//|      at or below SoftExitR, close at market.                       |
//|  13. One position at a time.                                       |
//|                                                                  |
//|  TIMEZONE - read this before running.                             |
//|  The research data is Dukascopy EET (UTC+2 winter / +3 summer).    |
//|  AsiaStartHour/AsiaEndHour/killzone hours below are BROKER SERVER  |
//|  hours.  Most MT5 brokers run EET, in which case leave them at     |
//|  2 and 9.  If your server is not EET, shift them by the difference |
//|  or the Asian range will be the wrong window.  Check with          |
//|  PrintServerTime=true on the first run.                            |
//+------------------------------------------------------------------+
#property copyright "ICT_v7 research"
#property version   "1.00"
#property strict

#include <Trade\Trade.mqh>
#include <Trade\SymbolInfo.mqh>

//--- structure / entry ------------------------------------------------
input group "=== Structure (do not change without re-testing) ==="
input int    SwingBars        = 5;      // swing needs this many bars each side
input int    MaxGapBars       = 40;     // M15 bars allowed from raid to displacement
input double DispRatio        = 0.50;   // displacement body / range
input double MinRR            = 2.0;    // skip if the pool is nearer than this
input double MaxRR            = 10.0;   // skip if the pool is further than this
input double CostRiskMax      = 0.20;   // skip if cost / stop exceeds this
input int    EntryWindowMin   = 360;    // limit order lifetime, minutes
input int    MaxHoldMin       = 1440;   // hard time stop, minutes

input group "=== Exit management (added after loss analysis) ==="
input double BreakEvenAtR     = 1.5;    // move stop to entry at this R
input int    MinTargetCrossings = 2;    // target must have been crossed this often...
input int    TargetLookbackBars = 96;   // ...within this many closed M15 bars (96 = 24h)
input double CapTargetR       = 6.0;    // cap the target at this R
input int    SoftExitMin      = 15;     // check the position this many minutes in
input double SoftExitR        = -0.5;   // ... and close if it is at or below this R

input group "=== Session windows (BROKER SERVER hours) ==="
input int    AsiaStartHour    = 2;      // EET 02:00
input int    AsiaEndHour      = 9;      // EET 09:00 - range readable from here
input bool   PrintServerTime  = true;   // log server time once, to verify the offset

input group "=== Risk and housekeeping ==="
input double RiskPercent      = 1.0;    // percent of equity risked per trade
input double FixedLots        = 0.0;    // >0 overrides RiskPercent
input double CommissionPoints = 0.0;    // round-trip commission, in POINTS
input int    MaxSpreadPoints  = 0;      // 0 = no cap; else skip when spread exceeds
input long   MagicNumber      = 20260906;
input bool   AllowLongs       = true;
input bool   AllowShorts      = true;
input bool   Verbose          = true;

CTrade         trade;
CSymbolInfo    sym;

//--- per-side raid state ---------------------------------------------
struct RaidState
  {
   bool     active;
   datetime bar;        // M15 bar time of the raid
   double   px;         // the raid extreme = the stop
   double   ref;        // frozen swing level the displacement must close beyond
   int      bars;       // M15 bars elapsed since the raid
  };
RaidState gLong, gShort;

//--- running swing levels.  The research keeps these as state that persists until a
//--- NEWER pivot confirms; re-scanning a fixed window instead loses any swing older
//--- than the window and silently blocks the raid that depends on it.
double   gSwHi = 0, gSwLo = 0;
datetime gSwBar = 0;

//--- position bookkeeping --------------------------------------------
double   gEntry = 0, gStop = 0, gR = 0;
datetime gFillTime = 0;
bool     gBeDone = false, gSoftChecked = false;
datetime gLastM15 = 0;
ulong    gPendingTicket = 0;

//+------------------------------------------------------------------+
int OnInit()
  {
   if(!sym.Name(_Symbol)) { Print("symbol init failed"); return INIT_FAILED; }
   trade.SetExpertMagicNumber(MagicNumber);
   trade.SetTypeFillingBySymbol(_Symbol);
   trade.SetDeviationInPoints(10);
   ResetRaid(gLong); ResetRaid(gShort);
   if(PrintServerTime)
      PrintFormat("AsiaRangeRaid on %s | server time now %s | Asia window %02d:00-%02d:00 server. "
                  "Research used EET. If these differ, shift AsiaStartHour/AsiaEndHour.",
                  _Symbol, TimeToString(TimeCurrent(), TIME_DATE|TIME_MINUTES),
                  AsiaStartHour, AsiaEndHour);
   return INIT_SUCCEEDED;
  }

void ResetRaid(RaidState &r) { r.active=false; r.bar=0; r.px=0; r.ref=0; r.bars=0; }

//+------------------------------------------------------------------+
//| every tick: manage the open position, then act on new M15 bars    |
//+------------------------------------------------------------------+
void OnTick()
  {
   if(!sym.RefreshRates()) return;

   bool inPosition = PositionSelectByMagic();
   if(inPosition) ManageOpen();
   // A filled order sets `busy` for the life of the trade, so any other limit still
   // resting can no longer become a trade - cancel it rather than let it fill.
   if(inPosition) DeletePending(); else if(HasPending()) ExpireStale();

   // The DETECTOR RUNS ON EVERY M15 BAR regardless of whether we are in a trade.
   // The research engine kept raid state updated continuously and only filtered
   // overlapping signals at the order stage.  Gating the detector on being flat
   // lets the raid state go stale and silently drops later setups - it cost 25 of
   // 80 trades in the first live comparison, several of them the biggest winners.
   datetime m15[1];
   if(CopyTime(_Symbol, PERIOD_M15, 0, 1, m15) != 1) return;
   if(m15[0] == gLastM15) return;                          // one pass per closed bar
   gLastM15 = m15[0];

   // BUSY MEANS "IN A POSITION", NOT "HAS A WORKING ORDER".  ict_bt.run skips a signal
   // only when its entry bar falls at or before the PREVIOUS TRADE'S EXIT bar; a limit
   // that is still working blocks nothing, and an order that never fills changes no
   // state at all.  Treating a resting order as busy silenced the detector for up to
   // six hours after every signal and cost 15 of 64 trades in 2022-2023 alone.
   OnNewM15Bar(inPosition);                                // busy -> detect, do not order
  }

//+------------------------------------------------------------------+
bool PositionSelectByMagic()
  {
   for(int i = PositionsTotal() - 1; i >= 0; i--)
     {
      ulong tk = PositionGetTicket(i);
      if(tk == 0) continue;
      if(PositionGetString(POSITION_SYMBOL) == _Symbol &&
         PositionGetInteger(POSITION_MAGIC) == MagicNumber)
        {
         if(gFillTime == 0)                                // freshly filled
           {
            gEntry    = PositionGetDouble(POSITION_PRICE_OPEN);
            gStop     = PositionGetDouble(POSITION_SL);
            gR        = MathAbs(gEntry - gStop);
            gFillTime = (datetime)PositionGetInteger(POSITION_TIME);
            gBeDone = false; gSoftChecked = false;
            DeletePending();
            if(Verbose) PrintFormat("filled @ %.2f  stop %.2f  R=%.2f pts", gEntry, gStop, gR);
           }
         return true;
        }
     }
   if(gFillTime != 0) { gFillTime = 0; gR = 0; }           // position closed
   return false;
  }

//+------------------------------------------------------------------+
//| rules 10-12: break-even, soft exit.  The capped target is already |
//| in the TP placed at entry.                                        |
//+------------------------------------------------------------------+
void ManageOpen()
  {
   if(gR <= 0) return;
   long   type = PositionGetInteger(POSITION_TYPE);
   bool   isBuy = (type == POSITION_TYPE_BUY);
   double now   = isBuy ? sym.Bid() : sym.Ask();
   double favR  = (isBuy ? (now - gEntry) : (gEntry - now)) / gR;

   // 10. break-even once favourable excursion reaches BreakEvenAtR
   if(!gBeDone && favR >= BreakEvenAtR)
     {
      double sl = PositionGetDouble(POSITION_SL);
      bool   need = isBuy ? (sl < gEntry) : (sl > gEntry);
      if(need && trade.PositionModify(PositionGetInteger(POSITION_TICKET),
                                      NormalizePrice(gEntry), PositionGetDouble(POSITION_TP)))
        { gBeDone = true; if(Verbose) Print("stop moved to break-even"); }
     }

   int held = (int)((TimeCurrent() - gFillTime) / 60);

   // 11. soft exit, checked once
   if(!gSoftChecked && held >= SoftExitMin)
     {
      gSoftChecked = true;
      if(favR <= SoftExitR)
        {
         if(Verbose) PrintFormat("soft exit at %.2fR after %d min", favR, held);
         trade.PositionClose(PositionGetInteger(POSITION_TICKET));
         return;
        }
     }

   // 12. hard time stop
   if(held >= MaxHoldMin)
     {
      if(Verbose) Print("time stop");
      trade.PositionClose(PositionGetInteger(POSITION_TICKET));
     }
  }

//+------------------------------------------------------------------+
void OnNewM15Bar(bool busy)
  {
   // The Asian range is unreadable between midnight and AsiaEndHour.  The research
   // does NOT skip those bars: it sets ah/al to NaN and keeps the detector running, so
   // a raid armed late in one session can still produce its signal after midnight with
   // the draw-on-liquidity target falling back to PDH/PDL alone.  Returning early here
   // also froze the 40-bar raid clock and the swing state for nine hours a day.
   double asiaHi = 0, asiaLo = 0;                          // 0 == unavailable (NaN)
   AsianRange(asiaHi, asiaLo);

   MqlRates r[];
   int need = MathMax(MaxGapBars + 4 * SwingBars + 10, 600);   // cold-start depth
   if(CopyRates(_Symbol, PERIOD_M15, 1, need, r) < need) return;   // index 0 = last CLOSED
   ArraySetAsSeries(r, true);

   UpdateSwings(r, need);                                  // persists across bars
   double swHi = gSwHi, swLo = gSwLo;

   double hi = r[0].high, lo = r[0].low, cl = r[0].close, op = r[0].open;
   double rng = MathMax(hi - lo, _Point);

   // age the raid states
   if(gLong.active)  { gLong.bars++;  if(gLong.bars  > MaxGapBars) ResetRaid(gLong);  }
   if(gShort.active) { gShort.bars++; if(gShort.bars > MaxGapBars) ResetRaid(gShort); }

   // 2. the raid.  It must be the bar that FIRST breaks the level: the previous
   //    bar has to have been on the other side of it.  Without this the state
   //    re-arms on every bar of an extended run beyond the range and the stop
   //    ends up on a different extreme than the research used.
   double prevLo = r[1].low, prevHi = r[1].high;

   if(AllowLongs && asiaLo > 0 && lo < asiaLo && prevLo >= asiaLo && (!gLong.active || lo < gLong.px) && swHi > 0)
     { gLong.active=true; gLong.bar=r[0].time; gLong.px=lo; gLong.ref=swHi; gLong.bars=0;
       if(Verbose) PrintFormat("RAID sell-side @ %.2f (asia low %.2f) ref swing high %.2f", lo, asiaLo, swHi); }

   if(AllowShorts && asiaHi > 0 && hi > asiaHi && prevHi <= asiaHi && (!gShort.active || hi > gShort.px) && swLo > 0)
     { gShort.active=true; gShort.bar=r[0].time; gShort.px=hi; gShort.ref=swLo; gShort.bars=0;
       if(Verbose) PrintFormat("RAID buy-side @ %.2f (asia high %.2f) ref swing low %.2f", hi, asiaHi, swLo); }

   double body = MathAbs(cl - op);
   if(body / rng < DispRatio) return;                      // 3. displacement quality

   // 3+4+5: displacement closing beyond the frozen swing, then the first FVG in the leg
   if(gLong.active && gLong.bars > 0 && cl > gLong.ref && cl > op)
     {
      if(busy) ResetRaid(gLong);                           // consumed, but not tradeable
      else
        {
         int rc = TryEntry(true, r, need, gLong, asiaHi, asiaLo);
         if(rc > 0) ResetRaid(gLong);                      // A SIGNAL WAS EMITTED
         if(rc == 2) return;
        }
     }

   if(gShort.active && gShort.bars > 0 && cl < gShort.ref && cl < op)
     {
      if(busy) ResetRaid(gShort);
      else if(TryEntry(false, r, need, gShort, asiaHi, asiaLo) > 0) ResetRaid(gShort);
     }
  }

//+------------------------------------------------------------------+
//| Asian range of the CURRENT day, only once the window has closed   |
//+------------------------------------------------------------------+
bool AsianRange(double &hiOut, double &loOut)
  {
   MqlDateTime t; TimeToStruct(TimeCurrent(), t);
   if(t.hour < AsiaEndHour) return false;                  // causality: not closed yet

   datetime dayStart = StructToTime(t) - (t.hour*3600 + t.min*60 + t.sec);
   datetime from = dayStart + AsiaStartHour*3600;
   datetime to   = dayStart + AsiaEndHour*3600;

   // M1, not M15.  The research window is df.between_time("02:00","09:00") on
   // one-minute bars, which includes the 09:00 MINUTE only.  Reading it off M15 bars
   // swallows the whole 09:00-09:14 candle and moves both extremes.
   MqlRates r[];
   int n = CopyRates(_Symbol, PERIOD_M1, from, to, r);    // inclusive of the AsiaEnd minute
   if(n <= 0) return false;
   hiOut = -DBL_MAX; loOut = DBL_MAX;
   for(int i = 0; i < n; i++) { hiOut = MathMax(hiOut, r[i].high); loOut = MathMin(loOut, r[i].low); }
   return (hiOut > loOut);
  }

//+------------------------------------------------------------------+
//| the most recent CONFIRMED swing high / low.  A pivot at index k   |
//| needs SwingBars bars on each side, so it is only confirmed once   |
//| SwingBars newer bars exist - never uses an unconfirmed pivot.      |
//+------------------------------------------------------------------+
void UpdateSwings(const MqlRates &r[], int n)
  {
   // Mirrors the research `swings()`:  numpy argmax()==n means the pivot bar is
   // STRICTLY above every OLDER bar in the window and >= every NEWER one (ties go to
   // the earlier index).  In a series array r[k+j] is OLDER and r[k-j] is NEWER, so
   // the two comparisons are not symmetric - getting them the wrong way round picks a
   // different pivot on every equal high, which moves the stop and the raid reference.
   //
   // The level then PERSISTS until a newer pivot confirms, exactly like the research's
   // running sh/sl.  Bars must be walked oldest -> newest so the newest pivot wins.
   int kmax = SwingBars;
   for(int k = SwingBars; k < n - SwingBars; k++)
      if(r[k].time > gSwBar) kmax = k; else break;
   if(gSwBar == 0) kmax = n - SwingBars - 1;               // cold start: scan it all

   for(int k = kmax; k >= SwingBars; k--)                  // decreasing k = forward in time
     {
      if(r[k].time <= gSwBar) continue;
      bool hi = true, lo = true;
      for(int j = 1; j <= SwingBars; j++)
        {
         if(r[k].high <  r[k-j].high || r[k].high <= r[k+j].high) hi = false;
         if(r[k].low  >  r[k-j].low  || r[k].low  >= r[k+j].low ) lo = false;
         if(!hi && !lo) break;
        }
      if(hi) gSwHi = r[k].high;
      if(lo) gSwLo = r[k].low;
     }
   if(n > SwingBars) gSwBar = r[SwingBars].time;
  }

//+------------------------------------------------------------------+
//| Monday filter.  True if the order could still be working on Monday |
//+------------------------------------------------------------------+
bool IsMonday(datetime t)
  {
   MqlDateTime d; TimeToStruct(t, d); return d.day_of_week == 1;
  }

bool FillsOnMonday(datetime now, int windowMin)
  {
   return IsMonday(now) || IsMonday(now + windowMin * 60);
  }

//+------------------------------------------------------------------+
//| rules 4-9: find the gap, price the trade, apply the gates, order  |
//+------------------------------------------------------------------+
//  Returns 0 = no signal, the raid stays armed and may fire on a later bar.
//          1 = A SIGNAL WAS EMITTED but no order was placed (an execution gate said no).
//          2 = a signal was emitted and the limit order is resting.
//
//  The 0/1 split is the whole point.  In the research the DETECTOR emits the signal as
//  soon as the displacement closes through the frozen swing and a gap exists, and it
//  clears the sweep at that instant - `sweep[side] = None`.  Every later gate (R:R,
//  cost/risk, the Monday rule) lives in the EXECUTION layer and runs after the sweep is
//  already gone, so a rejected setup is simply not traded.  Letting the raid stay armed
//  and retry on the next displacement bar turns one rejected signal into a queue of
//  late duplicates: it added 109 orders the research never places, and it re-took
//  Monday setups on Tuesday morning.
int TryEntry(bool isLong, const MqlRates &r[], int n, RaidState &st,
             double asiaHi, double asiaLo)
  {
   // 4. first 3-candle FVG inside the leg (walk the leg oldest -> newest)
   double gLo = 0, gHi = 0;
   bool found = false;
   for(int k = st.bars; k >= 2 && !found; k--)             // k = bars back from current
     {
      int a = k, b = k - 2;                                // a older, b newer
      if(a >= n || b < 0) continue;
      if(isLong)  { if(r[b].low  > r[a].high) { gLo = r[a].high; gHi = r[b].low;  found = true; } }
      else        { if(r[b].high < r[a].low ) { gLo = r[b].high; gHi = r[a].low;  found = true; } }
     }
   if(!found || gHi <= gLo) return 0;   // GATE 6 failed: no gap, raid stays armed

   // ---- from here the signal EXISTS.  Every rejection below returns 1. ----------

   double entry = (gLo + gHi) / 2.0;                       // 5. CE
   double stop  = st.px;                                   // 6. raid extreme
   double R     = isLong ? (entry - stop) : (stop - entry);
   if(R <= 0) return 1;

   // 7. nearest unswept pool in the trade direction
   double pdh, pdl;
   if(!PrevDay(pdh, pdl)) return 1;
   double tp = 0;
   if(isLong)
     {
      double best = DBL_MAX;
      if(pdh    > entry) best = MathMin(best, pdh);
      if(asiaHi > 0 && asiaHi > entry) best = MathMin(best, asiaHi);
      if(best == DBL_MAX) return 1;
      tp = best;
     }
   else
     {
      double best = -DBL_MAX;
      if(pdl    < entry) best = MathMax(best, pdl);
      if(asiaLo > 0 && asiaLo < entry) best = MathMax(best, asiaLo);
      if(best == -DBL_MAX) return 1;
      tp = best;
     }

   // 7b. DRAW-ON-LIQUIDITY REACHABILITY.  Count how many times price has CLOSED across
   //     this target over the last TargetLookbackBars closed M15 bars.  Zero means price
   //     has spent the whole window on one side of it: the trade is being asked to reach
   //     liquidity it has not been near all day.  Measured on 2015-2026, this single gate
   //     takes DEV profit factor 1.233 -> 1.576 and VAL 1.367 -> 1.712 while RAISING total
   //     R, raising the win rate and halving the drawdown.  Permutation p = 0.0002.
   //     Counted on the UNCAPPED target, which is the level the research measured.
   if(MinTargetCrossings > 0)
     {
      int lim = MathMin(TargetLookbackBars, n - 1);
      int xings = 0;
      bool prev = (r[lim].close > tp);
      for(int k = lim - 1; k >= 0; k--)
        {
         bool cur = (r[k].close > tp);
         if(cur != prev) xings++;
         prev = cur;
        }
      if(xings < MinTargetCrossings)
        {
         if(Verbose) PrintFormat("skip: target %.2f crossed only %d time(s) in %d bars",
                                 tp, xings, lim);
         return 1;
        }
     }

   double rr = (isLong ? (tp - entry) : (entry - tp)) / R;
   if(rr < MinRR || rr > MaxRR) return 1;              // 8. R:R gate - skip, never resize
   if(rr > CapTargetR)                                     // 11. cap the target
     { rr = CapTargetR; tp = isLong ? entry + rr*R : entry - rr*R; }

   // 9. cost / structural risk
   double spread = (sym.Ask() - sym.Bid()) / _Point;
   if(MaxSpreadPoints > 0 && spread > MaxSpreadPoints) return 1;
   double cost = spread + CommissionPoints;
   if(cost / (R / _Point) > CostRiskMax)
     { if(Verbose) PrintFormat("skip: cost %.1f pts / stop %.1f pts = %.0f%% > %.0f%%",
                               cost, R/_Point, 100*cost/(R/_Point), 100*CostRiskMax); return 1; }

   // SKIP_DOW = (0,) in asia_locked.py: Monday is the weekly ACCUMULATION phase, and
   // is the only negative weekday in BOTH periods independently (2024-26 PF 0.708
   // p=0.0315; 2015-23 PF 0.513 p=0.0047).  The rule is applied to the FILL day, so
   // live it means: never leave an order that could fill on a Monday.  The order is
   // also killed if it survives into Monday (see ExpireStale).
   if(FillsOnMonday(TimeCurrent(), EntryWindowMin)) return 1;

   double lots = Lots(R);
   if(lots <= 0) return 1;

   entry = NormalizePrice(entry); stop = NormalizePrice(stop); tp = NormalizePrice(tp);
   datetime expiry = TimeCurrent() + EntryWindowMin * 60;

   // Do NOT cancel the resting order.  In the research two limits can be live at once
   // and whichever fills first becomes the trade; the other simply expires.  Cancelling
   // makes the newest signal the only one that can fill, which is a different model.
   bool ok = isLong
      ? trade.BuyLimit (lots, entry, _Symbol, stop, tp, ORDER_TIME_SPECIFIED, expiry, "AsiaRaid")
      : trade.SellLimit(lots, entry, _Symbol, stop, tp, ORDER_TIME_SPECIFIED, expiry, "AsiaRaid");

   if(ok)
     {
      gPendingTicket = trade.ResultOrder();
      PrintFormat("%s LIMIT %.2f  stop %.2f  target %.2f  RR %.2f  R %.1f pts  lots %.2f",
                  isLong ? "BUY" : "SELL", entry, stop, tp, rr, R/_Point, lots);
     }
   else PrintFormat("order failed: %d %s", trade.ResultRetcode(), trade.ResultRetcodeDescription());
   return ok ? 2 : 1;                    // the caller clears the raid either way
  }

//+------------------------------------------------------------------+
bool PrevDay(double &pdh, double &pdl)
  {
   MqlRates d[];
   if(CopyRates(_Symbol, PERIOD_D1, 1, 1, d) != 1) return 1;   // index 1 = yesterday
   pdh = d[0].high; pdl = d[0].low;
   return (pdh > pdl);
  }

//+------------------------------------------------------------------+
double Lots(double stopPoints)
  {
   if(FixedLots > 0) return NormalizeLots(FixedLots);
   double risk  = AccountInfoDouble(ACCOUNT_EQUITY) * RiskPercent / 100.0;
   double tickV = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_VALUE);
   double tickS = SymbolInfoDouble(_Symbol, SYMBOL_TRADE_TICK_SIZE);
   if(tickV <= 0 || tickS <= 0) return 0;
   double lossPerLot = (stopPoints / tickS) * tickV;
   if(lossPerLot <= 0) return 0;
   return NormalizeLots(risk / lossPerLot);
  }

double NormalizeLots(double l)
  {
   double mn = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MIN);
   double mx = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_MAX);
   double st = SymbolInfoDouble(_Symbol, SYMBOL_VOLUME_STEP);
   if(st <= 0) st = 0.01;
   l = MathFloor(l / st) * st;
   if(l < mn) return 0;                                    // too small to risk correctly
   return MathMin(l, mx);
  }

double NormalizePrice(double p)
  { return NormalizeDouble(p, (int)SymbolInfoInteger(_Symbol, SYMBOL_DIGITS)); }

bool HasPending()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) == _Symbol &&
         OrderGetInteger(ORDER_MAGIC) == MagicNumber) return true;
     }
   return false;
  }

//--- the broker honours ORDER_TIME_SPECIFIED, but delete defensively too
void ExpireStale()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) != _Symbol ||
         OrderGetInteger(ORDER_MAGIC) != MagicNumber) continue;
      datetime setup = (datetime)OrderGetInteger(ORDER_TIME_SETUP);
      // expire on age, and also the moment the clock rolls into Monday - the locked
      // model does not take a fill on a Monday (SKIP_DOW).
      if(TimeCurrent() - setup >= EntryWindowMin * 60 || IsMonday(TimeCurrent()))
         trade.OrderDelete(tk);
     }
  }

void DeletePending()
  {
   for(int i = OrdersTotal() - 1; i >= 0; i--)
     {
      ulong tk = OrderGetTicket(i);
      if(tk == 0) continue;
      if(OrderGetString(ORDER_SYMBOL) == _Symbol &&
         OrderGetInteger(ORDER_MAGIC) == MagicNumber) trade.OrderDelete(tk);
     }
   gPendingTicket = 0;
  }
//+------------------------------------------------------------------+
