"""Склейка 2ГИС + Яндекс, фильтр «без сайта», скоринг, Excel.
python analyze.py DATADIR OUT.xlsx
"""
import json, os, re, sys, urllib.parse
from collections import defaultdict, Counter
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment
from openpyxl.utils import get_column_letter

DATA, OUT = sys.argv[1], sys.argv[2]

from analyze_helpers import classify, digits, norm_name, house, EXCLUDE_RE, niche_by_cats


g = json.load(open(os.path.join(DATA, "2gis.json"), encoding="utf-8"))["firms"]
y = json.load(open(os.path.join(DATA, "yandex.json"), encoding="utf-8"))["orgs"]

recs = []
for f in g.values():
    links = [l.split("|", 1) for l in f.get("links", [])]
    recs.append({"src": "2ГИС", "id": f["id"], "name": f["name"], "addr": f.get("addr") or "",
                 "district": f.get("district", ""), "phones": [p for p in f.get("phones", []) if p],
                 "urls": [u for t, u in links], "cats": f.get("rubrics", ""), "rating": f.get("rating"),
                 "reviews": f.get("reviews") or 0, "hits": f["hits"], "email": f.get("email", ""),
                 "branches": f.get("branches") or 1, "org": f.get("org"),
                 "closed": f.get("status") not in (None, "", "active") if "links" in f else False,
                 "link": "https://2gis.ru/norilsk/firm/" + f["id"], "detailed": "links" in f})
for o in y.values():
    full = o.get("full") or ""
    recs.append({"src": "Яндекс", "id": o["id"], "name": o["name"], "addr": o.get("addr") or "",
                 "district": "Кайеркан" if "Кайеркан" in full else "Талнах" if "Талнах" in full else "",
                 "phones": [p for p in o.get("phones", []) if p],
                 "urls": list(o.get("urls", [])) + [s.split("|", 1)[1] for s in o.get("social", [])],
                 "cats": o.get("cats", ""), "rating": o.get("rating"), "reviews": o.get("reviews") or 0,
                 "hits": o["hits"], "email": "", "branches": 1, "org": None,
                 "closed": (o.get("status") or "open") not in ("open",),
                 "link": f"https://yandex.ru/maps/org/{o.get('seo') or 'org'}/{o['id']}/", "detailed": True})

# --- склейка: общий телефон ИЛИ (имя + номер дома) ---
parent = list(range(len(recs)))
def find(i):
    while parent[i] != i:
        parent[i] = parent[parent[i]]; i = parent[i]
    return i
def union(a, b):
    parent[find(a)] = find(b)

by_key = defaultdict(list)
for i, r in enumerate(recs):
    for p in r["phones"]:
        d = digits(p)
        # общий городской номер типа диспетчерской может склеить лишнее — только мобильные/уникальные
        if d:
            by_key["p" + d].append(i)
    by_key["n" + norm_name(r["name"]) + "|" + house(r["addr"])].append(i)
for ids in by_key.values():
    for j in ids[1:]:
        union(ids[0], j)

groups = defaultdict(list)
for i in range(len(recs)):
    groups[find(i)].append(recs[i])

# доменные имена, которые встречаются у многих разных компаний (федеральные сети) — тоже «сайт»
NICHE_ORDER = ["Стоматология", "Автосервис", "Ремонт и стройка", "Салоны красоты", "Цветы", "Доставка и еда",
               "Медицина и здоровье", "Обучение и дети", "Праздники и фото", "Бытовые услуги", "Гостиницы и досуг",
               "Деловые услуги"]
NICHE_VALUE = {"Стоматология": 10, "Автосервис": 9, "Ремонт и стройка": 9, "Медицина и здоровье": 8,
               "Салоны красоты": 8, "Цветы": 8, "Доставка и еда": 8, "Обучение и дети": 7, "Праздники и фото": 7,
               "Гостиницы и досуг": 7, "Бытовые услуги": 6, "Деловые услуги": 6}
