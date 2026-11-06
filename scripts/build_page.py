import json, sys
d = json.load(open(sys.argv[1], encoding="utf-8"))
for r in d["leads"]:
    r.pop("queries", None)
    r["cats"] = (r.get("cats") or "")[:160]
s = json.dumps(d, ensure_ascii=False, separators=(",", ":")).replace("</", "<\/")
t = open(sys.argv[2], encoding="utf-8").read().replace("__DATA__", s)
open(sys.argv[3], "w", encoding="utf-8").write(t)
print(len(t.encode()))
