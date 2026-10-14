"""Analisi delle partite di taratura, divise per fase di gioco (regni 1-3, 4-6, 7-9, 10+).
Uso: python strumenti/taratura_analisi.py strumenti/taratura_out/*.json"""
import json, sys, statistics as st, collections as C
files = sys.argv[1:]
phases = ["A(1-3)", "B(4-6)", "C(7-9)", "D(10+)"]
agg = {p: {"days": 0, "fights": [], "scenes": C.Counter(), "deaths": 0} for p in phases}
causes = C.Counter()
intr = C.Counter()
for f in files:
    d = json.load(open(f))
    for p, n in d.get("phase_days", {}).items():
        agg[p]["days"] += n
    for x in d.get("fights", []):
        agg[x["phase"]]["fights"].append(x)
    for day, p, k in d.get("scene_log", []):
        fam = k.split("_")[0] if k.startswith(("intrigo", "eco", "dialogo")) else k
        agg[p]["scenes"][fam] += 1
    for dd in d["deaths"]:
        t = dd[1]; p = "A(1-3)" if t <= 3 else "B(4-6)" if t <= 6 else "C(7-9)" if t <= 9 else "D(10+)"
        agg[p]["deaths"] += 1
        causes[" ".join(dd[2].split()[:2])] += 1
    for k, o, _d in d.get("intrigues", []):
        intr[(k, o)] += 1
    print(f, "giorni", d["days"], "morti", len(d["deaths"]), "tier finale", d["samples"][-1]["tier"] if d["samples"] else "?")
print()
for p in phases:
    a = agg[p]; days = max(1, a["days"]); fs = a["fights"]
    if not a["days"]:
        continue
    rs = sorted(x["ratio"] for x in fs)
    def q(v): return rs[min(len(rs) - 1, int(v * len(rs)))] if rs else 0
    forced = [x for x in fs if x["forced"]]
    print(f"== {p}: {a['days']} giorni · scontri {len(fs)} ({len(fs)/days:.2f}/g, imboscate {len(forced)/days:.2f}/g) · "
          f"vinti {sum(x['won'] for x in fs)/max(1,len(fs)):.0%} · morti {a['deaths']} ({a['deaths']/days*100:.2f}/100g)")
    if rs:
        print(f"   rapporto nemico/te: mediana {q(.5):.2f} · p10 {q(.1):.2f} · p90 {q(.9):.2f} · >1.5: {sum(r>1.5 for r in rs)/len(rs):.0%} · <0.3: {sum(r<0.3 for r in rs)/len(rs):.0%}")
        if forced:
            fr = sorted(x["ratio"] for x in forced)
            print(f"   imboscate: mediana {fr[len(fr)//2]:.2f} · p90 {fr[int(.9*len(fr))]:.2f} · vinte {sum(x['won'] for x in forced)/len(forced):.0%}")
        kinds = C.Counter(x["kind"] for x in fs)
        print("   tipi:", dict(kinds.most_common(5)))
    tot = sum(a["scenes"].values())
    print(f"   scene {tot} ({tot/days:.2f}/g):", ", ".join(f"{k} {v}" for k, v in a["scenes"].most_common(10)))
print("\ncause di morte (dal registro):", causes.most_common(8))
dk = C.Counter()
for f in files:
    for x in json.load(open(f)).get("fights", []):
        if x["died"]:
            dk[(x["kind"], "imboscata" if x["forced"] else "scelto", round(x["ratio"], 1))] += 1
print("morti in combattimento (tipo, chi, rapporto):", dk.most_common(12))
print("trame:", intr.most_common(20))