PITCH = {
    "Стоматология": "Цены на услуги, врачи, онлайн-запись, отзывы — пациенты выбирают клинику по сайту; высокий средний чек окупает сайт с 1–2 пациентов",
    "Автосервис": "Прайс на работы, онлайн-запись на время, калькулятор ТО/шиномонтажа — ловит сезонный спрос (шины, подготовка к зиме)",
    "Ремонт и стройка": "Портфолио работ, калькулятор стоимости, заявка на замер — клиенты сравнивают подрядчиков по примерам работ",
    "Медицина и здоровье": "Услуги и цены, специалисты, онлайн-запись, лицензии — доверие и поток записей без звонков",
    "Салоны красоты": "Прайс, мастера, портфолио и онлайн-запись 24/7 — меньше пропущенных звонков, больше записей",
    "Цветы": "Каталог букетов с ценами и онлайн-оплатой, доставка — заказы приходят 24/7, особенно к праздникам",
    "Доставка и еда": "Меню с корзиной и онлайн-оплатой без комиссии агрегаторов (экономия 20–35% с заказа)",
    "Обучение и дети": "Расписание, направления, цены, запись на пробное занятие — родители выбирают по сайту",
    "Праздники и фото": "Портфолио, пакеты и цены, бронирование дат — сайт = витрина работ",
    "Гостиницы и досуг": "Фото, цены и прямое бронирование без комиссии Booking/Суточно (экономия 15–20%)",
    "Бытовые услуги": "Прайс, заявка онлайн, отслеживание статуса — клиенты из поиска «ремонт … Норильск»",
    "Деловые услуги": "Услуги, кейсы, заявка/консультация онлайн — доверие и входящие лиды из поиска",
}

def district_label(d):
    d = d or ""
    if "Кайеркан" in d: return "Кайеркан"
    if "Талнах" in d: return "Талнах"
    if "Оганер" in d: return "Оганер"
    return "Норильск (центр)"


