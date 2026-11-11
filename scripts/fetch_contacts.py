"""Подписи к телефонам и данные о владельце из карточек 2ГИС.
python fetch_contacts.py  ->  data/contacts.json  {lead_index: {"ph": [[номер, подпись]], "legal": "ИП ..."}}
Возобновляемый: уже обработанные компании пропускаются.
"""
import json, os, re, time, random
import scrape

L = json.load(open("data/leads.json", encoding="utf-8"))["leads"]
path = "data/contacts.json"
out = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {}
LEGAL = re.compile(r"\b(ИП|ООО|АО|ОАО|ЗАО|ПАО)\s+[«\"]?[А-ЯЁA-Z][^,;.()]{2,60}")
todo = [(i, l["link2gis"].rsplit("/", 1)[1]) for i, l in enumerate(L) if l.get("link2gis") and str(i) not in out]
print("todo", len(todo), flush=True)
for k, (i, fid) in enumerate(todo):
    h = scrape.get("https://2gis.ru/norilsk/firm/" + fid)
    st = scrape.gis_state(h) if h else None
    x = ((st or {}).get("data", {}).get("entity", {}).get("profile", {}).get(fid) or {}).get("data") or {}
    ph = []
    for g in x.get("contact_groups", []):
        gname = g.get("name") or g.get("comment") or ""
        for c in g.get("contacts", []):
            if c.get("type") == "phone":
                ph.append([c.get("text") or c.get("value"), (c.get("comment") or gname or "").strip()])
    blob = json.dumps(x.get("ads") or {}, ensure_ascii=False) + " " + json.dumps(x.get("context") or {}, ensure_ascii=False)
    m = LEGAL.search(blob)
    out[str(i)] = {"ph": ph, "legal": m.group(0).strip() if m else ""}
    if k % 50 == 0:
        print(k, len(todo), flush=True)
        json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    time.sleep(random.uniform(0.4, 0.8))
json.dump(out, open(path, "w", encoding="utf-8"), ensure_ascii=False)
print("DONE", sum(1 for v in out.values() if any(p[1] for p in v["ph"])), "с подписями,",
      sum(1 for v in out.values() if v["legal"]), "с юрлицом", flush=True)
