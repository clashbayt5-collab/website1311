import re, urllib.parse

# не «свой сайт»: соцсети, мессенджеры, агрегаторы, конструкторы-визитки
SOCIAL = {
    "t.me": "Telegram", "telegram.me": "Telegram", "vk.com": "VK", "vk.ru": "VK", "vk.cc": "VK",
    "instagram.com": "Instagram", "ok.ru": "OK", "wa.me": "WhatsApp", "api.whatsapp.com": "WhatsApp",
    "whatsapp.com": "WhatsApp", "viber.com": "Viber", "max.ru": "MAX", "youtube.com": "YouTube",
    "youtu.be": "YouTube", "rutube.ru": "RuTube", "dzen.ru": "Дзен", "tiktok.com": "TikTok",
    "facebook.com": "Facebook",
}
LANDING = {"taplink.cc": "Taplink", "taplink.ws": "Taplink", "taplink.at": "Taplink", "taplink.ru": "Taplink",
           "hipolink.me": "Hipolink", "hipolink.net": "Hipolink", "linktr.ee": "Linktree", "mssg.me": "mssg.me",
           "wbiz.me": "wbiz", "tapy.me": "Tapy", "msg.link": "msg.link", "bio.link": "bio.link",
           "clck.ru": "короткая ссылка", "menuquickresto.ru": "QR-меню", "deliveryguru.ru": "QR-меню",
           "qr-menu.ru": "QR-меню", "menu.ru": "QR-меню", "tapmenu.ru": "QR-меню", "mst.link": "короткая ссылка"}

# кому сайт не продать: госучреждения, банки, почта, федеральные сети
EXCLUDE_RE = re.compile(
    r"\b(МБДОУ|МАДОУ|МКДОУ|МБОУ|МАОУ|МКОУ|МБУ|МАУ|МКУ|МБУК|МАУК|ГБУЗ|КГБУЗ|КГБУ|КГКУ|ФГБУ|ФГУП|ФКУ|ФГБОУ|ГУ МВД|ОМВД|ПАО|АО)\b"
    r"|поликлиник|больниц|станция скорой|диспансер|роддом|родильный|Единой России|Единая Россия|партия|Дом культуры|Дворец культуры|библиотек|муниципальн|государствен|Почта России|почтовое отделение|отделение почт|банкомат|Сбер|ВТБ|Альфа-Банк|"
    r"Газпромбанк|Россельхозбанк|Совкомбанк|Т-Банк|Тинькофф|МФЦ|Мои документы|Пенсионн|Социальный фонд|ИФНС|"
    r"Росреестр|прокуратур|полици|администраци|Норникель|Норильский никель|Заполярн(ый|ого) филиал|"
    r"Пятёрочка|Пятерочка|Магнит|Красное&Белое|Бристоль|DNS|М\.Видео|Эльдорадо|Wildberries|Ozon|Озон|СДЭК|DPD|Boxberry|"
    r"Додо|Вкусно — и точка|Burger King|KFC|Ростикс|Fix Price|Светофор|Спортмастер|Детский мир|Инвитро|Гемотест|Хеликс|КДЛ|"
    r"МТС|Мегафон|Билайн|Tele2|Ростелеком|Ингосстрах|РЕСО|Росгосстрах|СОГАЗ|АльфаСтрахование",
    re.I)
BOOKING = {"dikidi.net": "DIKIDI", "dikidi.ru": "DIKIDI", "dikidi.app": "DIKIDI", "yclients.com": "YCLIENTS",
           "sonline.su": "Sonline", "arnica.pro": "Arnica", "beautybox.ru": "Beautybox", "easyweek.io": "EasyWeek",
           "booking.com": "Booking", "ostrovok.ru": "Ostrovok", "sutochno.ru": "Суточно.ру", "avito.ru": "Avito",
           "uslugi.yandex.ru": "Яндекс Услуги", "eda.yandex.ru": "Яндекс Еда", "eda.yandex": "Яндекс Еда",
           "market.yandex.ru": "Яндекс Маркет", "yandex.ru": "Яндекс", "ya.ru": "Яндекс",
           "delivery-club.ru": "Delivery Club", "ozon.ru": "Ozon", "wildberries.ru": "WB", "profi.ru": "Профи",
           "2gis.ru": "2ГИС", "chibbis.ru": "Chibbis", "zoon.ru": "Zoon",
           "prodoctorov.ru": "ПроДокторов", "napopravku.ru": "НаПоправку", "sberhealth.ru": "СберЗдоровье",
           "flowwow.com": "Flowwow", "flowwow.ru": "Flowwow", "kudago.com": "KudaGo", "afisha.ru": "Афиша",
           "tvil.ru": "Твил", "101hotels.com": "101Hotels", "hh.ru": "hh.ru", "gosuslugi.ru": "Госуслуги"}


