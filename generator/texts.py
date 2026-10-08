"""Teksty interfejsu i szablony analiz w każdym języku.

Analizy są składane z szablonów na podstawie liczb z modelu - bez LLM,
więc generowanie nie zużywa żadnych tokenów.
"""

UI = {
    "pl": {
        "lang_name": "Polski",
        "tagline": "Codzienne typy oparte na statystyce",
        "today": "Dziś", "tomorrow": "Jutro",
        "coupons": "Kupony", "all_matches": "Wszystkie mecze",
        "coupon_safe": "Kupon bezpieczny", "coupon_standard": "Kupon standard", "coupon_bold": "Kupon odważny",
        "probability": "Prawdopodobieństwo", "fair_odds": "Kurs fair",
        "fair_odds_hint": "Kurs fair = 1 / prawdopodobieństwo modelu. Jeśli bukmacher oferuje wyższy, typ ma dodatnią wartość według modelu.",
        "pick": "Typ", "alternatives": "Alternatywy", "likely_score": "Najbardziej prawdopodobny wynik",
        "xg": "Oczekiwane gole", "form": "Forma (ostatnie 5)", "low_data": "Mało danych - typ orientacyjny",
        "no_matches": "Brak meczów w obsługiwanych ligach na ten dzień.",
        "updated": "Aktualizacja", "next_update": "Aktualizacje codziennie ok. 8:00, 12:00, 16:00 i 20:00 (czasu polskiego).",
        "results": "Skuteczność", "about": "O nas", "advertise": "Reklama", "responsible": "Graj odpowiedzialnie",
        "results_title": "Rozliczone typy", "hit_rate": "Trafność", "settled": "Rozliczone", "won": "Trafione",
        "last_days": "ostatnie 30 dni", "all_time": "od początku", "no_history": "Historia pojawi się po rozliczeniu pierwszych meczów.",
        "date": "Data", "match": "Mecz", "result": "Wynik", "status": "Status",
        "demo": "TRYB DEMO - dane syntetyczne. Dodaj klucz API, by pokazać prawdziwe mecze.",
        "disclaimer": "18+. Typy są wynikiem modelu statystycznego i nie gwarantują wygranej. Zakłady wiążą się z ryzykiem utraty pieniędzy. Graj wyłącznie u legalnych bukmacherów posiadających zezwolenie w Twoim kraju.",
        "help_text": "Potrzebujesz pomocy?", "help_url": "https://www.kcpu.gov.pl/", "help_name": "Krajowe Centrum Przeciwdziałania Uzależnieniom",
        "ad_placeholder": "Miejsce na Twoją reklamę", "ad_label": "Reklama",
        "data_credit": "Dane meczowe: football-data.org. Typy, statystyki i analizy: własny model BetsLike.",
        "about_html": """<p>BetsLike publikuje codzienne typy piłkarskie wyliczane przez własny model statystyczny (rozkład Poissona z korektą Dixona-Colesa). Model analizuje wyniki bieżącego sezonu, siłę ataku i obrony drużyn, grę u siebie i na wyjeździe oraz formę.</p>
<p>Nie kopiujemy typów innych serwisów. Z zewnątrz pobieramy wyłącznie surowe fakty (terminarz i wyniki) z licencjonowanego API, a wszystkie liczby, typy i komentarze powstają u nas.</p>
<p>Publikujemy też pełną historię rozliczonych typów - także tych nietrafionych.</p>""",
        "advertise_html": """<p>Jesteś legalnym bukmacherem lub marką związaną ze sportem? Na stronie są przygotowane miejsca reklamowe w kilku wersjach językowych.</p>
<p>Przyjmujemy reklamy wyłącznie od operatorów posiadających zezwolenie na rynek, na którym wyświetlana jest reklama. Wszystkie reklamy są wyraźnie oznaczone.</p>""",
        "contact": "Kontakt",
        "responsible_html": """<p>Zakłady bukmacherskie są dozwolone wyłącznie dla osób pełnoletnich. Traktuj je jako rozrywkę, nie sposób zarabiania pieniędzy.</p>
<ul><li>Ustal budżet i limit czasu, zanim zaczniesz.</li><li>Nigdy nie odgrywaj się po przegranej.</li><li>Nie obstawiaj pod wpływem alkoholu ani emocji.</li><li>Korzystaj tylko z legalnych, licencjonowanych bukmacherów.</li></ul>""",
    },
    "en": {
        "lang_name": "English",
        "tagline": "Daily statistics-based football tips",
        "today": "Today", "tomorrow": "Tomorrow",
        "coupons": "Bet slips", "all_matches": "All matches",
        "coupon_safe": "Safe slip", "coupon_standard": "Standard slip", "coupon_bold": "Bold slip",
        "probability": "Probability", "fair_odds": "Fair odds",
        "fair_odds_hint": "Fair odds = 1 / model probability. If a bookmaker offers more, the pick has positive value according to the model.",
        "pick": "Pick", "alternatives": "Alternatives", "likely_score": "Most likely score",
        "xg": "Expected goals", "form": "Form (last 5)", "low_data": "Limited data - indicative pick",
        "no_matches": "No matches in covered leagues on this day.",
        "updated": "Updated", "next_update": "Updated daily around 8:00, 12:00, 16:00 and 20:00 (CET/CEST).",
        "results": "Track record", "about": "About", "advertise": "Advertise", "responsible": "Play responsibly",
        "results_title": "Settled picks", "hit_rate": "Hit rate", "settled": "Settled", "won": "Won",
        "last_days": "last 30 days", "all_time": "all time", "no_history": "History appears once the first matches are settled.",
        "date": "Date", "match": "Match", "result": "Result", "status": "Status",
        "demo": "DEMO MODE - synthetic data. Add an API key to show real matches.",
        "disclaimer": "18+. Picks are produced by a statistical model and do not guarantee winnings. Betting involves the risk of losing money. Only bet with bookmakers licensed in your country.",
        "help_text": "Need help?", "help_url": "https://www.begambleaware.org/", "help_name": "BeGambleAware",
        "ad_placeholder": "Your ad here", "ad_label": "Advertisement",
        "data_credit": "Match data: football-data.org. Picks, statistics and analysis: BetsLike's own model.",
        "about_html": """<p>BetsLike publishes daily football picks computed by its own statistical model (Poisson distribution with the Dixon-Coles correction). The model looks at current-season results, attacking and defensive strength, home and away performance, and form.</p>
<p>We do not copy picks from other sites. The only external input is raw facts (fixtures and results) from a licensed API; every number, pick and comment is produced here.</p>
<p>We also publish the full history of settled picks - including the losing ones.</p>""",
        "advertise_html": """<p>Are you a licensed bookmaker or a sports brand? The site has ad slots available in several language versions.</p>
<p>We only accept ads from operators licensed for the market where the ad is shown. All ads are clearly labelled.</p>""",
        "contact": "Contact",
        "responsible_html": """<p>Betting is for adults only. Treat it as entertainment, not a way to make money.</p>
<ul><li>Set a budget and a time limit before you start.</li><li>Never chase losses.</li><li>Don't bet under the influence of alcohol or emotions.</li><li>Only use legal, licensed bookmakers.</li></ul>""",
    },
    "de": {
        "lang_name": "Deutsch",
        "tagline": "Tägliche Fußballtipps auf Basis von Statistik",
        "today": "Heute", "tomorrow": "Morgen",
        "coupons": "Wettscheine", "all_matches": "Alle Spiele",
        "coupon_safe": "Sicherer Schein", "coupon_standard": "Standard-Schein", "coupon_bold": "Mutiger Schein",
        "probability": "Wahrscheinlichkeit", "fair_odds": "Faire Quote",
        "fair_odds_hint": "Faire Quote = 1 / Modellwahrscheinlichkeit. Bietet ein Buchmacher mehr, hat der Tipp laut Modell einen positiven Wert.",
        "pick": "Tipp", "alternatives": "Alternativen", "likely_score": "Wahrscheinlichstes Ergebnis",
        "xg": "Erwartete Tore", "form": "Form (letzte 5)", "low_data": "Wenig Daten - Tipp nur zur Orientierung",
        "no_matches": "Keine Spiele in den abgedeckten Ligen an diesem Tag.",
        "updated": "Aktualisiert", "next_update": "Tägliche Updates gegen 8:00, 12:00, 16:00 und 20:00 Uhr (MEZ/MESZ).",
        "results": "Bilanz", "about": "Über uns", "advertise": "Werbung", "responsible": "Verantwortungsvoll spielen",
        "results_title": "Abgerechnete Tipps", "hit_rate": "Trefferquote", "settled": "Abgerechnet", "won": "Gewonnen",
        "last_days": "letzte 30 Tage", "all_time": "insgesamt", "no_history": "Die Bilanz erscheint, sobald die ersten Spiele abgerechnet sind.",
        "date": "Datum", "match": "Spiel", "result": "Ergebnis", "status": "Status",
        "demo": "DEMO-MODUS - synthetische Daten. API-Schlüssel hinzufügen, um echte Spiele anzuzeigen.",
        "disclaimer": "18+. Die Tipps stammen aus einem statistischen Modell und garantieren keinen Gewinn. Wetten birgt das Risiko, Geld zu verlieren. Wette nur bei in deinem Land lizenzierten Anbietern.",
        "help_text": "Brauchst du Hilfe?", "help_url": "https://www.check-dein-spiel.de/", "help_name": "Check dein Spiel",
        "ad_placeholder": "Ihre Werbung hier", "ad_label": "Anzeige",
        "data_credit": "Spieldaten: football-data.org. Tipps, Statistiken und Analysen: eigenes BetsLike-Modell.",
        "about_html": """<p>BetsLike veröffentlicht täglich Fußballtipps aus einem eigenen statistischen Modell (Poisson-Verteilung mit Dixon-Coles-Korrektur). Berücksichtigt werden Ergebnisse der laufenden Saison, Angriffs- und Abwehrstärke, Heim- und Auswärtsleistung sowie die Form.</p>
<p>Wir übernehmen keine Tipps anderer Seiten. Von außen beziehen wir nur reine Fakten (Spielplan und Ergebnisse) über eine lizenzierte API; alle Zahlen, Tipps und Kommentare entstehen bei uns.</p>
<p>Die komplette Bilanz abgerechneter Tipps ist öffentlich - auch die verlorenen.</p>""",
        "advertise_html": """<p>Sie sind ein lizenzierter Buchmacher oder eine Sportmarke? Auf der Seite stehen Werbeplätze in mehreren Sprachversionen zur Verfügung.</p>
<p>Wir akzeptieren nur Anzeigen von Anbietern mit Lizenz für den jeweiligen Markt. Alle Anzeigen sind klar gekennzeichnet.</p>""",
        "contact": "Kontakt",
        "responsible_html": """<p>Wetten ist nur für Erwachsene. Betrachte es als Unterhaltung, nicht als Einnahmequelle.</p>
<ul><li>Lege vorher ein Budget und ein Zeitlimit fest.</li><li>Versuche nie, Verluste zurückzugewinnen.</li><li>Wette nicht unter Alkoholeinfluss oder emotional.</li><li>Nutze nur legale, lizenzierte Anbieter.</li></ul>""",
    },
    "es": {
        "lang_name": "Español",
        "tagline": "Pronósticos diarios de fútbol basados en estadística",
        "today": "Hoy", "tomorrow": "Mañana",
        "coupons": "Combinadas", "all_matches": "Todos los partidos",
        "coupon_safe": "Combinada segura", "coupon_standard": "Combinada estándar", "coupon_bold": "Combinada atrevida",
        "probability": "Probabilidad", "fair_odds": "Cuota justa",
        "fair_odds_hint": "Cuota justa = 1 / probabilidad del modelo. Si una casa ofrece más, el pronóstico tiene valor positivo según el modelo.",
        "pick": "Pronóstico", "alternatives": "Alternativas", "likely_score": "Resultado más probable",
        "xg": "Goles esperados", "form": "Forma (últimos 5)", "low_data": "Pocos datos - pronóstico orientativo",
        "no_matches": "No hay partidos de las ligas cubiertas este día.",
        "updated": "Actualizado", "next_update": "Actualizaciones diarias hacia las 8:00, 12:00, 16:00 y 20:00 (CET/CEST).",
        "results": "Historial", "about": "Quiénes somos", "advertise": "Publicidad", "responsible": "Juego responsable",
        "results_title": "Pronósticos resueltos", "hit_rate": "Acierto", "settled": "Resueltos", "won": "Acertados",
        "last_days": "últimos 30 días", "all_time": "total", "no_history": "El historial aparecerá cuando se resuelvan los primeros partidos.",
        "date": "Fecha", "match": "Partido", "result": "Resultado", "status": "Estado",
        "demo": "MODO DEMO - datos sintéticos. Añade una clave de API para mostrar partidos reales.",
        "disclaimer": "+18. Los pronósticos provienen de un modelo estadístico y no garantizan ganancias. Apostar conlleva el riesgo de perder dinero. Apuesta solo en operadores con licencia en tu país.",
        "help_text": "¿Necesitas ayuda?", "help_url": "https://www.jugarbien.es/", "help_name": "Jugar Bien",
        "ad_placeholder": "Tu anuncio aquí", "ad_label": "Publicidad",
        "data_credit": "Datos de partidos: football-data.org. Pronósticos, estadísticas y análisis: modelo propio de BetsLike.",
        "about_html": """<p>BetsLike publica pronósticos diarios de fútbol calculados con un modelo estadístico propio (distribución de Poisson con corrección de Dixon-Coles). El modelo analiza los resultados de la temporada, la fuerza ofensiva y defensiva, el rendimiento como local y visitante y la forma.</p>
<p>No copiamos pronósticos de otras webs. Solo obtenemos datos brutos (calendario y resultados) de una API con licencia; todas las cifras, pronósticos y comentarios se generan aquí.</p>
<p>Publicamos el historial completo de pronósticos resueltos, también los fallados.</p>""",
        "advertise_html": """<p>¿Eres una casa de apuestas con licencia o una marca deportiva? La web dispone de espacios publicitarios en varios idiomas.</p>
<p>Solo aceptamos anuncios de operadores con licencia para el mercado donde se muestra el anuncio. Todos los anuncios están claramente identificados.</p>""",
        "contact": "Contacto",
        "responsible_html": """<p>Las apuestas son solo para mayores de edad. Tómalas como entretenimiento, no como forma de ganar dinero.</p>
<ul><li>Fija un presupuesto y un límite de tiempo antes de empezar.</li><li>Nunca intentes recuperar pérdidas.</li><li>No apuestes bajo los efectos del alcohol o de las emociones.</li><li>Usa solo casas de apuestas legales y con licencia.</li></ul>""",
    },
}

