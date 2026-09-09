"""Full systematic search inside the DAY-TRADING box (5/8/12 pip, <=4h hold).
Search on IS, then one pass on the reserved hold-out."""
import sys, pathlib, numpy as np, pandas as pd
sys.path.insert(0, r"C:\personal\ICT_v7")
from census.features import build
from engine.barrier import sequential

DATA=pathlib.Path(r"C:\personal\ICT_v7\data"); PIP={"EURUSD":1e-4,"GBPUSD":1e-4,"USDJPY":1e-2}
WIDTHS=[5,8,12]; IS_END="2025-06-30"; OOS="2025-07-01"; MIN_T=100

def wilson(k,n,z=1.96):
    if n==0: return (np.nan,np.nan)
    p=k/n; d=1+z*z/n; c=(p+z*z/(2*n))/d
    h=z*np.sqrt(p*(1-p)/n+z*z/(4*n*n))/d
    return c-h,c+h

def stats(sig,out,hld):
    r,_=sequential(np.ascontiguousarray(sig.astype(np.bool_)),out,hld)
    dec=int((r!=0).sum()); k=int((r==1).sum())
    if dec<MIN_T: return None
    lo,hi=wilson(k,dec)
    return dict(trades=dec,wr=k/dec,wl=lo,wh=hi,PF=k/max(dec-k,1))

cache={}; rows=[]
for p in PIP:
    df=pd.read_parquet(DATA/f"{p}.parquet"); oc=pd.read_parquet(DATA/f"{p}_dt.parquet")
    ft=build(df,PIP[p]).loc[oc.index]
    is_m=np.asarray(oc.index<=IS_END); oos_m=np.asarray(oc.index>=OOS)
    cache[p]=(ft,oc,is_m,oos_m)
    for w in WIDTHS:
        for s in ("L","S"):
            out=np.ascontiguousarray(oc[f"o_{w}{s}"].values.astype(np.int8))
            hld=np.ascontiguousarray(oc[f"h_{w}{s}"].values.astype(np.int64))
            def sc(mask,name):
                st_=stats(mask&is_m,out,hld)
                if st_: rows.append(dict(pair=p,width=w,side=s,hyp=name,**st_))
            sc(np.ones(len(ft),bool),"ALL_BARS(null)")
            for c in [c for c in ft.columns if c not in ("hour","dow")]:
                try: q=pd.qcut(ft[c][is_m],5,labels=False,retbins=True,duplicates="drop")[1]
                except Exception: continue
                e=np.asarray(q,float); e[0],e[-1]=-np.inf,np.inf
                lab=np.asarray(pd.cut(ft[c],e,labels=False))
                for b in range(len(e)-1): sc(lab==b,f"{c}_q{b}")
            for hh in range(24): sc(np.asarray(ft.hour==hh),f"hour_{hh:02d}")
            for dd in range(5):  sc(np.asarray(ft.dow==dd),f"dow_{dd}")

r=pd.DataFrame(rows); r.to_csv(r"C:\personal\ICT_v7\reports\dt_IS.csv",index=False)
null=r[r.hyp=="ALL_BARS(null)"]; r=r[r.hyp!="ALL_BARS(null)"]
print(f"=== DAY-TRADING BOX: 5/8/12 pip stop, max 4h hold ===")
print(f"hypotheses tested: {len(r):,}\n")
print("NULL (take every bar):")
print(null[["pair","width","side","trades","wr"]].to_string(index=False))
print(f"\n--- IN-SAMPLE win-rate distribution over {len(r):,} hypotheses ---")
print(r.wr.describe(percentiles=[.5,.9,.99]).to_string())
for th in (.70,.60,.55,.52): print(f"  WR >= {th:.2f} : {(r.wr>=th).sum()}")
print(f"\n--- TOP 12 IN-SAMPLE ---")
top=r.nlargest(12,"wr")
print(top[["pair","width","side","hyp","trades","wr","wl","wh","PF"]].to_string(index=False))

# ---- one pass on reserved data ----
res=[]
for _,c in top.iterrows():
    ft,oc,is_m,oos_m=cache[c.pair]; n=c.hyp
    if n.startswith("hour_"): mask=np.asarray(ft.hour==int(n[5:]))
    elif n.startswith("dow_"): mask=np.asarray(ft.dow==int(n[4:]))
    else:
        f_,b=n.rsplit("_q",1)
        e=np.asarray(pd.qcut(ft[f_][is_m],5,labels=False,retbins=True,duplicates="drop")[1],float)
        e[0],e[-1]=-np.inf,np.inf
        mask=np.asarray(pd.cut(ft[f_],e,labels=False)==int(b))
    out=np.ascontiguousarray(oc[f"o_{c.width}{c.side}"].values.astype(np.int8))
    hld=np.ascontiguousarray(oc[f"h_{c.width}{c.side}"].values.astype(np.int64))
    st_=stats(mask&oos_m,out,hld) or {}
    res.append(dict(pair=c.pair,width=c.width,side=c.side,hyp=n,IS_wr=c.wr,IS_n=c.trades,
        OOS_n=st_.get("trades",0),OOS_wr=st_.get("wr",np.nan),OOS_wl=st_.get("wl",np.nan),
        OOS_PF=st_.get("PF",np.nan),decay=st_.get("wr",np.nan)-c.wr))
o=pd.DataFrame(res); o.to_csv(r"C:\personal\ICT_v7\reports\dt_OOS.csv",index=False)
print(f"\n=== HOLD-OUT 2025-07-01 -> 2026-09-04 ===")
print(o.to_string(index=False,float_format=lambda x:f"{x:.4f}"))
print(f"\nOOS >= 0.70: {(o.OOS_wr>=0.70).sum()}   OOS >= 0.55: {(o.OOS_wr>=0.55).sum()}   "
      f"OOS > 0.50: {(o.OOS_wr>0.50).sum()}   Wilson-low > 0.50: {(o.OOS_wl>0.50).sum()}")
print(f"mean IS {o.IS_wr.mean():.4f} -> mean OOS {o.OOS_wr.mean():.4f}  (decay {o.decay.mean():+.4f})")
