"""Baixa um retrato de cada autor a partir da imagem principal do seu artigo na Wikipédia.
Só aceita arquivos do Wikimedia Commons marcados como domínio público ou CC0.
Grava docs/saints/<n>.jpg e docs/saints/index.json (com a origem e a licença de cada imagem)."""
import json, os, re, time, io, urllib.parse, requests
from PIL import Image

UA = {"User-Agent": "CatenaPatristica/1.0 (https://github.com/erosantoniojob-sys/catena-patristica)"}
API = "https://en.wikipedia.org/w/api.php"
SKIP = {"Canonical Scriptures", "Second Temple Judaism"}
os.makedirs("docs/saints", exist_ok=True)
authors = json.load(open("docs/data/index.json", encoding="utf-8"))["authors"]
out, log = {}, []

def get(params):
    for _ in range(3):
        try:
            r = requests.get(API, params={**params, "format": "json", "formatversion": 2}, headers=UA, timeout=30)
            if r.status_code == 200:
                return r.json()
        except Exception:
            pass
        time.sleep(2)
    return {}

for i, a in enumerate(authors):
    w = a.get("w") or ""
    m = re.match(r"https?://en\.wikipedia\.org/wiki/([^#?]+)", w)
    if not m or a.get("c") in SKIP:
        continue
    title = urllib.parse.unquote(m.group(1))
    try:
        d = get({"action": "query", "titles": title, "redirects": 1, "prop": "pageimages", "piprop": "name|thumbnail", "pithumbsize": 320})
        page = (d.get("query", {}).get("pages") or [{}])[0]
        name, thumb = page.get("pageimage"), (page.get("thumbnail") or {}).get("source")
        if not name or not thumb:
            log.append(f"{a['n']}: sem imagem"); continue
        d2 = get({"action": "query", "titles": "File:" + name, "prop": "imageinfo", "iiprop": "extmetadata|url"})
        info = ((d2.get("query", {}).get("pages") or [{}])[0].get("imageinfo") or [{}])[0]
        meta = info.get("extmetadata") or {}
        lic = (meta.get("LicenseShortName") or {}).get("value", "")
        if not re.search(r"public domain|^pd\b|cc0", lic, re.I):
            log.append(f"{a['n']}: licença não livre o bastante ({lic or 'desconhecida'})"); continue
        img = requests.get(thumb, headers=UA, timeout=60)
        if img.status_code != 200:
            log.append(f"{a['n']}: download falhou ({img.status_code})"); continue
        im = Image.open(io.BytesIO(img.content)).convert("RGB")
        wd, ht = im.size; s = min(wd, ht)
        top = 0 if ht > wd else (ht - s) // 2            # retratos: corta a partir do topo, onde fica o rosto
        im = im.crop(((wd - s) // 2, top, (wd - s) // 2 + s, top + s)).resize((160, 160), Image.LANCZOS)
        fn = f"{i}.jpg"; im.save("docs/saints/" + fn, quality=82, optimize=True)
        out[a["n"]] = {"f": fn, "lic": lic, "src": info.get("descriptionurl", "")}
    except Exception as e:
        log.append(f"{a['n']}: erro {repr(e)[:120]}")
    time.sleep(0.15)

json.dump(out, open("docs/saints/index.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
os.makedirs("tools/logs", exist_ok=True)
open("tools/logs/retratos.log", "w", encoding="utf-8").write(f"{len(out)} retratos gravados\n" + "\n".join(log) + "\n")
print(len(out), "retratos;", len(log), "sem imagem aproveitável")