MARKETS = {
    "pl": {"1": "Wygrana gospodarzy (1)", "X": "Remis (X)", "2": "Wygrana gości (2)",
           "1X": "Gospodarze lub remis (1X)", "X2": "Goście lub remis (X2)", "12": "Bez remisu (12)",
           "O15": "Powyżej 1,5 gola", "O25": "Powyżej 2,5 gola", "O35": "Powyżej 3,5 gola",
           "U25": "Poniżej 2,5 gola", "U35": "Poniżej 3,5 gola",
           "BTTS": "Obie drużyny strzelą", "NOBTTS": "Nie obie strzelą"},
    "en": {"1": "Home win (1)", "X": "Draw (X)", "2": "Away win (2)",
           "1X": "Home or draw (1X)", "X2": "Away or draw (X2)", "12": "No draw (12)",
           "O15": "Over 1.5 goals", "O25": "Over 2.5 goals", "O35": "Over 3.5 goals",
           "U25": "Under 2.5 goals", "U35": "Under 3.5 goals",
           "BTTS": "Both teams to score", "NOBTTS": "Both teams to score - No"},
    "de": {"1": "Heimsieg (1)", "X": "Unentschieden (X)", "2": "Auswärtssieg (2)",
           "1X": "Heim oder Remis (1X)", "X2": "Auswärts oder Remis (X2)", "12": "Kein Remis (12)",
           "O15": "Über 1,5 Tore", "O25": "Über 2,5 Tore", "O35": "Über 3,5 Tore",
           "U25": "Unter 2,5 Tore", "U35": "Unter 3,5 Tore",
           "BTTS": "Beide Teams treffen", "NOBTTS": "Nicht beide treffen"},
    "es": {"1": "Gana local (1)", "X": "Empate (X)", "2": "Gana visitante (2)",
           "1X": "Local o empate (1X)", "X2": "Visitante o empate (X2)", "12": "Sin empate (12)",
           "O15": "Más de 1,5 goles", "O25": "Más de 2,5 goles", "O35": "Más de 3,5 goles",
           "U25": "Menos de 2,5 goles", "U35": "Menos de 3,5 goles",
           "BTTS": "Ambos marcan", "NOBTTS": "Ambos marcan - No"},
}

