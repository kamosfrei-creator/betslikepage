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
4. `generator/news.py` zbiera wiadomości o drużynach grających dziś i jutro
   i koryguje nimi model (szczegóły niżej).
5. `generator/texts.py` składa analizy z szablonów w ~40 językach (`i18n/*.json`).
6. `generator/build.py` przy każdej aktualizacji automatycznie rozlicza
   wcześniejsze typy i kupony, zapisuje je w `data/history.json` (cała historia,
   bez kasowania) i generuje stronę do `_site/`. `generator/stats.py` liczy
   skuteczność: 7 dni / 30 dni / od początku, osobno kupony, osobno każdy rodzaj
   typu, historię dzień po dniu i archiwum miesięczne.

Typ meczu jest aktualizowany przy każdej aktualizacji aż do rozpoczęcia meczu,
a potem zamrażany - rozliczany jest dokładnie ten typ, który był na stronie
przed gwizdkiem.

## Kontuzje, składy i newsy

| Źródło | Co daje | Koszt |
|---|---|---|
| API-Football (`API_FOOTBALL_KEY`) | listy zawodników, którzy nie zagrają / są niepewni, potwierdzone składy (ok. 1 h przed meczem) | darmowy plan 100 zapytań/dzień - sprawdź, czy obejmuje bieżący sezon; jeśli nie, plan płatny od ok. 19 USD/mies. |
| Kanały RSS portali (`news_feeds` w `config.json`) | sygnały z nagłówków: kontuzja/zawieszenie, powrót do gry, zmiana trenera | darmowe |

Jak to wpływa na typy: każdy nieobecny zawodnik obniża oczekiwane gole
drużyny o 1,5% i zwiększa straty o 1,2% (niepewny liczy się w 40%), łącznie
maksymalnie 10%. Gdy nie ma twardych danych, sygnał „problemy kadrowe" z
nagłówków daje -3%. Korekty są celowo ostrożne: listy kontuzji obejmują też
zawodników, których brak od dawna widać już w wynikach, a bez danych o
znaczeniu zawodnika (gwiazda czy rezerwowy) większa korekta częściej szkodzi
niż pomaga. Historia skuteczności pokaże, czy warto je zwiększyć - parametry
są na górze `generator/news.py`.

Nagłówki RSS są analizowane słowami kluczowymi (EN, PL, DE, ES, PT, IT, FR,
NL). Na stronie nie publikujemy żadnego cudzego tekstu - tylko nasze wnioski
w naszych słowach. Przed dodaniem kanału sprawdź jego regulamin (niektóre
portale zastrzegają użycie RSS do celów niekomercyjnych).

## Języki

~40 języków: wszystkie języki urzędowe UE, norweski, islandzki, ukraiński,
rosyjski, turecki, serbski, bośniacki, macedoński, albański, kataloński oraz
chiński, hindi, arabski, bengalski, urdu, indonezyjski i japoński (arabski
i urdu z układem od prawej do lewej). Lista w `config.json` -> `languages`.

Język wybierany jest automatycznie z ustawień przeglądarki odwiedzającego
(dokładniejsze niż IP i nie wymaga przetwarzania danych osobowych), można go
zmienić ręcznie z listy - wybór jest zapamiętywany. Tłumaczenia zostały
przygotowane maszynowo - przed promocją strony w danym kraju warto dać je do
przejrzenia native speakerowi.

## Uruchomienie

### Lokalnie

```bash
python -m generator.build --demo     # dane syntetyczne
python -m generator.build --demo --now 2026-10-01T06:00:00   # symulacja innego dnia
python -m generator.build --demo --langs pl,en   # tylko wybrane języki (szybciej)
FOOTBALL_DATA_TOKEN=xxx python -m generator.build
python -m http.server -d _site 8000  # podgląd: http://localhost:8000
python -m unittest discover -s tests -t .
```

Wymaga tylko Pythona 3.9+, bez dodatkowych bibliotek.

### Publikacja (jednorazowa konfiguracja)

1. Zarejestruj się na <https://www.football-data.org/client/register> i skopiuj klucz API.
2. W repozytorium: **Settings → Secrets and variables → Actions → New repository secret**,
   nazwa `FOOTBALL_DATA_TOKEN`. Opcjonalnie drugi sekret `API_FOOTBALL_KEY`
   (klucz z <https://www.api-football.com/>) - kontuzje i składy.
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
i18n/                    tłumaczenia (jeden plik JSON na język)
static/                  CSS, JS, favicon
data/history.json        historia typów (aktualizowana przez workflow)
.github/workflows/       automatyczne aktualizacje i publikacja
tests/                   testy
```
