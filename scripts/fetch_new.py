"""Отметки «скоро открытие» и свежесть карточек 2ГИС для самых новых компаний базы.
python fetch_new.py  ->  data/new.json  {lead_index: {"id":..., "opening": "YYYY-MM-DD"|None, "closed": flag}}
"""
import json, time, random
import scrape

cand = json.load(open("data/new_cand.json"))
out = {}
for k, (li, fid) in enumerate(cand):
    h = scrape.get("https://2gis.ru/norilsk/firm/" + fid)
    st = scrape.gis_state(h) if h else None
    x = ((st or {}).get("data", {}).get("entity", {}).get("profile", {}).get(fid) or {}).get("data") or {}
    fl = x.get("flags") or {}
    opening = None
    for p in fl.get("temporary_closed_parameters") or []:
        if p.get("name") == "opening_day":
            opening = p.get("value")
    out[str(li)] = {"id": fid, "tc": fl.get("temporary_closed"), "opening": opening,
                    "reviews": (x.get("reviews") or {}).get("general_review_count")}
    if k % 20 == 0:
        print(k, len(cand), flush=True)
        json.dump(out, open("data/new.json", "w", encoding="utf-8"), ensure_ascii=False)
    time.sleep(random.uniform(0.5, 1.0))
json.dump(out, open("data/new.json", "w", encoding="utf-8"), ensure_ascii=False)
print("DONE", sum(1 for v in out.values() if v["tc"]), "с отметками")
