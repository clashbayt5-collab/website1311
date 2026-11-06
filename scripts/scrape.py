"""Сбор компаний Норильска из 2ГИС и Яндекс.Карт по нишам/подзапросам.
python scrape.py 2gis|yandex OUTDIR
Результат сохраняется инкрементально в OUTDIR/<src>.json (можно перезапускать — продолжит).
"""
import json, os, re, sys, time, random, html, urllib.parse
import requests

QUERIES = {
    "Цветы": ["цветы", "доставка цветов", "букеты", "цветочный салон", "воздушные шары", "сухоцветы", "флорист"],
    "Автосервис": ["автосервис", "шиномонтаж", "автомойка", "кузовной ремонт", "автоэлектрик", "развал схождение",
                   "детейлинг", "тонировка автомобилей", "ремонт двигателя", "автозапчасти", "эвакуатор",
                   "ремонт дизельных двигателей", "автостекла", "ремонт ходовой", "ремонт акпп", "покраска авто"],
    "Стоматология": ["стоматология", "стоматологическая клиника", "детская стоматология", "имплантация зубов",
                     "ортодонт", "зубопротезирование", "отбеливание зубов"],
    "Салоны красоты": ["салон красоты", "парикмахерская", "барбершоп", "маникюр", "ногтевая студия", "косметология",
                       "массаж", "наращивание ресниц", "оформление бровей", "солярий", "тату салон", "эпиляция",
                       "spa салон", "визажист"],
    "Доставка и еда": ["доставка еды", "суши", "пицца", "доставка обедов", "шаурма", "доставка воды",
                       "торты на заказ", "кондитерская", "пекарня", "кейтеринг"],
    "Ремонт и стройка": ["ремонт квартир", "натяжные потолки", "пластиковые окна", "двери", "мебель на заказ",
                         "кухни на заказ", "сантехник", "электрик", "жалюзи", "ремонт ванной", "отделочные работы"],
    "Бытовые услуги": ["клининг", "химчистка", "ремонт телефонов", "ремонт бытовой техники", "ремонт компьютеров",
                       "ателье", "ремонт обуви", "изготовление ключей", "грузоперевозки", "грузчики",
                       "ритуальные услуги", "прачечная", "ремонт часов"],
    "Медицина и здоровье": ["медицинский центр", "психолог", "массажный кабинет", "оптика", "ветеринарная клиника",
                            "груминг", "лабораторные анализы", "логопед", "мануальный терапевт"],
    "Обучение и дети": ["детский центр", "автошкола", "курсы английского", "репетитор", "танцевальная студия",
                        "фитнес", "йога", "частный детский сад", "музыкальная школа", "развивающий центр"],
    "Праздники и фото": ["фотостудия", "фотограф", "организация праздников", "ведущий", "аниматоры",
                         "свадебный салон", "прокат костюмов", "видеосъемка"],
    "Гостиницы и досуг": ["посуточно квартиры", "гостиница", "сауна", "баня", "кальянная", "кафе",
                          "банкетный зал", "квест", "компьютерный клуб"],
    "Деловые услуги": ["юридические услуги", "бухгалтерские услуги", "агентство недвижимости", "страхование",
                       "типография", "наружная реклама", "курьерская доставка", "кадастровые работы"],
}
CITY_RE = re.compile(r"Норильск|Талнах|Кайеркан|Оганер|Снежногорск")
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/140.0 Safari/537.36"
S = requests.Session()
S.headers.update({"User-Agent": UA, "Accept-Language": "ru-RU,ru;q=0.9"})


def get(url, tries=3):
    for i in range(tries):
        try:
            r = S.get(url, timeout=30)
            if r.status_code == 200:
                return r.text
            if r.status_code == 404:
                return None
            print("HTTP", r.status_code, url, flush=True)
        except Exception as e:
            print("ERR", e, url, flush=True)
        time.sleep(5 * (i + 1))
    return None


def pause(a, b):
    time.sleep(random.uniform(a, b))


# ---------------- 2ГИС ----------------
def gis_state(h):
    a = h.find("var initialState = JSON.parse('")
    if a < 0:
        return None
    s = a + len("var initialState = JSON.parse('")
    e = h.find("');", s)
    raw = h[s:e]
    # JS single-quoted literal -> python str
    txt = raw.encode("latin-1", "backslashreplace").decode("unicode_escape") if False else js_unescape(raw)
    return json.loads(txt)


