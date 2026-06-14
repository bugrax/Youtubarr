#!/usr/bin/env python3
"""youtubearr POC — Radarr'daki film için YouTube'da tam-film eşleşmesi bulur."""
import json, subprocess, sys, re, unicodedata

OFFICIAL = {"arzu film","türk sineması","dijital sanat","mars pictures","tff",
            "yeşilçam","türk filmi","fono film","erler film","türker inanoğlu"}

def norm(s):
    s=s.lower()
    s=s.replace("ı","i").replace("ş","s").replace("ğ","g").replace("ü","u").replace("ö","o").replace("ç","c").replace("â","a")
    s=unicodedata.normalize("NFKD",s).encode("ascii","ignore").decode()
    return re.sub(r"[^a-z0-9 ]"," ",s)

def tokens(s):
    stop={"the","a","of","film","filmi","full","hd","4k","izle","tek","parca","parça","movie"}
    return [t for t in norm(s).split() if t and t not in stop and len(t)>1]

def search(query, n=12):
    try:
        out=subprocess.run(["yt-dlp",f"ytsearch{n}:{query}","--flat-playlist","--dump-json","--no-warnings"],
                           capture_output=True,text=True,timeout=90).stdout
    except Exception: return []
    res=[]
    for line in out.splitlines():
        try: res.append(json.loads(line))
        except: pass
    return res

def score(film, cand):
    runtime=film.get("runtime") or 0
    dur=(cand.get("duration") or 0)/60.0
    if runtime and dur:
        ratio=dur/runtime
        if ratio<0.80 or ratio>1.30: return None,"süre uymadı (%dk)"%round(dur)
        dur_score=max(0,1-abs(1-ratio)*2)  # 1.0 birebir, uzaklaştıkça düşer
    elif dur and dur<40:
        return None,"çok kısa"
    else:
        dur_score=0.3
    ftok=set(tokens(film.get("originalTitle") or film.get("title")))
    ctok=set(tokens(cand.get("title","")))
    if not ftok: return None,"başlık yok"
    overlap=len(ftok & ctok)/len(ftok)
    if overlap<0.6: return None,"başlık uymadı"
    views=cand.get("view_count") or 0
    ch=norm(cand.get("channel") or cand.get("uploader") or "")
    official = any(o.replace("ı","i").replace("ş","s").replace("ç","c") in ch for o in [norm(x) for x in OFFICIAL])
    import math
    view_score=min(1.0, math.log10(views+1)/7.0)  # 10M+ ~1.0
    total = dur_score*0.45 + overlap*0.30 + view_score*0.15 + (0.10 if official else 0)
    return total, dict(durmin=round(dur),overlap=round(overlap,2),views=views,official=official)

def best_match(film):
    title=film.get("originalTitle") or film.get("title")
    cands=search(title)
    scored=[]
    for c in cands:
        s,info=score(film,c)
        if s is not None: scored.append((s,c,info))
    scored.sort(key=lambda x:-x[0])
    return scored

if __name__=="__main__":
    films=json.load(open("/tmp/targets.json"))
    for f in films:
        sc=best_match(f)
        head=f"\n### {f.get('originalTitle')} ({f.get('year')}) — {f.get('runtime')}dk"
        if sc:
            s,c,info=sc[0]
            conf="YÜKSEK" if s>=0.75 else "ORTA" if s>=0.6 else "DÜŞÜK"
            print(f"{head}\n  ✅ {conf} ({s:.2f}) {info['durmin']}dk views={info['views']:,} {'[RESMİ]' if info['official'] else ''}")
            print(f"     {c.get('title','')[:60]}  [{c.get('channel','')}]")
            print(f"     https://youtu.be/{c.get('id')}")
        else:
            print(f"{head}\n  ❌ eşleşme yok")
