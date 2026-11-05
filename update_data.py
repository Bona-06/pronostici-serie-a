#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Aggiorna data.json con risultati e calendario della Serie A.

Fonte dati: API pubblica di ESPN (nessuna chiave/API key richiesta).
Il programma:
  1. legge dal calendario ESPN le date delle giornate;
  2. scarica i risultati delle partite gia' giocate -> classifica (V/N/P, GF, GS);
  3. scarica le partite dei prossimi 10 giorni -> prossima giornata per l'app;
  4. scrive tutto in data.json, che l'app (index.html) legge automaticamente.

Esecuzione locale (test):   python update_data.py
"""
import json
import time
import datetime
import urllib.request

LEAGUE = "ita.1"
BASE = "https://site.api.espn.com/apis/site/v2/sports/soccer/" + LEAGUE + "/scoreboard"
HEADERS = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}

# Nomi ESPN -> nomi corti usati dall'app
ALIAS = {
    "INTER MILAN": "Inter", "AC MILAN": "Milan", "AS ROMA": "Roma",
    "SSC NAPOLI": "Napoli", "US LECCE": "Lecce", "HELLAS VERONA": "Verona",
    "ACF FIORENTINA": "Fiorentina", "GENOA CFC": "Genoa", "FC INTERNAZIONALE MILANO": "Inter",
}

def norm(name):
    n = " ".join(str(name).upper().split())
    if n in ALIAS:
        return ALIAS[n]
    for pre in ("AC ", "AS ", "US ", "SSC ", "AFC ", "FC "):
        if n.startswith(pre):
            n = n[len(pre):]
    return n.strip().title()

def get_json(url):
    req = urllib.request.Request(url, headers=HEADERS)
    with urllib.request.urlopen(req, timeout=30) as r:
        return json.loads(r.read().decode("utf-8"))

def main():
    today = datetime.date.today()

    # 1. calendario: elenco date in cui si gioca
    cal = get_json(BASE)["leagues"][0]["calendar"]
    dates = sorted({datetime.datetime.strptime(d[:10], "%Y-%m-%d").date() for d in cal})

    stats = {}       # squadra -> {gf, ga, w, d, l}
    fixtures = []    # partite future

    def team(t):
        return stats.setdefault(t, {"gf": 0, "ga": 0, "w": 0, "d": 0, "l": 0})

    # 2. scarico giornata per giornata
    for d in dates:
        if d > today + datetime.timedelta(days=10):
            continue
        url = BASE + "?dates=" + d.strftime("%Y%m%d") + "&limit=400"
        try:
            day = get_json(url)
        except Exception as e:
            print("Salto il", d, "->", e)
            continue
        for ev in day.get("events", []):
            comp = ev["competitions"][0]
            home = away = None
            hg = ag = None
            for c in comp.get("competitors", []):
                nm = norm(c["team"]["displayName"])
                if c.get("homeAway") == "home":
                    home = nm
                    try: hg = int(c.get("score"))
                    except (TypeError, ValueError): pass
                else:
                    away = nm
                    try: ag = int(c.get("score"))
                    except (TypeError, ValueError): pass
            if not home or not away:
                continue
            done = comp.get("status", {}).get("type", {}).get("completed", False)
            if done and hg is not None and ag is not None:
                H, A = team(home), team(away)
                H["gf"] += hg; H["ga"] += ag
                A["gf"] += ag; A["ga"] += hg
                if hg > ag:   H["w"] += 1; A["l"] += 1
                elif hg < ag: A["w"] += 1; H["l"] += 1
                else:         H["d"] += 1; A["d"] += 1
            elif d >= today:
                fixtures.append({"date": str(d), "home": home, "away": away})
        time.sleep(0.3)  # educazione verso il server

    # 3. pulizia fixture: uniche, ordinate, prime 12
    seen, clean = set(), []
    for f in sorted(fixtures, key=lambda x: (x["date"], x["home"])):
        key = (f["home"], f["away"])
        if key in seen:
            continue
        seen.add(key)
        clean.append(f)
    clean = clean[:12]

    out = {
        "lastUpdate": str(today),
        "teams": stats,
        "next": [[f["home"], f["away"]] for f in clean],
    }
    with open("data.json", "w", encoding="utf-8") as fh:
        json.dump(out, fh, ensure_ascii=False, indent=1)

    print("Squadre:", len(stats),
          "| Partite giocate:", sum(t["w"] + t["d"] + t["l"] for t in stats) // 2,
          "| Prossime partite:", len(clean))
    for f in clean:
        print("  ", f["date"], f["home"], "-", f["away"])

if __name__ == "__main__":
    main()
