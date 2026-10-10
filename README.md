# FormaBet - codzienne typy piłkarskie

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

## Strony

- **Przegląd** (`index.html`): kupony dnia, najmocniejsze typy, tabele meczów
  wg lig z prawdopodobieństwami 1/X/2, przewidywanym wynikiem i typem.
- **Liga** (`league-<KOD>.html`): mecze dziś/jutro, tabela, trafność typów w lidze.
- **Analiza meczu** (`match-<id>.html`): xG modelu, szanse 1X2, wszystkie rynki
  (1X2, podwójna szansa, over/under, BTTS), prawdopodobieństwa dokładnych wyników,
  kursy i ich ruch, value bet z linkiem do bukmachera (afiliacja), statystyki
  sezonu (gole, stracone, BTTS, over 2,5, czyste konta), ostatnie 10 meczów,
  H2H, kontuzje i zawieszenia, przewidywane składy, kluczowe czynniki i analiza.

## Model - jakie czynniki bierzemy pod uwagę

| Czynnik | Skąd | Koszt |
|---|---|---|
| Siła ataku i obrony, osobno u siebie i na wyjeździe, świeższe mecze ważniejsze | wyniki z football-data.org | darmowe |
| Model Poissona z korektą Dixona-Colesa (rozkład wyników) | własny | darmowe |
| Ranking Elo (30% udziału w 1X2) | własny, z wyników | darmowe |
| **Indeks formy 0-100** (ostatnie 5 meczów: punkty + bilans bramek, ważone siłą rywala wg Elo i świeżością; 60% ogółem + 40% w tej samej roli u siebie/na wyjeździe) | własny, z wyników | darmowe |
| Tabela ligowa, H2H | football-data.org | darmowe |
| Obciążenie meczami (odpoczynek ≤ 3,5 dnia, ≥ 4 mecze w 14 dniach) | wyniki | darmowe |
| Absencje wg pozycji i znaczenia zawodnika, motywacja, rotacja, zmiana trenera, przewidywane składy | **research AI** (Claude Haiku 5.5 + wyszukiwarka) | ok. $5-15/mies. |
| Kursy, ruch kursów, value bet | The Odds API (opcjonalnie) | darmowy plan 500 zapytań/mies. wystarcza na 2 odczyty dziennie |

Obliczenia idą etapami, a strona meczu pokazuje szanse 1/X/2 po każdym:
model bazowy (siła u siebie/na wyjeździe) → forma (różnica indeksów 100 pkt
= ±12% oczekiwanych goli, parametry `FORM_*` w `generator/build.py`) →
obciążenie meczami → wiadomości o drużynach (AI) → ranking Elo = wynik końcowy.

Korekty z researchu (parametry w `generator/research.py`): kluczowy napastnik
-7% oczekiwanych goli, kluczowy bramkarz +7% traconych, zawodnik podstawowy
ok. 45% tego, rezerwowy 10%, niepewny 40%; maks. 20%. Motywacja ±3% ataku,
ryzyko rotacji -3% ataku na poziom. Wszystko przemnożone przez pewność
informacji (0,3-1). Historia skuteczności pokaże, czy parametry trzeba zmienić.

**Research AI** robi jedno zapytanie na ligę (do 12 meczów) najwyżej raz na
20 h: najpierw model szuka faktów w internecie (maks. 4 wyszukiwania), potem
drugie, tanie zapytanie zamienia notatki na dane. Model ma ignorować typy i
kursy innych serwisów. Na stronę trafiają tylko dane (nazwiska, pozycje), a
teksty piszą nasze szablony. Szacunek kosztu: ~10 lig × 4 wyszukiwania × $0,01
= ~$0,40 dziennie przy pełnym terminarzu, w praktyce mniej (wyszukiwanie
$10/1000, tokeny Haiku $0,10/$0,50 za milion). Limit wydatków ustaw w
Anthropic Console → Billing.

Bez klucza `ANTHROPIC_API_KEY` strona działa dalej - korzysta wtedy z
API-Football (`API_FOOTBALL_KEY`) i nagłówków RSS (`news_feeds`).

## Kursy i afiliacja

Kursy pobiera `generator/odds.py` z The Odds API (`ODDS_API_KEY`, rejestracja
na the-odds-api.com) o godzinach z `config.json` → `odds.hours`.
Nazwy bukmacherów i linki pokazujemy **tylko** dla bukmacherów wpisanych do
`config.json` → `bookmakers` - wpisuj tam wyłącznie operatorów licencjonowanych
na danym rynku, a `languages` ogranicz do krajów, gdzie mają licencję:

```json
"bookmakers": {
  "betclic": {"name": "Betclic", "url": "https://twój-link-afiliacyjny", "languages": ["pl"]}
}
```

Klucz (np. `betclic`) to identyfikator bukmachera w The Odds API. Bez wpisów
strona pokazuje tylko średni kurs rynku, bez nazw i linków.

## Konta i komentarze (Supabase, darmowy plan)

Logowanie linkiem z e-maila, komentarze pod meczami, zgłaszanie komentarzy,
synchronizacja ulubionych lig, obserwowanych meczów i kuponu między urządzeniami.
Bez konfiguracji przycisk „Zaloguj” pokazuje „Konta nie są jeszcze dostępne”,
a ulubione i kupon działają lokalnie w przeglądarce.

1. Załóż projekt na <https://supabase.com> (region w UE, np. Frankfurt).
2. **SQL Editor → New query** → wklej `supabase/schema.sql` → **Run**.
3. **Authentication → URL Configuration**: Site URL =
   `https://kamosfrei-creator.github.io/betslikepage/` (albo Twoja domena),
   w Redirect URLs dodaj ten sam adres z `**` na końcu.
4. **Project Settings → API**: skopiuj `Project URL` i klucz `anon public` do
   `config.json` → `supabase.url` i `supabase.anon_key` (klucz anon jest
   publiczny z założenia - dostęp chronią reguły RLS ze schematu).
5. Darmowy plan Supabase wysyła tylko kilka e-maili na godzinę - przy większym
   ruchu podłącz własny serwer SMTP (Authentication → SMTP Settings).

Moderacja: komentarz ukrywasz w **Table Editor → comments → hidden = true**;
zgłoszenia są w tabeli `reports`. Polityka prywatności jest na stronie
`privacy.html` - uzupełnij w niej dane administratora (firma/osoba, adres).

## Indeks meczu (-10 do +10)

`indeks = 10 × (P(wygrana gospodarzy) − P(wygrana gości))` z końcowych
prawdopodobieństw modelu. +5 = wygrana gospodarzy o 50 pkt proc. bardziej
prawdopodobna niż gości. Na stronie: filtr „Min. indeks” (±2…±7), sortowanie
i „Lista wg indeksu” (od największego); w statystykach trafność wg indeksu.

## Kontuzje z innych źródeł (gdy nie ma klucza Anthropic)

| Źródło | Co daje | Koszt |
|---|---|---|
| API-Football (`API_FOOTBALL_KEY`) | listy zawodników, którzy nie zagrają / są niepewni, potwierdzone składy (ok. 1 h przed meczem) | darmowy plan 100 zapytań/dzień |
| Kanały RSS portali (`news_feeds` w `config.json`) | sygnały z nagłówków: kontuzja/zawieszenie, powrót do gry, zmiana trenera | darmowe |

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
   Do researchu AI: `ANTHROPIC_API_KEY` (console.anthropic.com → API Keys).
   Do kursów: `ODDS_API_KEY` (the-odds-api.com).
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