rows, with_site = [], []
for grp in groups.values():
    names = Counter(r["name"] for r in grp)
    best = max(grp, key=lambda r: (r["src"] == "2ГИС", len(r["name"] or "")))
    hits = {}
    for r in grp:
        for h in r["hits"]:
            hits.setdefault(h["niche"], set()).add(h["q"])
    sites, socials, landings, bookings = set(), set(), set(), set()
    linkmap = {}
    for r in grp:
        for u in r["urls"]:
            if "google." in u or "goo.gl" in u: continue
            k, v = classify(u)
            if k == "site": sites.add(v)
            elif k == "social": socials.add(v)
            elif k == "landing": landings.add(v)
            elif k == "booking": bookings.add(v)
            if k in ("social", "landing", "booking") and v not in ("2ГИС", "Яндекс"):
                url = u[u.index("?http") + 1:] if "?http" in u else u
                if v == "WhatsApp": url = url.split("?")[0]
                if v == "Telegram" and re.search(r"t\.me/\+?\d{10,}", url): v = "Telegram (номер)"
                linkmap.setdefault(v, url if re.match(r"^\w+://", url) else "https://" + url)
    phones, seen = [], set()
    for r in grp:
        for p in r["phones"]:
            d = digits(p)
            if d and d not in seen:
                seen.add(d); phones.append(p.replace("‒", "-"))
    rating = max([r["rating"] for r in grp if r["rating"]] or [None], key=lambda x: x or 0)
    reviews = max(r["reviews"] or 0 for r in grp)
    closed = all(r["closed"] for r in grp)
    addrs = []
    for r in sorted(grp, key=lambda r: r["src"] != "2ГИС"):
        words = [w for w in re.findall(r"[а-яёa-z]{4,}", (r["addr"] or "").lower())
                 if w not in ("улица", "проспект", "просп", "переулок", "проезд", "площадь", "норильск", "корп", "этаж", "район")]
        h = (house(r["addr"]), words[0][:5] if words else "")
        if r["addr"] and h not in [x[0] for x in addrs]:
            addrs.append((h, r["addr"]))
    addrs_str = "; ".join(a for _, a in addrs[:6]) + (f" (+ ещё {len(addrs) - 6})" if len(addrs) > 6 else "")
    branches = max([r["branches"] or 1 for r in grp] + [len(addrs)])
    srcs = sorted({r["src"] for r in grp})
    niches = sorted(hits, key=lambda n: -NICHE_VALUE.get(n, 5))
    allcats = ", ".join(sorted({c.strip() for r in grp for c in (r["cats"] or "").split(",") if c.strip()}))
    main = niche_by_cats(allcats, best["name"])
    if not main:
        continue  # рубрики не относятся ни к одной целевой нише — шум поиска
    rec = {
        "name": best["name"], "niche": main, "all_niches": ", ".join(niches),
        "queries": ", ".join(sorted({q for s in hits.values() for q in s})),
        "cats": max((r["cats"] for r in grp), key=len), "addr": addrs_str,
        "district": district_label(next((r["district"] for r in grp if r["district"]), "")),
        "phones": ", ".join(phones), "email": next((r["email"] for r in grp if r["email"]), ""),
        "linkmap": linkmap, "socials": ", ".join(sorted(socials)), "landing": ", ".join(sorted(landings)),
        "booking": ", ".join(sorted(bookings)), "sites": ", ".join(sorted(sites)),
        "rating": rating, "reviews": reviews, "branches": branches, "srcs": " + ".join(srcs),
        "link2gis": next((r["link"] for r in grp if r["src"] == "2ГИС"), ""),
        "linkya": next((r["link"] for r in grp if r["src"] == "Яндекс"), ""),
        "closed": closed, "detailed": all(r["detailed"] for r in grp if r["src"] == "2ГИС"),
    }
    if closed or not phones and not socials:
        continue
    if EXCLUDE_RE.search(rec["name"] or "") or EXCLUDE_RE.search(rec["cats"] or ""):
        continue
    if sites:
        with_site.append(rec); continue
    if not rec["detailed"] and rec["srcs"] == "2ГИС":
        continue  # без деталей нельзя утверждать «нет сайта»
    # --- скоринг потенциала (0–100) ---
    s = NICHE_VALUE.get(main, 5) * 3                    # ценность сайта для ниши: до 30
    s += min(reviews, 300) / 300 * 25                   # живой поток клиентов: до 25
    s += 10 if (rating or 0) >= 4.5 else 5 if (rating or 0) >= 4 else 0
    s += 10 if socials else 0                           # уже ведёт маркетинг, но без сайта
    s += 8 if landings or bookings else 0               # «костыль» вместо сайта — понятная боль
    s += 7 if branches > 1 else 0
    s += 5 if len(srcs) == 2 else 0                     # есть на обеих картах — активный бизнес
    s += 5 if len(hits) > 1 or sum(len(v) for v in hits.values()) >= 3 else 0
    rec["score"] = round(min(s, 100))
    rec["prio"] = "A — горячий" if s >= 60 else "B — тёплый" if s >= 45 else "C — холодный"
    why = []
    if reviews >= 50: why.append(f"{reviews} отзывов — стабильный поток клиентов")
    if socials: why.append(f"ведут {', '.join(sorted(socials))}, но сайта нет")
    if landings: why.append(f"вместо сайта {', '.join(sorted(landings))}")
    if bookings: why.append(f"зависят от площадок: {', '.join(sorted(bookings))}")
    if branches > 1: why.append(f"{branches} филиала(ов)")
    if not socials and not landings: why.append("в интернете только карточка на картах")
    rec["why"] = "; ".join(why)
    rec["pitch"] = PITCH.get(main, "")
    rows.append(rec)

rows.sort(key=lambda r: (-r["score"], -r["reviews"]))

# ---------------- Excel ----------------
wb = Workbook()
HDR = PatternFill("solid", fgColor="1F4E78"); HF = Font(color="FFFFFF", bold=True)
PF = {"A": PatternFill("solid", fgColor="C6EFCE"), "B": PatternFill("solid", fgColor="FFEB9C"),
      "C": PatternFill("solid", fgColor="F2F2F2")}
