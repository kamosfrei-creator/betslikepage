-- OnePickAway: konta, komentarze, ustawienia, typowanie, łapki i ranking typerów.
-- Uruchom w Supabase: SQL Editor -> New query -> wklej całość -> Run.
-- Logowanie odbywa się linkiem z e-maila (Authentication -> Providers -> Email, "Magic Link").

-- Profil: publiczny nick (adres e-mail nigdy nie jest pokazywany innym).
create table if not exists public.profiles (
  id uuid primary key references auth.users on delete cascade,
  nick text unique not null check (char_length(nick) between 3 and 24 and nick ~ '^[[:alnum:]_.-]+$'),
  created_at timestamptz not null default now()
);

-- Komentarze pod meczami.
create table if not exists public.comments (
  id bigint generated always as identity primary key,
  match_id bigint not null,
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  nick text not null,
  body text not null check (char_length(body) between 1 and 1000),
  hidden boolean not null default false,
  created_at timestamptz not null default now()
);
create index if not exists comments_match_idx on public.comments (match_id, created_at);

-- Zgłoszenia komentarzy do moderacji.
create table if not exists public.reports (
  comment_id bigint not null references public.comments on delete cascade,
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  created_at timestamptz not null default now(),
  primary key (comment_id, user_id)
);

-- Ulubione ligi, obserwowane mecze i kupon - synchronizowane między urządzeniami.
create table if not exists public.user_prefs (
  user_id uuid primary key default auth.uid() references auth.users on delete cascade,
  fav_leagues text[] not null default '{}',
  fav_matches bigint[] not null default '{}',
  slip jsonb not null default '[]',
  updated_at timestamptz not null default now()
);

alter table public.profiles enable row level security;
alter table public.comments enable row level security;
alter table public.reports enable row level security;
alter table public.user_prefs enable row level security;

-- profiles: każdy widzi nicki, każdy tworzy/zmienia tylko swój.
create policy "profiles read" on public.profiles for select using (true);
create policy "profiles insert own" on public.profiles for insert with check (auth.uid() = id);
create policy "profiles update own" on public.profiles for update using (auth.uid() = id);

-- comments: wszyscy widzą nieukryte; zalogowany dodaje pod własnym nickiem; usuwa tylko swoje.
create policy "comments read" on public.comments for select using (not hidden);
create policy "comments insert own" on public.comments for insert with check (
  auth.uid() = user_id
  and nick = (select p.nick from public.profiles p where p.id = auth.uid())
  and hidden = false
);
create policy "comments delete own" on public.comments for delete using (auth.uid() = user_id);

-- reports: zalogowany może zgłosić komentarz; zgłoszenia czyta tylko administrator (panel Supabase).
create policy "reports insert" on public.reports for insert with check (auth.uid() = user_id);

-- user_prefs: tylko właściciel.
create policy "prefs own" on public.user_prefs for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Ochrona przed spamem: maks. 5 komentarzy na minutę na użytkownika.
create or replace function public.comments_rate_limit() returns trigger language plpgsql as $$
begin
  if (select count(*) from public.comments c
      where c.user_id = new.user_id and c.created_at > now() - interval '1 minute') >= 5 then
    raise exception 'rate limit';
  end if;
  return new;
end $$;
drop trigger if exists comments_rate_limit on public.comments;
create trigger comments_rate_limit before insert on public.comments
  for each row execute function public.comments_rate_limit();

-- Moderacja: komentarz ukrywasz w Table Editor -> comments -> hidden = true.
-- Zgłoszone komentarze: select c.*, count(r.*) from comments c join reports r on r.comment_id = c.id group by c.id;

-- =====================================================================
-- Typowanie przez użytkowników, łapki pod typami strony, ranking typerów.
-- Tabelę matches wypełnia automat (GitHub Actions) kluczem service_role:
-- termin, wynik i prawdopodobieństwa modelu. Dzięki temu baza sama wie,
-- kiedy zamknąć typowanie i ile punktów dać za trafienie.

create table if not exists public.matches (
  id bigint primary key,
  utc timestamptz not null,
  comp text not null,
  home text not null,
  away text not null,
  status text not null,
  hg int,
  ag int,
  p1 real, px real, p2 real,
  pick text,        -- typ strony (bezpieczny)
  pickr text,       -- typ strony z kursem 1,5-2,0
  updated_at timestamptz not null default now()
);
create index if not exists matches_utc_idx on public.matches (utc);

-- Typ użytkownika 1/X/2 - jeden na mecz, zmiana możliwa do rozpoczęcia meczu.
create table if not exists public.predictions (
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  match_id bigint not null references public.matches on delete cascade,
  outcome text not null check (outcome in ('1', 'X', '2')),
  created_at timestamptz not null default now(),
  primary key (user_id, match_id)
);
create index if not exists predictions_match_idx on public.predictions (match_id);

