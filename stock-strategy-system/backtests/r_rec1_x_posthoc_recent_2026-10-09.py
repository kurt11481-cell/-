import importlib.util, sys, math, numpy as np, pandas as pd
sys.dont_write_bytecode=True
BT=sys.argv[1]
spec=importlib.util.spec_from_file_location("rr",BT+"/r_rec1_x_replay_2026-10-09.py"); m=importlib.util.module_from_spec(spec); spec.loader.exec_module(m)
mod=m.load_engine(); rate=m.load_rate()
WIN=[("2010-03-11",None),("2016-01-01",None),("2021-01-01",None),("2023-09-29",None)]
def segd(M,R,a):
    sb=m.seg(mod,R["EB"],R["XB"],a,M.n); sx=m.seg(mod,R["EX"],R["XX"],a,M.n)
    nb=sum(1 for b in R["log"]["boosts"] if b["start"]>=a)
    return sx["cagr"]-sb["cagr"], sx["mdd"]-sb["mdd"], nb
def yearly(M,R):
    EB,EX=R["EB"],R["EX"]; yrs=M.idx.year; out={}
    for y in sorted(set(yrs)):
        ii=np.where(yrs==y)[0]; a,b=ii[0],ii[-1]
        base_b=EB[a-1] if a>0 else 1.0; base_x=EX[a-1] if a>0 else 1.0
        lx=math.log(EX[b]/base_x)-math.log(EB[b]/base_b)
        out[y]=lx*252/len(ii)
    return out
for mk in ("SOX","NDX","SPX"):
    o=m.load_ohlc(mk)
    M=m.Market(mod,o,rate)
    runs={"주(연속)":m.run_pair(mod,M),"H252(연속)":m.run_pair(mod,M,hwm="h252")}
    for lab,R in runs.items():
        cells=[]
        for w,_ in WIN:
            a=int(M.idx.searchsorted(pd.Timestamp(w)))
            dc,dm,nb=segd(M,R,a); cells.append(f"{w[:4] if w!='2023-09-29' else '최근3y'}: {dc*100:+.2f} ({dm*100:+.1f}) n{nb}")
        y=yearly(M,R); ys=np.array(sorted(y)); v=np.array([y[k] for k in ys])
        ew=" ".join(f"h{h}:{np.sum(v*0.5**((ys.max()-ys)/h))/np.sum(0.5**((ys.max()-ys)/h))*100:+.2f}" for h in (2,3,5))
        print(mk,lab,"|"," | ".join(cells),"| 지수가중 연차:",ew)
    cells=[]
    for w,_ in WIN:
        Mf=m.Market(mod,o,rate,start=pd.Timestamp(w)); Rf=m.run_pair(mod,Mf)
        dc,dm,nb=segd(Mf,Rf,0); cells.append(f"{w[:4] if w!='2023-09-29' else '최근3y'}: {dc*100:+.2f} ({dm*100:+.1f}) n{nb}")
    print(mk,"새 시작(그 시점부터 적용)","|"," | ".join(cells))
    if mk=="SOX":
        y=yearly(M,runs["주(연속)"]); y2=yearly(M,runs["H252(연속)"])
        print(" SOX 연도별 X-B(주/H252, %p):"," ".join(f"{k}:{y[k]*100:+.1f}/{y2[k]*100:+.1f}" for k in range(2016,2027)))
