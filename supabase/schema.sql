-- Esegui in Supabase → SQL Editor (progetto gratuito)
-- Crea una tabella con un solo record condiviso da tutti i dispositivi.

create table if not exists turni_data (
  id text primary key default 'main',
  data jsonb not null default '{}'::jsonb,
  updated_at timestamptz not null default now()
);

insert into turni_data (id, data)
values ('main', '{}'::jsonb)
on conflict (id) do nothing;

alter table turni_data enable row level security;

create policy "Lettura turni"
  on turni_data for select
  using (true);

create policy "Scrittura turni"
  on turni_data for update
  using (true);

create policy "Inserimento turni"
  on turni_data for insert
  with check (true);