-- Łapka w górę / w dół pod typem strony (kind: safe = typ główny, range = kurs 1,5-2,0).
create table if not exists public.pick_votes (
  user_id uuid not null default auth.uid() references auth.users on delete cascade,
  match_id bigint not null references public.matches on delete cascade,
  kind text not null check (kind in ('safe', 'range')),
  v smallint not null check (v in (-1, 1)),
  created_at timestamptz not null default now(),
  primary key (user_id, match_id, kind)
);
create index if not exists pick_votes_match_idx on public.pick_votes (match_id);

alter table public.matches enable row level security;
alter table public.predictions enable row level security;
alter table public.pick_votes enable row level security;

drop policy if exists "matches read" on public.matches;
create policy "matches read" on public.matches for select using (true);

-- Cudze typy widać dopiero po rozpoczęciu meczu (nie da się ich kopiować).
drop policy if exists "predictions read" on public.predictions;
create policy "predictions read" on public.predictions for select using (
  auth.uid() = user_id or exists (select 1 from public.matches m where m.id = match_id and m.utc <= now()));
drop policy if exists "predictions insert" on public.predictions;
create policy "predictions insert" on public.predictions for insert with check (
  auth.uid() = user_id
  and exists (select 1 from public.profiles p where p.id = auth.uid())
  and exists (select 1 from public.matches m where m.id = match_id and m.utc > now()));
drop policy if exists "predictions update" on public.predictions;
create policy "predictions update" on public.predictions for update using (auth.uid() = user_id) with check (
  auth.uid() = user_id and exists (select 1 from public.matches m where m.id = match_id and m.utc > now()));
drop policy if exists "predictions delete" on public.predictions;
create policy "predictions delete" on public.predictions for delete using (
  auth.uid() = user_id and exists (select 1 from public.matches m where m.id = match_id and m.utc > now()));

drop policy if exists "votes read own" on public.pick_votes;
create policy "votes read own" on public.pick_votes for select using (auth.uid() = user_id);
drop policy if exists "votes write own" on public.pick_votes;
create policy "votes write own" on public.pick_votes for all using (auth.uid() = user_id) with check (auth.uid() = user_id);

-- Punkty: trafienie = kurs sprawiedliwy modelu (1 / prawdopodobieństwo), maks. 10.
-- Trafiony faworyt (70%) daje ~1,4 pkt, trafiony remis (28%) ~3,6 pkt.
create or replace view public.scored_predictions as
select pr.user_id, pr.match_id, pr.outcome, m.utc, m.comp, m.home, m.away, m.hg, m.ag, m.status,
       case when m.hg > m.ag then '1' when m.hg = m.ag then 'X' else '2' end as result,
       case when m.status <> 'FINISHED' or m.hg is null then null
            when (case when m.hg > m.ag then '1' when m.hg = m.ag then 'X' else '2' end) = pr.outcome
              then round(least(10, 1 / greatest(0.1, coalesce(case pr.outcome when '1' then m.p1 when 'X' then m.px else m.p2 end, 0.4)))::numeric, 2)
            else 0 end as points
from public.predictions pr join public.matches m on m.id = pr.match_id
where m.utc <= now();

-- Ranking typerów: punkty z 30 dni i od początku, trafność.
create or replace view public.leaderboard as
select p.nick,
       count(s.points) as n,
       count(*) filter (where s.points > 0) as hits,
       coalesce(sum(s.points), 0) as points,
       coalesce(sum(s.points) filter (where s.utc > now() - interval '30 days'), 0) as points30,
       count(s.points) filter (where s.utc > now() - interval '30 days') as n30
from public.scored_predictions s join public.profiles p on p.id = s.user_id
group by p.nick
having count(s.points) > 0;

-- Publiczna historia typów (profil typera) - tylko mecze już rozpoczęte.
create or replace view public.tipster_history as
select p.nick, s.match_id, s.outcome, s.utc, s.comp, s.home, s.away, s.hg, s.ag, s.status, s.points
from public.scored_predictions s join public.profiles p on p.id = s.user_id;

-- Głosy społeczności na mecz (kto wygra?) - same liczby, bez nicków.
create or replace view public.prediction_counts as
select match_id,
       count(*) filter (where outcome = '1') as n1,
       count(*) filter (where outcome = 'X') as nx,
       count(*) filter (where outcome = '2') as n2
from public.predictions group by match_id;

-- Łapki pod typami strony.
create or replace view public.vote_counts as
select match_id, kind, count(*) filter (where v = 1) as up, count(*) filter (where v = -1) as down
from public.pick_votes group by match_id, kind;

-- Najlepiej oceniane typy strony (ostatnie 2 dni i nadchodzące).
create or replace view public.top_voted as
select m.id as match_id, v.kind, m.utc, m.comp, m.home, m.away, m.hg, m.ag, m.status,
       case v.kind when 'safe' then m.pick else m.pickr end as market, v.up, v.down
from public.vote_counts v join public.matches m on m.id = v.match_id
where m.utc > now() - interval '2 days' and v.up > 0;

grant select on public.leaderboard, public.tipster_history, public.prediction_counts,
  public.vote_counts, public.top_voted to anon, authenticated;
revoke all on public.scored_predictions from anon, authenticated;
