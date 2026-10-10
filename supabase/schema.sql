-- FormaBet: konta użytkowników, komentarze i zapisane ustawienia.
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
