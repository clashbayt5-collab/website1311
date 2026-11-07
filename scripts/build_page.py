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
d["scripts"] = json.load(open(scripts_path, encoding="utf-8"))
s = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\\/")
t = open(tpl_path, encoding="utf-8").read().replace("__DATA__", s)
open(out_path, "w", encoding="utf-8", newline="\n").write(t)
print(len(t.encode()), "bytes;", sum(1 for r in d["leads"] if "rv" in r), "компаний с отзывами")
