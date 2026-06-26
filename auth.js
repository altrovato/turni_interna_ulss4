"use strict";
/* Autenticazione, permessi e storico modifiche (Supabase) */
window.TurniAuth = (function(){
  let sb = null;
  let session = null;
  let profile = null;
  let onAuthChange = null;

  function configured(){
    const c = window.TURNI_CONFIG || {};
    const url = (c.supabaseUrl || "").trim();
    const key = (c.supabaseKey || "").trim();
    return !!(url && key && !url.includes("TUOPROGETTO") && !key.includes("LA_TUA_ANON"));
  }

  function client(){
    if(!configured()) return null;
    if(!sb && window.supabase){
      sb = window.supabase.createClient(
        window.TURNI_CONFIG.supabaseUrl.trim(),
        window.TURNI_CONFIG.supabaseKey.trim()
      );
    }
    return sb;
  }

  function accessToken(){
    return session?.access_token || null;
  }

  async function init(){
    const c = client();
    if(!c) return false;
    const { data } = await c.auth.getSession();
    session = data.session;
    if(session) await loadProfile();
    if(session) await refreshRepartoMeta();
    c.auth.onAuthStateChange(async (_ev, s)=>{
      session = s;
      if(s){ await loadProfile(); await refreshRepartoMeta(); }
      else { profile = null; repartoHasPrimario = null; }
      if(onAuthChange) onAuthChange(isLoggedIn());
    });
    return isLoggedIn();
  }

  async function loadProfile(){
    const c = client();
    if(!c || !session) { profile = null; return null; }
    const { data, error } = await c.from("profiles").select("*").eq("id", session.user.id).maybeSingle();
    if(error) throw error;
    profile = data;
    return profile;
  }

  function isLoggedIn(){ return !!(session && profile); }
  function hasSession(){ return !!session; }
  function requiresAuth(){ return configured(); }

  function current(){
    if(!profile) return null;
    return {
      userId: profile.id,
      medicoId: profile.medico_id,
      ruolo: profile.ruolo,
      faTurni: profile.fa_turni,
      nome: profile.nome,
      email: session?.user?.email || ""
    };
  }

  let repartoHasPrimario = null;

  function isPrimario(){ return profile?.ruolo === "primario"; }
  function hasPrimarioInReparto(){ return repartoHasPrimario === true; }
  function canEditTurni(){ return isPrimario() || !!profile?.fa_turni; }
  function canManageOrganico(){
    return isPrimario() || (!hasPrimarioInReparto() && !!profile?.fa_turni);
  }
  function canManageSettings(){
    return isPrimario() || (!hasPrimarioInReparto() && !!profile?.fa_turni);
  }

  async function refreshRepartoMeta(){
    const c = client();
    if(!c || !session){ repartoHasPrimario = null; return null; }
    try{
      const { data, error } = await c.rpc("reparto_has_primario");
      if(error) throw error;
      repartoHasPrimario = !!data;
    }catch(e){
      console.warn("reparto_has_primario:", e);
      repartoHasPrimario = null;
    }
    return repartoHasPrimario;
  }

  async function signIn(email, password){
    const c = client();
    const { data, error } = await c.auth.signInWithPassword({ email: email.trim(), password });
    if(error) throw error;
    session = data.session;
    await loadProfile();
    if(!profile) throw new Error("Account senza profilo. Usa «Registrati» per completare l'iscrizione.");
    return current();
  }

  async function signUp(email, password){
    const c = client();
    const { data, error } = await c.auth.signUp({ email: email.trim(), password });
    if(error) throw error;
    session = data.session;
    return data;
  }

  async function signOut(){
    const c = client();
    if(c) await c.auth.signOut();
    session = null;
    profile = null;
  }

  async function registerMedico(nome){
    const c = client();
    const { data, error } = await c.rpc("register_medico", { p_nome: nome.trim() });
    if(error) throw error;
    await loadProfile();
    await refreshRepartoMeta();
    return data;
  }

  async function setupPrimario(medicoId, nome){
    const c = client();
    const { data, error } = await c.rpc("setup_primario", { p_medico_id: medicoId, p_nome: nome });
    if(error) throw error;
    await loadProfile();
    return data;
  }

  async function claimInvite(code){
    const c = client();
    const { data, error } = await c.rpc("claim_invite", { p_code: code.trim() });
    if(error) throw error;
    await loadProfile();
    return data;
  }

  async function upsertInvite(medicoId, email, inviteCode){
    const c = client();
    const { error } = await c.from("medico_invites").upsert({
      medico_id: medicoId,
      email: email.trim().toLowerCase(),
      invite_code: inviteCode.toUpperCase()
    }, { onConflict: "medico_id" });
    if(error) throw error;
  }

  async function fetchInvites(){
    const c = client();
    const { data, error } = await c.from("medico_invites").select("*");
    if(error) throw error;
    return data || [];
  }

  async function updateProfileFlags(medicoId, fields){
    const c = client();
    const { error } = await c.from("profiles").update(fields).eq("medico_id", medicoId);
    if(error) throw error;
    if(profile?.medico_id === medicoId){
      Object.assign(profile, fields);
    }
  }

  async function logAudit(azione, dettaglio){
    const cur = current();
    const entry = {
      user_id: cur?.userId || null,
      user_nome: cur?.nome || "Sistema",
      azione,
      dettaglio
    };
    const c = client();
    if(!c || !session) return entry;
    try{
      await c.from("turni_audit").insert(entry);
    }catch(e){
      console.warn("Audit cloud:", e);
    }
    return entry;
  }

  async function fetchAudit(limit){
    const c = client();
    if(!c || !session) return [];
    const { data, error } = await c.from("turni_audit")
      .select("*")
      .order("created_at", { ascending: false })
      .limit(limit || 200);
    if(error) throw error;
    return data || [];
  }

  function genInviteCode(){
    return Math.random().toString(36).slice(2, 8).toUpperCase();
  }

  return {
    configured, client, accessToken, init, isLoggedIn, hasSession, requiresAuth, current,
    isPrimario, hasPrimarioInReparto, canEditTurni, canManageOrganico, canManageSettings,
    signIn, signUp, signOut, registerMedico, setupPrimario, claimInvite,
    upsertInvite, fetchInvites, updateProfileFlags, refreshRepartoMeta,
    logAudit, fetchAudit, genInviteCode,
    set onAuthChange(fn){ onAuthChange = fn; }
  };
})();
