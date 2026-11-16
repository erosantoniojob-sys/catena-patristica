"""Traduz os comentários (inglês -> português do Brasil) com o Argos Translate.

Uso: python tools/translate.py <shard> <total_shards> <livros> <minutos>
  livros: "all" ou lista separada por vírgula dos prefixos dos arquivos (ex.: "john,romans")
Lê docs/data/<livro>-N.json e grava out/tr/<livro>-N.json no mesmo formato de capítulos,
com uma lista de traduções alinhada, posição a posição, com os comentários do arquivo original.
"""
import json, os, sys, time, glob, re

shard, total, books, minutes = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3].strip().lower(), float(sys.argv[4])
deadline = time.time() + minutes * 60
os.makedirs("out/tr", exist_ok=True)

import argostranslate.package, argostranslate.translate
argostranslate.package.update_package_index()
avail = argostranslate.package.get_available_packages()
pkg = next((p for p in avail if p.from_code == "en" and p.to_code == "pb"), None) or \
      next(p for p in avail if p.from_code == "en" and p.to_code == "pt")
argostranslate.package.install_from_path(pkg.download())
tr = argostranslate.translate.get_translation_from_codes("en", pkg.to_code)
print("modelo:", pkg.from_code, "->", pkg.to_code, flush=True)

cache = {}
def translate(text):
    if text in cache:
        return cache[text]
    parts = []
    for para in text.split("\n"):
        parts.append(tr.translate(para) if para.strip() else para)
    cache[text] = "\n".join(parts)
    return cache[text]

files = sorted(f for f in glob.glob("docs/data/*.json") if re.search(r"-\d+\.json$", f))
if books != "all":
    want = set(b.strip() for b in books.split(",") if b.strip())
    files = [f for f in files if os.path.basename(f).rsplit("-", 1)[0] in want]
files = [f for i, f in enumerate(files) if i % total == shard]
print(len(files), "arquivos neste lote", flush=True)

def run_daily():
    src, dst = "docs/data/daily.json", "docs/tr/daily.json"
    if os.path.exists(dst) or not os.path.exists(src):
        return
    rows = json.load(open(src, encoding="utf-8"))
    json.dump([translate(r[6]) for r in rows], open("out/tr/daily.json", "w", encoding="utf-8"), ensure_ascii=False)
    print("frases do dia traduzidas", flush=True)

if shard == 0:
    run_daily()

for f in files:
    name = os.path.basename(f)
    done_path = os.path.join("docs/tr", name)
    prev = {}
    if os.path.exists(done_path):
        prev = json.load(open(done_path, encoding="utf-8"))
        if not prev.get("_partial"):
            print("pronto, pulando:", name, flush=True)
            continue
    data = json.load(open(f, encoding="utf-8"))
    for ch, rows in data.items():           # reaproveita o que já foi traduzido numa rodada anterior
        old = prev.get(ch)
        if isinstance(old, list):
            for r, t in zip(rows, old):
                if t:
                    cache[r[5]] = t
    out, partial, n, t0 = {}, False, 0, time.time()
    for ch, rows in data.items():
        res = []
        for r in rows:
            if r[5] in cache:
                res.append(cache[r[5]])
            elif time.time() > deadline:
                res.append(None); partial = True
            else:
                try:
                    res.append(translate(r[5])); n += 1
                except Exception as e:
                    print("erro em", name, ch, repr(e)[:200], flush=True)
                    res.append(None); partial = True
        out[ch] = res
    if partial:
        out["_partial"] = True
    json.dump(out, open(os.path.join("out/tr", name), "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    chars = sum(len(r[5]) for rows in data.values() for r in rows)
    print(f"{name}: {n} trechos novos em {time.time()-t0:.0f}s ({chars/1e6:.2f} MB no arquivo){' [parcial]' if partial else ''}", flush=True)
    if time.time() > deadline:
        print("tempo esgotado; o restante fica para a próxima rodada", flush=True)
        break
