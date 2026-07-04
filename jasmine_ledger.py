#!/usr/bin/env python3
"""JASMINE LEDGER — isolated, deposit-aware, independently auditable track record.
Runs ALONE on a dedicated box. Seals one hash-chained record per day and publishes
to a public git repo. Capital injections are recorded as flagged entries and EXCLUDED
from performance: returns are reported TIME-WEIGHTED (the institutional standard), so
adding £1,000/month can never be mistaken for profit.

Audit:  git clone <repo> && python3 jasmine_ledger.py verify && python3 jasmine_ledger.py report
"""
import json, hashlib, datetime, sys, os, subprocess
HERE=os.path.dirname(os.path.abspath(__file__))
LEDGER=os.path.join(HERE,"ledger.jsonl"); CONF=os.path.join(HERE,"jasmine.conf.json")
GENESIS="0"*64

def conf():
    with open(CONF) as f: return json.load(f)
def rows():
    return [json.loads(l) for l in open(LEDGER)] if os.path.exists(LEDGER) else []
def rec_hash(r):
    core={k:r.get(k) for k in ("date","ts_utc","kind","balance","equity","closed_net_pl",
          "deposit","currency","account","source","prev_hash","seq")}
    return hashlib.sha256(json.dumps(core,sort_keys=True).encode()).hexdigest()
def pull_state():
    out=subprocess.check_output(conf()["state_pull_cmd"],shell=True,timeout=30).decode()
    return json.loads(out)["live"]
def append(r):
    r["hash"]=rec_hash(r)
    with open(LEDGER,"a") as f: f.write(json.dumps(r)+"\n")
    return r
def publish(msg):
    if not conf().get("git_push"): return
    for c in (["git","-C",HERE,"add","ledger.jsonl"],["git","-C",HERE,"commit","-m",msg],["git","-C",HERE,"push"]):
        subprocess.run(c,check=False)
def new(kind, st, prev, seq, deposit=0.0):
    return {"date":datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d"),
        "ts_utc":datetime.datetime.now(datetime.timezone.utc).isoformat(),"kind":kind,
        "account":st.get("account_number"),"currency":st.get("currency","GBP"),
        "balance":round(float(st.get("real_balance",st.get("equity",0))),2),
        "equity":round(float(st.get("equity",0)),2),
        "closed_net_pl":round(float(st.get("closed_net_pl",0)),2),
        "open_positions":st.get("open_positions_mt4",0),"deposit":round(float(deposit),2),
        "source":conf().get("account","broker-mt4"),"prev_hash":prev,"seq":seq}

def seal():
    ex=rows(); today=datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%d")
    if any(r["date"]==today and r["kind"]=="seal" for r in ex): print("already sealed %s"%today); return
    st=pull_state(); prev=ex[-1]["hash"] if ex else GENESIS
    r=append(new("seal",st,prev,(ex[-1]["seq"]+1) if ex else 0))
    print("SEALED %s seq %d £%.2f hash %s"%(today,r["seq"],r["balance"],r["hash"][:16]))
    publish("jasmine seal %s seq %d £%.2f"%(today,r["seq"],r["balance"]))

def deposit():
    """Record a capital injection. Usage: jasmine_ledger.py deposit <amount>
    Seal this AFTER the funds land so the recorded balance already includes them."""
    amt=float(sys.argv[2]); ex=rows(); st=pull_state()
    prev=ex[-1]["hash"] if ex else GENESIS
    r=append(new("deposit",st,prev,(ex[-1]["seq"]+1) if ex else 0,deposit=amt))
    print("DEPOSIT %s +£%.2f  balance now £%.2f  seq %d (excluded from performance)"%(r["date"],amt,r["balance"],r["seq"]))
    publish("jasmine deposit %s +£%.2f seq %d"%(r["date"],amt,r["seq"]))

def genesis():
    """First entry. Usage: jasmine_ledger.py genesis  (records opening capital as the baseline)"""
    if rows(): print("genesis already exists"); return
    st=pull_state(); r=append(new("genesis",st,GENESIS,0,deposit=float(st.get("real_balance",st.get("equity",0)))))
    print("GENESIS %s  opening capital £%.2f  hash %s  — the clock starts. For Jasmine."%(r["date"],r["balance"],r["hash"][:16]))
    publish("jasmine GENESIS %s £%.2f"%(r["date"],r["balance"]))

def verify():
    rs=rows()
    if not rs: print("empty"); return
    prev=GENESIS
    for r in rs:
        if r["prev_hash"]!=prev or rec_hash(r)!=r["hash"]:
            print("BROKEN at seq %d (%s)"%(r["seq"],r["date"])); return
        prev=r["hash"]
    print("CHAIN INTACT ✓  %d entries  %s→%s"%(len(rs),rs[0]["date"],rs[-1]["date"]))

def report():
    rs=rows()
    if not rs: print("no genesis yet"); return
    # time-weighted return: chain daily returns, crediting deposits OUT of the numerator
    twr=1.0; prevbal=None; deposits=0.0; daily=[]
    for r in rs:
        b=r["balance"]; d=r.get("deposit",0.0) if r["kind"]!="genesis" else 0.0
        if prevbal is not None and prevbal>0:
            rt=(b-d)/prevbal - 1.0      # strip injected capital from the period's gain
            twr*=(1+rt); daily.append((r["date"],rt))
        if r["kind"] in ("deposit","genesis"): deposits+=r.get("deposit",0.0)
        prevbal=b
    base=rs[0]["balance"]; cur=rs[-1]["balance"]
    net_dep=sum(r.get("deposit",0.0) for r in rs)
    print("=== JASMINE track record (%s) ==="%rs[0]["account"])
    print("opened %s £%.2f   latest %s £%.2f"%(rs[0]["date"],base,rs[-1]["date"],cur))
    print("capital injected total: £%.2f   |   TRADING profit (ex-deposits): £%.2f"%(net_dep,cur-net_dep))
    print("TIME-WEIGHTED RETURN (the real number): %+.2f%%"%((twr-1)*100))
    from collections import OrderedDict; mo=OrderedDict()
    for r in rs:
        if r["kind"]=="genesis": continue
        b=r["balance"]; d=r.get("deposit",0.0)
    # monthly TWR
    mtwr=OrderedDict(); pv=None
    for r in rs:
        b=r["balance"]; d=r.get("deposit",0.0) if r["kind"]!="genesis" else 0.0
        if pv is not None and pv>0:
            m=r["date"][:7]; mtwr.setdefault(m,1.0); mtwr[m]*=(1+((b-d)/pv-1))
        pv=b
    print("\nmonth      TWR      +1%%")
    hit=0
    for m,v in mtwr.items():
        ret=(v-1)*100; hit+=ret>=1.0; print("  %s  %+6.2f%%   %s"%(m,ret,"✓" if ret>=1 else ""))
    print("\nmonths ≥ +1%% TWR: %d / 6   (target: 6 consecutive, 0.5–1%% over retail)  — for Jasmine"%hit)

if __name__=="__main__":
    cmd=sys.argv[1] if len(sys.argv)>1 else "report"
    {"genesis":genesis,"seal":seal,"deposit":deposit,"verify":verify,"report":report}.get(cmd,report)()
