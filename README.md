# BetsLike - codzienne typy piłkarskie

Statyczna strona z typami i kuponami na dziś i jutro, generowana automatycznie
4 razy dziennie (ok. 8:00, 12:00, 16:00, 20:00 czasu polskiego). Działa
samodzielnie na GitHub Actions + GitHub Pages: **bez serwera, bez AI, bez
zużycia tokenów i za darmo**.

## Jak to działa

1. `generator/fetch.py` pobiera **surowe fakty** (terminarz i wyniki) z
   licencjonowanego API [football-data.org](https://www.football-data.org/)
   (darmowy plan).
2. `generator/model.py` liczy własny model statystyczny (Poisson + korekta
   Dixona-Colesa): siła ataku/obrony, gra u siebie/na wyjeździe, forma, waga
   świeższych meczów.
3. `generator/coupons.py` wybiera typ dla każdego meczu i składa 3 kupony
   (bezpieczny, standard, odważny) z prawdopodobieństwem i kursem fair.
4. `generator/texts.py` składa analizy z szablonów w 4 językach (PL, EN, DE, ES).
5. `generator/build.py` rozlicza wcześniejsze typy (publiczna historia
   skuteczności w `data/history.json`) i generuje stronę do `_site/`.

Język wybierany jest automatycznie z ustawień przeglądarki odwiedzającego
(dokładniejsze niż IP i nie wymaga przetwarzania danych osobowych), można go
zmienić ręcznie - wybór jest zapamiętywany.

## Uruchomienie

### Lokalnie

```bash
python -m generator.build --demo     # dane syntetyczne
FOOTBALL_DATA_TOKEN=xxx python -m generator.build
python -m http.server -d _site 8000  # podgląd: http://localhost:8000
python -m unittest discover -s tests -t .
```

Wymaga tylko Pythona 3.9+, bez dodatkowych bibliotek.

### Publikacja (jednorazowa konfiguracja)

1. Zarejestruj się na <https://www.football-data.org/client/register> i skopiuj klucz API.
2. W repozytorium: **Settings → Secrets and variables → Actions → New repository secret**,
   nazwa `FOOTBALL_DATA_TOKEN`.
3. **Settings → Pages → Source: GitHub Actions**. (Pages w prywatnym repo wymaga
   płatnego planu GitHub - repo publiczne działa za darmo.)
4. Zmerguj kod do `main` lub uruchom workflow ręcznie (**Actions → Aktualizacja typów → Run workflow**).
5. W `config.json` ustaw `base_url` (np. własna domena) i `contact_email`.

Własną domenę podpina się w **Settings → Pages → Custom domain**.

## Reklamy

Miejsca reklamowe są już na stronie (z linkiem "Miejsce na Twoją reklamę").
Reklamę partnera dodaje się w `config.json`:

```json
"ads": [
  {"slot": "day0", "languages": ["pl"], "url": "https://...", "image": "https://.../banner.png", "alt": "Nazwa"}
]
```

Dostępne sloty: `day0` (pod kuponami na dziś), `day1` (jutro), `results`.
Linki dostają automatycznie `rel="sponsored nofollow"` i oznaczenie "Reklama · 18+".

## Zgodność z prawem - ważne

- **Treści są nasze.** Strona nie kopiuje ani nie "przeredagowuje" cudzych typów
  i artykułów - to mogłoby naruszać prawa autorskie i regulaminy tych serwisów,
  nawet po zmianie słów. Pobieramy tylko fakty (wyniki, terminarz) z API, którego
  licencja na to pozwala, i podajemy źródło danych w stopce (to wymóg licencji
  i nic nie kosztuje - same fakty nie są chronione).
- **Reklama hazardu w Polsce** (ustawa o grach hazardowych): wolno reklamować
  wyłącznie bukmacherów z zezwoleniem Ministra Finansów (lista na stronach
  Ministerstwa Finansów). Reklama nielegalnego operatora to przestępstwo, także dla
  wydawcy strony. W innych krajach obowiązują lokalne zasady - dlatego reklamy
  można kierować do konkretnych wersji językowych. Reklamy muszą zawierać
  informację 18+ i o ryzyku.
- Strona zawiera ostrzeżenie 18+, informację, że typy nie gwarantują wygranej,
  i linki do pomocy przy uzależnieniu.
- Strona nie używa cookies ani śledzenia (tylko `localStorage` na wybór języka),
  więc nie potrzebuje bannera cookies. Po dodaniu analityki lub reklam z
  trackingiem trzeba dodać zgodę RODO i politykę prywatności.
- To nie jest porada prawna - przed zawarciem umów reklamowych warto skonsultować
  się z prawnikiem.

## Struktura

```
config.json              ustawienia (ligi, języki, godziny, reklamy)
generator/               kod generatora
static/                  CSS, JS, favicon
data/history.json        historia typów (aktualizowana przez workflow)
.github/workflows/       automatyczne aktualizacje i publikacja
tests/                   testy
```