def domain(u):
    u = (u or "").strip()
    if not u:
        return ""
    if "?http" in u:  # редирект 2ГИС link.2gis.ru/...?http://real
        u = u[u.index("?http") + 1:]
    if not re.match(r"^\w+://", u):
        u = "http://" + u
    d = urllib.parse.urlparse(u).netloc.lower().split(":")[0]
    return d[4:] if d.startswith("www.") else d


def classify(u):
    d = domain(u)
    if not d:
        return None, None
    for table, kind in ((SOCIAL, "social"), (LANDING, "landing"), (BOOKING, "booking")):
        for k, v in table.items():
            if d == k or d.endswith("." + k):
                return kind, v
    return "site", d


def digits(p):
    s = re.sub(r"\D", "", p or "")
    return s[-10:] if len(s) >= 10 else ""


def norm_name(n):
    n = (n or "").lower().split(",")[0].replace("ё", "е")
    n = re.sub(r"[«»\"'`.\-–—!?()]", " ", n)
    return re.sub(r"\s+", " ", n).strip()


def house(a):
    m = re.search(r"\d+[а-я]?", (a or "").lower().replace("ё", "е"))
    return m.group(0) if m else ""


# ниша по рубрикам компании (точнее, чем по поисковому запросу)
NICHE_KW = [
    ("Стоматология", r"стоматолог|зубн|ортодонт|имплант"),
    ("Цветы", r"цвет(ы|оч)|букет|флорист|воздушн.{0,3} шар|шарики"),
    ("Автосервис", r"авто(сервис|мастерск|мойк|техцентр|электр|стекл|запчаст|тюнинг|ремонт)|шиномонтаж|кузов|развал|детейлинг|тонировк|эвакуат|сто|ремонт (двигател|акпп|ходов|дизел)|покраска авто|замена масла|грузовых автомоб"),
    ("Салоны красоты", r"салон красоты|парикмахер|барбер|маникюр|ногтев|косметолог|ресниц|бров|солярий|тату|эпиляц|депиляц|spa|спа-|визаж|массаж|красоты"),
    ("Доставка и еда", r"доставк.{0,5}(еды|обед|пицц|суши|воды)|суши|пицц|ролл|шаурм|кондитер|торт|пекарн|кейтеринг|быстрое питание|фастфуд|питьев.. вод"),
    ("Медицина и здоровье", r"медицин|клиник|психолог|психотерап|оптик|офтальмолог|ветеринар|зоосалон|груминг|\bанализ|логопед|мануальн|остеопат|невролог|гинеколог|\bузи\b"),
    ("Ремонт и стройка", r"ремонт (квартир|помещ|ванн)|отделочн|натяжн|потолк|окна|окон|двер|мебел|кухн|сантехн|электромонтаж|электрик|жалюзи|рольстав|строител|балкон|водоснабжен|отоплен|канализац"),
    ("Обучение и дети", r"детск.. (центр|клуб|сад)|развивающ|автошкол|курс|репетитор|танц|фитнес|йог|музыкальн|спортивн|школа|обучени|языков|английск|секци|тренаж"),
    ("Праздники и фото", r"фото|видеосъ|праздник|ведущ|аниматор|свадеб|прокат костюм|event|ивент"),
    ("Гостиницы и досуг", r"гостиниц|хостел|посуточ|апартамент|сауна|бан[яи]|кальян|кафе|ресторан|бар|банкетн|квест|компьютерный клуб|караоке|боулинг"),
    ("Бытовые услуги", r"клининг|уборк|химчистк|прачечн|ремонт (телефон|бытов|компьют|обуви|часов|одежд|техники)|сервисный центр|ателье|пошив|ключ|грузоперевоз|грузчик|переезд|ритуал|мастер на час|металлоремонт"),
    ("Деловые услуги", r"юрид|юрист|адвокат|бухгалт|недвижимост|риелт|риэлт|страхов|нотари|типограф|полиграф|реклам|курьер|кадастр|оценк"),
]
_NKW = [(n, re.compile(p, re.I)) for n, p in NICHE_KW]


def niche_by_cats(cats, name=""):
    for n, rx in _NKW:
        if rx.search(cats or ""):
            return n
    for n, rx in _NKW:
        if rx.search(name or ""):
            return n
    return ""
