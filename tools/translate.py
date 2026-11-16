"""Traduz os comentários (inglês -> português do Brasil) com o Argos Translate.

Uso: python tools/translate.py <shard> <total_shards> <livros> <minutos>
  livros: "all" ou lista separada por vírgula dos prefixos dos arquivos (ex.: "john,romans")
Lê docs/data/<livro>-N.json e grava docs/tr/<livro>-N.json no mesmo formato de capítulos,
com uma lista de traduções alinhada, posição a posição, com os comentários do arquivo original.
A cada arquivo terminado, e a cada 20 minutos no meio de um arquivo, grava e envia ao repositório,
para as traduções aparecerem no site aos poucos. Arquivo incompleto leva a marca "_partial".
"""
import json, os, sys, time, glob, re, subprocess

shard, total, books, minutes = int(sys.argv[1]), int(sys.argv[2]), sys.argv[3].strip().lower(), float(sys.argv[4])
deadline = time.time() + minutes * 60
SAVE_EVERY = 20 * 60
BRANCH = os.environ.get("BRANCH", "main")
LOG = f"tools/logs/lote-{shard}.log"
os.makedirs("docs/tr", exist_ok=True); os.makedirs("tools/logs", exist_ok=True)
log_lines = []

def say(*a):
    line = time.strftime("%H:%M:%S ") + " ".join(str(x) for x in a)
    print(line, flush=True); log_lines.append(line)

def publish(paths, msg):
    """Grava o registro e envia os arquivos; tenta de novo se outro lote enviou ao mesmo tempo."""
    open(LOG, "w", encoding="utf-8").write("\n".join(log_lines) + "\n")
    if os.environ.get("NO_PUSH"):
        return
    try:
        subprocess.run(["git", "add", LOG] + paths, check=True)
        if subprocess.run(["git", "diff", "--cached", "--quiet"]).returncode == 0:
            return
        subprocess.run(["git", "commit", "-q", "-m", msg], check=True)
        for attempt in range(6):
            if subprocess.run(["git", "pull", "-q", "--rebase", "origin", BRANCH]).returncode == 0 and \
               subprocess.run(["git", "push", "-q", "origin", f"HEAD:{BRANCH}"]).returncode == 0:
                return
            subprocess.run(["git", "rebase", "--abort"], capture_output=True)
            time.sleep(10 + 7 * shard % 20 + 10 * attempt)
        say("aviso: não consegui enviar agora; tento de novo no próximo ponto de gravação")
    except Exception as e:
        say("aviso: erro ao enviar", repr(e)[:160])

import argostranslate.package, argostranslate.translate
argostranslate.package.update_package_index()
avail = argostranslate.package.get_available_packages()
pkg = next((p for p in avail if p.from_code == "en" and p.to_code == "pb"), None) or \
      next(p for p in avail if p.from_code == "en" and p.to_code == "pt")
argostranslate.package.install_from_path(pkg.download())
tr = argostranslate.translate.get_translation_from_codes("en", pkg.to_code)
say("modelo:", pkg.from_code, "->", pkg.to_code)

cache = {}
def translate(text):
    if text not in cache:
        cache[text] = "\n".join(tr.translate(p) if p.strip() else p for p in text.split("\n"))
    return cache[text]

files = sorted(f for f in glob.glob("docs/data/*.json") if re.search(r"-\d+\.json$", f))
if books != "all":
    want = set(b.strip() for b in books.split(",") if b.strip())
    files = [f for f in files if os.path.basename(f).rsplit("-", 1)[0] in want]
files = [f for i, f in enumerate(files) if i % total == shard]
say(len(files), "arquivos neste lote")

if shard == 0 and os.path.exists("docs/data/daily.json") and not os.path.exists("docs/tr/daily.json"):
    rows = json.load(open("docs/data/daily.json", encoding="utf-8"))
    json.dump([translate(r[6]) for r in rows], open("docs/tr/daily.json", "w", encoding="utf-8"), ensure_ascii=False)
    say("frases do dia traduzidas"); publish(["docs/tr/daily.json"], "Tradução: frases do dia")

def snapshot(data):
    out, missing = {}, 0
    for ch, rows in data.items():
        out[ch] = [cache.get(r[5]) for r in rows]
        missing += sum(1 for t in out[ch] if t is None)
    if missing:
        out["_partial"] = True
    return out, missing

for f in files:
    name = os.path.basename(f); dst = os.path.join("docs/tr", name)
    if os.path.exists(dst):
        prev = json.load(open(dst, encoding="utf-8"))
        if not prev.get("_partial"):
            say("pronto, pulando:", name); continue
        data = json.load(open(f, encoding="utf-8"))
        for ch, rows in data.items():       # reaproveita o que já foi traduzido antes
            old = prev.get(ch)
            if isinstance(old, list):
                for r, t in zip(rows, old):
                    if t: cache[r[5]] = t
    else:
        data = json.load(open(f, encoding="utf-8"))
    todo = [r[5] for rows in data.values() for r in rows]
    chars_total = sum(len(t) for t in set(todo))
    t0 = last = time.time(); n = 0; chars = 0; out_of_time = False
    for text in todo:
        if text in cache:
            continue
        if time.time() > deadline:
            out_of_time = True; break
        try:
            translate(text); n += 1; chars += len(text)
        except Exception as e:
            say("erro em", name, repr(e)[:200]); cache[text] = ""
        if time.time() - last > SAVE_EVERY:
            out, missing = snapshot(data)
            json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
            say(f"{name}: parcial, {n} trechos, {chars/1e3:.0f} mil caracteres em {(time.time()-t0)/60:.0f} min; faltam {missing} trechos")
            publish([dst], f"Tradução parcial: {name}"); last = time.time()
    out, missing = snapshot(data)
    json.dump(out, open(dst, "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
    say(f"{name}: {n} trechos novos, {chars/1e3:.0f} de {chars_total/1e3:.0f} mil caracteres em {(time.time()-t0)/60:.0f} min" + (f"; faltam {missing}" if missing else "; completo"))
    publish([dst], ("Tradução parcial: " if missing else "Tradução: ") + name)
    if out_of_time:
        say("tempo esgotado; o restante fica para a próxima rodada"); break
publish([], f"Registro do lote {shard}")