# Szablony zdań analizy. Wariant wybierany deterministycznie po id meczu,
# żeby teksty były różnorodne, ale stabilne między aktualizacjami.
ANALYSIS = {
    "pl": {
        "intro": [
            "Model szacuje oczekiwane gole na {xh} dla {home} i {xa} dla {away}.",
            "Według naszych wyliczeń drużyna {home} powinna zdobyć średnio {xh} gola, a {away} {xa}.",
            "Prognoza modelu: {xh} - {xa} w oczekiwanych golach.",
        ],
        "home_record": "{home} u siebie: średnio {s} gola strzelonego i {c} straconego na mecz.",
        "away_record": "{away} na wyjeździe: {s} gola strzelonego i {c} straconego na mecz.",
        "form_good": "{team} jest w dobrej formie ({form}).",
        "form_bad": "{team} ma słabszą serię ({form}).",
        "fav_home": "Faworytem są gospodarze - szansa na ich wygraną to {p}.",
        "fav_away": "Lekko faworyzowani są goście - {p} szans na wygraną.",
        "balanced": "Mecz wygląda na wyrównany, szansa na remis wynosi {p}.",
        "goals_high": "Zapowiada się otwarte spotkanie: {p} szans na co najmniej 3 gole.",
        "goals_low": "Spodziewamy się raczej niskiego wyniku - {p} szans na maksymalnie 2 gole.",
    },
    "en": {
        "intro": [
            "The model projects {xh} expected goals for {home} and {xa} for {away}.",
            "By our numbers {home} should score around {xh} goals and {away} around {xa}.",
            "Model projection: {xh} - {xa} in expected goals.",
        ],
        "home_record": "{home} at home: {s} goals scored and {c} conceded per game.",
        "away_record": "{away} away: {s} goals scored and {c} conceded per game.",
        "form_good": "{team} are in good form ({form}).",
        "form_bad": "{team} are on a weaker run ({form}).",
        "fav_home": "The hosts are favourites with a {p} chance of winning.",
        "fav_away": "The visitors are slight favourites at {p} to win.",
        "balanced": "This looks evenly matched; the draw is rated at {p}.",
        "goals_high": "An open game is expected: {p} chance of 3+ goals.",
        "goals_low": "We expect a tight game - {p} chance of 2 goals or fewer.",
    },
    "de": {
        "intro": [
            "Das Modell erwartet {xh} Tore für {home} und {xa} für {away}.",
            "Nach unseren Zahlen sollte {home} etwa {xh} Tore erzielen, {away} etwa {xa}.",
            "Modellprognose: {xh} - {xa} erwartete Tore.",
        ],
        "home_record": "{home} zu Hause: {s} erzielte und {c} kassierte Tore pro Spiel.",
        "away_record": "{away} auswärts: {s} erzielte und {c} kassierte Tore pro Spiel.",
        "form_good": "{team} ist gut in Form ({form}).",
        "form_bad": "{team} hat eine schwächere Phase ({form}).",
        "fav_home": "Die Gastgeber sind Favorit mit {p} Siegchance.",
        "fav_away": "Die Gäste sind leicht favorisiert: {p} Siegchance.",
        "balanced": "Ein ausgeglichenes Spiel; ein Remis liegt bei {p}.",
        "goals_high": "Ein offenes Spiel ist zu erwarten: {p} Chance auf 3+ Tore.",
        "goals_low": "Eher ein knappes Spiel - {p} Chance auf höchstens 2 Tore.",
    },
    "es": {
        "intro": [
            "El modelo proyecta {xh} goles esperados para {home} y {xa} para {away}.",
            "Según nuestros números, {home} debería marcar unos {xh} goles y {away} unos {xa}.",
            "Proyección del modelo: {xh} - {xa} en goles esperados.",
        ],
        "home_record": "{home} en casa: {s} goles a favor y {c} en contra por partido.",
        "away_record": "{away} fuera: {s} goles a favor y {c} en contra por partido.",
        "form_good": "{team} llega en buena forma ({form}).",
        "form_bad": "{team} atraviesa una racha floja ({form}).",
        "fav_home": "El local es favorito con un {p} de probabilidad de ganar.",
        "fav_away": "El visitante es ligeramente favorito: {p} de ganar.",
        "balanced": "Partido igualado; el empate está en {p}.",
        "goals_high": "Se espera un partido abierto: {p} de probabilidad de 3+ goles.",
        "goals_low": "Esperamos un partido cerrado: {p} de 2 goles o menos.",
    },
}


