-- ============================================================
-- Turni Reparto v3 — registrazione autonoma medici
-- Esegui DOPO schema-v2-auth.sql
-- ============================================================

-- Esiste un profilo primario nel reparto?
create or replace function reparto_has_primario()
returns boolean language sql stable security definer set search_path = public as $$
  select exists (select 1 from profiles where ruolo = 'primario');
$$;

grant execute on function reparto_has_primario() to authenticated;

-- Iscrizione autonoma: crea profilo medico e voce in organico (turni_data)
create or replace function register_medico(p_nome text)
returns json language plpgsql security definer set search_path = public as $$
declare
  v_uid uuid := auth.uid();
  v_email text;
  v_nome text := trim(p_nome);
  v_mid text;
  v_fa_turni boolean;
  v_med jsonb;
  v_data jsonb;
  v_org jsonb;
begin
  if v_uid is null then raise exception 'Non autenticato'; end if;
  if length(v_nome) < 2 then raise exception 'Inserisci il cognome (minimo 2 caratteri)'; end if;
  if exists (select 1 from profiles where id = v_uid) then
    raise exception 'Account già registrato — effettua l''accesso';
  end if;
  select email into v_email from auth.users where id = v_uid;

  -- Primo iscritto: può assegnare compilatori finché non esiste un primario
  v_fa_turni := not exists (select 1 from profiles);

  v_mid := 'm' || substr(replace(gen_random_uuid()::text, '-', ''), 1, 8);

  insert into profiles (id, medico_id, ruolo, fa_turni, nome)
  values (v_uid, v_mid, 'medico', v_fa_turni, v_nome);

  v_med := jsonb_build_object(
    'id', v_mid,
    'nome', v_nome,
    'attivo', true,
    'puoNotte', true,
    'puoWeekend', true,
    'oreSett', 38,
    'decCalabria', false,
    'competenze', jsonb_build_object('AI', true, 'AD', true, 'AR', true),
    'email', coalesce(v_email, ''),
    'ruolo', 'medico',
    'faTurni', v_fa_turni
  );

  select data into v_data from turni_data where id = 'main' for update;
  if v_data is null then v_data := '{}'::jsonb; end if;
  v_org := coalesce(v_data->'organico', '[]'::jsonb);
  v_org := v_org || v_med;
  v_data := jsonb_set(v_data, '{organico}', v_org, true);

  insert into turni_data (id, data, updated_at)
  values ('main', v_data, now())
  on conflict (id) do update set data = excluded.data, updated_at = now();

  return json_build_object('ok', true, 'medico_id', v_mid, 'nome', v_nome, 'fa_turni', v_fa_turni);
end;
$$;

grant execute on function register_medico(text) to authenticated;