def js_unescape(raw):
    out = []
    i = 0
    n = len(raw)
    while i < n:
        c = raw[i]
        if c == "\\" and i + 1 < n:
            d = raw[i + 1]
            if d == "u":
                out.append(chr(int(raw[i + 2:i + 6], 16))); i += 6; continue
            if d == "x":
                out.append(chr(int(raw[i + 2:i + 4], 16))); i += 4; continue
            out.append({"n": "\n", "t": "\t", "r": "\r", "b": "\b", "f": "\f", "0": "\0"}.get(d, d)); i += 2; continue
        out.append(c); i += 1
    return "".join(out)


def scrape_2gis(path):
    db = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {"firms": {}, "done_q": []}
    save = lambda: json.dump(db, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    for niche, qs in QUERIES.items():
        for q in qs:
            if q in db["done_q"]:
                continue
            for pg in range(1, 25):
                url = "https://2gis.ru/norilsk/search/" + urllib.parse.quote(q) + (f"/page/{pg}" if pg > 1 else "")
                h = get(url)
                st = gis_state(h) if h else None
                if not st:
                    break
                added = 0
                for fid, v in st["data"]["entity"]["profile"].items():
                    x = v.get("data") or {}
                    if x.get("type") != "branch":
                        continue
                    city = "|".join(a.get("name", "") for a in x.get("adm_div", []))
                    if not CITY_RE.search(city):
                        continue
                    f = db["firms"].setdefault(fid, {
                        "id": fid, "name": x.get("name"), "addr": x.get("address_name"),
                        "district": next((a["name"] for a in x.get("adm_div", []) if a.get("type") == "district"), ""),
                        "org": (x.get("org") or {}).get("id"),
                        "branches": (x.get("org") or {}).get("branch_count"),
                        "rating": (x.get("reviews") or {}).get("general_rating"),
                        "reviews": (x.get("reviews") or {}).get("general_review_count"),
                        "rubrics": ", ".join(r["name"] for r in x.get("rubrics", [])),
                        "hits": []})
                    if not any(hh["q"] == q for hh in f["hits"]):
                        f["hits"].append({"niche": niche, "q": q}); added += 1
                print(f"2gis {q} p{pg} +{added} total={len(db['firms'])}", flush=True)
                if added == 0:
                    break
                pause(0.8, 1.6)
            db["done_q"].append(q); save()
    # детали карточек
    # пропускаем тех, у кого в Яндексе уже есть настоящий сайт — нам нужны только компании без сайта
    skip = set()
    ypath = os.path.join(os.path.dirname(path), "yandex.json")
    if os.path.exists(ypath):
        import analyze_helpers as ah
        for o in json.load(open(ypath, encoding="utf-8"))["orgs"].values():
            if any(ah.classify(u)[0] == "site" for u in o.get("urls", [])):
                skip.add(ah.norm_name(o["name"]) + "|" + ah.house(o.get("addr")))
    for f in db["firms"].values():
        if "links" not in f and skip:
            import analyze_helpers as ah
            if ah.norm_name(f["name"]) + "|" + ah.house(f.get("addr")) in skip:
                f["links"] = ["website|yandex-has-site"]; f["skipped"] = True
            elif ah.EXCLUDE_RE.search(f["name"] or "") or ah.EXCLUDE_RE.search(f.get("rubrics") or "") \
                    or not ah.niche_by_cats(f.get("rubrics"), f["name"]):
                f["links"] = []; f["phones"] = []; f["skipped"] = "irrelevant"
    todo = [f for f in db["firms"].values() if "links" not in f]
    print(f"2gis details: skip {sum(1 for f in db['firms'].values() if f.get('skipped'))} (сайт есть в Яндексе), todo {len(todo)}", flush=True)
    for i, f in enumerate(todo):
        h = get("https://2gis.ru/norilsk/firm/" + f["id"])
        st = gis_state(h) if h else None
        x = ((st or {}).get("data", {}).get("entity", {}).get("profile", {}).get(f["id"]) or {}).get("data") or {}
        cs = [c for g in x.get("contact_groups", []) for c in g.get("contacts", [])]
        f["phones"] = [c.get("text") for c in cs if c.get("type") == "phone"]
        f["email"] = " ".join(c.get("text") or c.get("value") or "" for c in cs if c.get("type") == "email")
        f["links"] = [c["type"] + "|" + (c.get("url") or c.get("text") or "") for c in cs
                      if c.get("type") not in ("phone", "email", "fax")]
        f["status"] = x.get("status")
        if i % 25 == 0:
            print(f"2gis details {i}/{len(todo)}", flush=True); save()
        pause(0.4, 0.8)
    save()
    print("2GIS DONE", flush=True)


# ---------------- Яндекс ----------------
STATE_RE = re.compile(r'<script[^>]*class="state-view"[^>]*>(.*?)</script>', re.S)


def scrape_yandex(path):
    db = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else {"orgs": {}, "done_q": []}
    save = lambda: json.dump(db, open(path, "w", encoding="utf-8"), ensure_ascii=False)
    for niche, qs in QUERIES.items():
        for q in qs:
            if q in db["done_q"]:
                continue
            for pg in range(1, 10):
                url = "https://yandex.ru/maps/11311/norilsk/search/" + urllib.parse.quote(q) + "/" + (f"?page={pg}" if pg > 1 else "")
                h = get(url)
                if not h:
                    break
                m = STATE_RE.search(h)
                if not m:
                    if "showcaptcha" in h or "SmartCaptcha" in h:
                        print("CAPTCHA — пауза 120с", flush=True); time.sleep(120); continue
                    print("no state", q, pg, flush=True); break
                j = json.loads(html.unescape(m.group(1)) if m.group(1).lstrip().startswith("{&") else m.group(1))
                try:
                    r = j["stack"][0]["results"]
                except Exception:
                    break
                items = r.get("items") or []
                added = 0
                for it in items:
                    if it.get("type") != "business":
                        continue
                    fa = it.get("fullAddress") or it.get("address") or ""
                    if not CITY_RE.search(fa):
                        continue
                    o = db["orgs"].setdefault(it["id"], {
                        "id": it["id"], "name": it.get("title"), "addr": it.get("address"), "full": fa,
                        "urls": it.get("urls") or [],
                        "phones": [p.get("number") for p in it.get("phones") or []],
                        "social": [s.get("type") + "|" + (s.get("href") or "").split("?")[0] for s in it.get("socialLinks") or []],
                        "cats": ", ".join(c.get("name", "") for c in it.get("categories") or []),
                        "rating": (it.get("ratingData") or {}).get("ratingValue"),
                        "reviews": (it.get("ratingData") or {}).get("ratingCount"),
                        "status": it.get("status"), "seo": it.get("seoname"), "hits": []})
                    if not any(hh["q"] == q for hh in o["hits"]):
                        o["hits"].append({"niche": niche, "q": q}); added += 1
                print(f"yandex {q} p{pg} +{added} ({len(items)}/{r.get('totalResultCount')}) total={len(db['orgs'])}", flush=True)
                pause(2.0, 3.5)
                if len(items) < 25:
                    break
            db["done_q"].append(q); save()
    save()
    print("YANDEX DONE", flush=True)


if __name__ == "__main__":
    src, out = sys.argv[1], sys.argv[2]
    if len(sys.argv) > 3 and sys.argv[3] == "pass2":
        # второй проход: ключевые подзапросы + районы (Талнах, Кайеркан) + синонимы — добирает пропущенных
        extra = {"Цветы": ["цветочный магазин", "флористика"], "Автосервис": ["СТО", "автомастерская", "шиномонтажная мастерская"],
                 "Стоматология": ["стоматолог", "зубной врач"], "Салоны красоты": ["ногти", "мастер маникюра", "студия красоты", "ресницы"],
                 "Доставка и еда": ["роллы", "доставка пиццы", "фастфуд"], "Ремонт и стройка": ["строительная компания", "ремонт под ключ"],
                 "Бытовые услуги": ["мастер на час", "сервисный центр"], "Медицина и здоровье": ["клиника", "ветеринар"],
                 "Обучение и дети": ["курсы", "школа танцев", "спортивная секция"], "Праздники и фото": ["шары", "праздничное агентство"],
                 "Гостиницы и досуг": ["хостел", "мини-гостиница"], "Деловые услуги": ["юрист", "бухгалтер", "риелтор"]}
        QUERIES.clear()
        base = {"Цветы": ["цветы"], "Автосервис": ["автосервис", "шиномонтаж", "автомойка"], "Стоматология": ["стоматология"],
                "Салоны красоты": ["салон красоты", "маникюр", "парикмахерская"], "Доставка и еда": ["доставка еды", "суши"],
                "Ремонт и стройка": ["ремонт квартир"], "Бытовые услуги": ["ремонт телефонов"], "Обучение и дети": ["детский центр"]}
        for n, qs in extra.items():
            QUERIES[n] = qs + [q + " " + d for q in base.get(n, []) for d in ("Талнах", "Кайеркан")]
    os.makedirs(out, exist_ok=True)
    (scrape_2gis if src == "2gis" else scrape_yandex)(os.path.join(out, src + ".json"))
