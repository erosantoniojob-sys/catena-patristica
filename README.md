# Catena Patrística

Ler a Escritura com a tradição: comentários dos Pais da Igreja, versículo por versículo.

**Acesse o aplicativo:** [Catena Patrística](https://erosantoniojob-sys.github.io/catena-patristica/)

- `docs/` — o aplicativo (página única) e os dados: `data/` comentários em inglês, `bible/` texto bíblico, `tr/` traduções para o português.
- `tools/translate.py` — tradução automática (Argos Translate, inglês → português do Brasil).
- `.github/workflows/translate.yml` — roda a tradução nas máquinas do GitHub. Para disparar, edite `tools/request.txt`.

## Fontes e licenças

- Comentários: [Commentaries Database](https://github.com/HistoricalChristianFaith/Commentaries-Database), do projeto Historical Christian Faith (domínio público).
- Texto bíblico: Bíblia Livre (BLIVRE), Copyright © 2018 Diego Santos, Mario Sérgio e Marco Teles, licença Creative Commons Atribuição 4.0 Brasil.
- As traduções em `docs/tr/` são feitas por máquina e podem conter erros; confira com o original antes de citar.
