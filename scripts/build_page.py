"""Собирает страницу: python build_page.py leads.json template.html out.html [call_scripts.json] [reviews.json]"""
import json, os, sys

leads_path, tpl_path, out_path = sys.argv[1:4]
scripts_path = sys.argv[4] if len(sys.argv) > 4 else os.path.join(os.path.dirname(__file__), "call_scripts.json")
reviews_path = sys.argv[5] if len(sys.argv) > 5 else os.path.join(os.path.dirname(leads_path), "reviews.json")

d = json.load(open(leads_path, encoding="utf-8"))
rev = json.load(open(reviews_path, encoding="utf-8")) if os.path.exists(reviews_path) else {}
for i, r in enumerate(d["leads"]):
    r.pop("queries", None)
    r["cats"] = (r.get("cats") or "")[:160]
    if str(i) in rev:
        r["rv"] = rev[str(i)]
# новые компании: «скоро открытие» в 2ГИС или свежая карточка с небольшим числом отзывов
new_path = os.path.join(os.path.dirname(leads_path), "new.json")
# самые свежие 10% карточек 2ГИС (номер карточки растёт со временем)
g_path = os.path.join(os.path.dirname(leads_path), "2gis.json")
ids = sorted(int(i) for i in json.load(open(g_path, encoding="utf-8"))["firms"] if i.startswith("7000000")) if os.path.exists(g_path) else []
FRESH_ID = ids[int(len(ids) * 0.9)] if ids else 0
if os.path.exists(new_path):
    for k, v in json.load(open(new_path, encoding="utf-8")).items():
        r = d["leads"][int(k)]
        if v.get("opening"):
            r["nw"] = {"opening": v.get("opening")}
        elif not v.get("tc") and int(v["id"]) >= FRESH_ID and (v.get("reviews") or 0) <= 20 and (r.get("reviews") or 0) <= 20:
            r["nw"] = {}
# подписи к телефонам и владелец из 2ГИС
ct_path = os.path.join(os.path.dirname(leads_path), "contacts.json")
if os.path.exists(ct_path):
    for k, v in json.load(open(ct_path, encoding="utf-8")).items():
        if v.get("ph") or v.get("legal"):
            d["leads"][int(k)]["ct"] = v
d["scripts"] = json.load(open(scripts_path, encoding="utf-8"))
s = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
t = open(tpl_path, encoding="utf-8").read().replace("__DATA__", s)
open(out_path, "w", encoding="utf-8", newline="\n").write(t)
print(len(t.encode()), "bytes;", sum(1 for r in d["leads"] if "rv" in r), "компаний с отзывами")