cols = [("Приоритет", "prio", 13), ("Балл", "score", 6), ("Ниша", "niche", 18), ("Название", "name", 34),
        ("Категории", "cats", 32), ("Адрес", "addr", 30), ("Район", "district", 14), ("Телефоны", "phones", 30),
        ("Email", "email", 22), ("Соцсети/мессенджеры", "socials", 24), ("Вместо сайта", "landing", 14),
        ("Площадки/запись", "booking", 18), ("Рейтинг", "rating", 8), ("Отзывов", "reviews", 8),
        ("Филиалов", "branches", 8), ("Где найдена", "srcs", 14), ("Почему нужен сайт", "why", 45),
        ("Аргумент для продажи", "pitch", 60), ("Подзапросы", "queries", 30), ("2ГИС", "link2gis", 20),
        ("Яндекс.Карты", "linkya", 20)]


def sheet(ws, data, columns, prio=True):
    for c, (h, _, w) in enumerate(columns, 1):
        cell = ws.cell(1, c, h); cell.fill = HDR; cell.font = HF
        cell.alignment = Alignment(wrap_text=True, vertical="center")
        ws.column_dimensions[get_column_letter(c)].width = w
    for r, rec in enumerate(data, 2):
        for c, (_, k, _) in enumerate(columns, 1):
            v = rec.get(k, "")
            cell = ws.cell(r, c, v)
            if k in ("link2gis", "linkya") and v:
                cell.hyperlink = v; cell.value = "открыть"; cell.font = Font(color="0563C1", underline="single")
        if prio and rec.get("prio"):
            ws.cell(r, 1).fill = PF[rec["prio"][0]]
    ws.freeze_panes = "E2"
    ws.auto_filter.ref = ws.dimensions


ws = wb.active; ws.title = "Сводка"
ws["A1"] = "Компании Норильска без сайта — 2ГИС + Яндекс.Карты"; ws["A1"].font = Font(bold=True, size=14)
ws["A2"] = f"Проверено {len(groups)} уникальных компаний; без собственного сайта: {len(rows)}"
ws["A4"] = "Ниша"; ws["B4"] = "Без сайта"; ws["C4"] = "A — горячие"; ws["D4"] = "B — тёплые"; ws["E4"] = "C"
for c in "ABCDE":
    ws[c + "4"].fill = HDR; ws[c + "4"].font = HF
ws.column_dimensions["A"].width = 24
for i, n in enumerate(NICHE_ORDER, 5):
    sub = [r for r in rows if r["niche"] == n]
    ws.cell(i, 1, n); ws.cell(i, 2, len(sub))
    for j, p in enumerate("ABC", 3):
        ws.cell(i, j, sum(1 for r in sub if r["prio"][0] == p))
k = len(NICHE_ORDER) + 6
notes = [
    "Как читать:",
    "«Без сайта» = ни в 2ГИС, ни в Яндексе нет собственного домена. Соцсети, Taplink, DIKIDI/YCLIENTS, Avito, агрегаторы — сайтом НЕ считаются.",
    "Балл 0–100: ценность сайта для ниши (до 30) + число отзывов (до 25) + рейтинг + есть соцсети + «костыль» вместо сайта + филиалы + есть на обеих картах.",
    "A (60+) — звонить в первую очередь: живой бизнес с клиентами и маркетингом, но без сайта.",
    "Закрытые и компании без телефона/соцсетей исключены.",
]
for i, t in enumerate(notes):
    ws.cell(k + i, 1, t)

sheet(wb.create_sheet("Все без сайта"), rows, cols)
for n in NICHE_ORDER:
    sub = [r for r in rows if r["niche"] == n]
    if sub:
        sheet(wb.create_sheet(n[:31]), sub, cols)
wb.save(OUT)
if len(sys.argv) > 3:
    keep = ["prio", "score", "niche", "name", "cats", "addr", "district", "phones", "email", "linkmap", "rating",
            "reviews", "branches", "srcs", "why", "link2gis", "linkya", "queries"]
    out = [{k: r.get(k) for k in keep} for r in rows]
    json.dump({"leads": out, "pitch": PITCH, "order": NICHE_ORDER, "checked": len(groups), "site_by_niche": Counter(r["niche"] for r in with_site)},
              open(sys.argv[3], "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
print("groups", len(groups), "no-site leads", len(rows), "with site", len(with_site))
print(Counter(r["prio"] for r in rows))
print(Counter(r["niche"] for r in rows).most_common())