def pct(p):
    return f"{round(p * 100)}%"


def num(x, lang):
    s = f"{x:.1f}"
    return s.replace(".", ",") if lang in ("pl", "de", "es") else s


def analysis(lang, match, pred, home_info, away_info):
    t = ANALYSIS[lang]
    home, away = match["home"], match["away"]
    probs = pred["probs"]
    seed = int(str(match["id"]).encode().hex(), 16) if not isinstance(match["id"], int) else match["id"]
    out = [t["intro"][seed % len(t["intro"])].format(
        home=home, away=away, xh=num(pred["xg_home"], lang), xa=num(pred["xg_away"], lang))]

    if home_info and home_info["home_scored"] is not None:
        out.append(t["home_record"].format(home=home, s=num(home_info["home_scored"], lang),
                                           c=num(home_info["home_conceded"], lang)))
    if away_info and away_info["away_scored"] is not None:
        out.append(t["away_record"].format(away=away, s=num(away_info["away_scored"], lang),
                                           c=num(away_info["away_conceded"], lang)))
    for team, info in ((home, home_info), (away, away_info)):
        if info and len(info["form"]) >= 4:
            wins, losses = info["form"].count("W"), info["form"].count("L")
            if wins >= 3:
                out.append(t["form_good"].format(team=team, form=info["form"]))
            elif losses >= 3:
                out.append(t["form_bad"].format(team=team, form=info["form"]))

    if probs["1"] >= 0.5:
        out.append(t["fav_home"].format(p=pct(probs["1"])))
    elif probs["2"] >= 0.42 and probs["2"] > probs["1"]:
        out.append(t["fav_away"].format(p=pct(probs["2"])))
    elif probs["X"] >= 0.28:
        out.append(t["balanced"].format(p=pct(probs["X"])))
    if probs["O25"] >= 0.58:
        out.append(t["goals_high"].format(p=pct(probs["O25"])))
    elif probs["U25"] >= 0.58:
        out.append(t["goals_low"].format(p=pct(probs["U25"])))
    return " ".join(out)
