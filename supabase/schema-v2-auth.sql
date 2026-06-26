-- ============================================================
-- Turni Reparto v2 — login, ruoli, storico modifiche
-- Esegui DOPO schema.sql (o su progetto nuovo: esegui tutto insieme)
-- In Supabase: Authentication → Providers → Email → disattiva
-- "Confirm email" se volete accesso immediato senza conferma.
-- ============================================================

-- Profili utente (collegati a auth.users)
create table if not exists profiles (
  id uuid primary key references auth.users(id) on delete cascade,
  medico_id text not null unique,
  ruolo text not null default 'medico' check (ruolo in ('primario', 'medico')),
  fa_turni boolean not null default false,
  nome text not null,
  updated_at timestamptz not null default now()
);

-- Inviti per attivazione account medici
create table if not exists medico_invites (
  medico_id text primary key,
  email text not null,
  invite_code text not null unique,
  claimed_by uuid references auth.users(id),
  created_at timestamptz not null default now()
);

-- Storico modifiche ai turni
create table if not exists turni_audit (
  id bigserial primary key,
  created_at timestamptz not null default now(),
  user_id uuid references auth.users(id),
  user_nome text not null,
  azione text not null,
  dettaglio jsonb not null default '{}'::jsonb
);

create index if not exists turni_audit_created_at_idx on turni_audit (created_at desc);

alter table profiles enable row level security;
alter table medico_invites enable row level security;
alter table turni_audit enable row level security;

-- Helper: utente corrente è primario
create or replace function is_primario()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from profiles where id = auth.uid() and ruolo = 'primario'
  );
$$;

-- Helper: utente può modificare i turni
create or replace function can_edit_turni()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (
    select 1 from profiles where id = auth.uid() and (ruolo = 'primario' or fa_turni = true)
  );
$$;

-- Profili: tutti gli autenticati leggono; primario aggiorna tutti; ciascuno aggiorna il proprio nome
drop policy if exists "profiles_select" on profiles;
create policy "profiles_select" on profiles for select to authenticated using (true);

drop policy if exists "profiles_update_primario" on profiles;
create policy "profiles_update_primario" on profiles for update to authenticated
  using (is_primario()) with check (is_primario());

drop policy if exists "profiles_update_self" on profiles;
create policy "profiles_update_self" on profiles for update to authenticated
  using (id = auth.uid()) with check (id = auth.uid());

drop policy if exists "profiles_insert" on profiles;
create policy "profiles_insert" on profiles for insert to authenticated
  with check (id = auth.uid() or is_primario());

-- Inviti
drop policy if exists "invites_select" on medico_invites;
create policy "invites_select" on medico_invites for select to authenticated using (true);

drop policy if exists "invites_manage_primario" on medico_invites;
create policy "invites_manage_primario" on medico_invites for all to authenticated
  using (is_primario()) with check (is_primario());

-- Audit: lettura per autenticati; scrittura per chi modifica turni (o primario)
drop policy if exists "audit_select" on turni_audit;
create policy "audit_select" on turni_audit for select to authenticated using (true);

drop policy if exists "audit_insert" on turni_audit;
create policy "audit_insert" on turni_audit for insert to authenticated with check (true);

-- Aggiorna RLS su turni_data: solo utenti autenticati
drop policy if exists "Lettura turni" on turni_data;
drop policy if exists "Scrittura turni" on turni_data;
drop policy if exists "Inserimento turni" on turni_data;

create policy "turni_data_select" on turni_data for select to authenticated using (true);
create policy "turni_data_update" on turni_data for update to authenticated using (true);
create policy "turni_data_insert" on turni_data for insert to authenticated with check (true);

-- Primo accesso: attiva il reparto (solo se non esiste ancora un primario)
create or replace function setup_primario(p_medico_id text, p_nome text)
returns json language plpgsql security definer set search_path = public as $$
declare v_uid uuid := auth.uid();
begin
  if v_uid is null then raise exception 'Non autenticato'; end if;
  if exists (select 1 from profiles where ruolo = 'primario') then
    raise exception 'Reparto già attivato';
  end if;
  insert into profiles (id, medico_id, ruolo, fa_turni, nome)
  values (v_uid, p_medico_id, 'primario', true, p_nome);
  return json_build_object('ok', true, 'medico_id', p_medico_id);
end;
$$;

grant execute on function setup_primario(text, text) to authenticated;

-- Attivazione account medico con codice invito
create or replace function claim_invite(p_code text)
returns json language plpgsql security definer set search_path = public as $$
declare
  v_uid uuid := auth.uid();
  v_invite medico_invites%rowtype;
  v_email text;
  v_nome text;
begin
  if v_uid is null then raise exception 'Non autenticato'; end if;
  if exists (select 1 from profiles where id = v_uid) then
    raise exception 'Account già collegato';
  end if;
  select * into v_invite from medico_invites
    where invite_code = upper(trim(p_code)) and claimed_by is null;
  if not found then raise exception 'Codice invito non valido o già usato'; end if;
  select email into v_email from auth.users where id = v_uid;
  if lower(v_email) <> lower(v_invite.email) then
    raise exception 'L''email dell''account non coincide con quella dell''invito';
  end if;
  select coalesce(
    (select elem->>'nome' from turni_data, jsonb_array_elements(data->'organico') elem
     where id = 'main' and elem->>'id' = v_invite.medico_id limit 1),
    v_invite.email
  ) into v_nome;
  insert into profiles (id, medico_id, ruolo, fa_turni, nome)
  values (
    v_uid, v_invite.medico_id, 'medico',
    coalesce((
      select (elem->>'faTurni')::boolean from turni_data, jsonb_array_elements(data->'organico') elem
      where id = 'main' and elem->>'id' = v_invite.medico_id limit 1
    ), false),
    v_nome
  );
  update medico_invites set claimed_by = v_uid where medico_id = v_invite.medico_id;
  return json_build_object('ok', true, 'medico_id', v_invite.medico_id, 'nome', v_nome);
end;
$$;

grant execute on function claim_invite(text) to authenticated;
