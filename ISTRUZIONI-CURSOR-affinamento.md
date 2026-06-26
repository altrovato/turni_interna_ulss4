# Istruzioni per Cursor — Affinamento motore `generaBozza`

> **STATO: APPLICATO in `index.html` e validato end-to-end** (giugno 2026). Documento conservato
> come registro delle modifiche. Cambiamenti in produzione: parametro `idealeFeriale`, riempimento
> reparto feriale a target con surplus → `/`, recupero lunedì `RF`, filtro martedì che include `RF`.

Esito della validazione del motore reale contro i 7 calendari veri (gen–lug 2026) e correzioni
applicate in `index.html`.

---

## 1. Contesto: cosa dice la validazione

Ho eseguito il motore reale `generaBozza` su tutti i mesi storici, partendo dagli input fissi
veri (weekend + assenze; Brondolin Dec. Calabria; Teso in maternità gen–mar), e confrontato il
risultato con i turni reali. **Il motore è già aderente su quasi tutto:**

- **Copertura minima** sempre rispettata (come o meglio del reale).
- **Ritmo settimanale** N e G ≈ 1 a settimana per medico (μ 3,8–4,4/mese), identico al reale.
- **Regole guardia**: mai notte→guardia il giorno dopo; Dec. Calabria **0** notti/guardie/weekend;
  martedì-post-domenica solo 1 slittamento su 6 mesi.
- **Rotazione weekend**: coerente con i calendari (5 ruoli VN·SN·SG·MN·MG su N medici).

**Unica divergenza sistematica → il reparto feriale viene riempito troppo.** Il motore mette
*tutti* i disponibili a `M`, quindi presenze sopra l'ideale e ogni medico chiude in **attivo** di ore;
i calendari veri tengono il reparto più snello (presenze vicine al minimo) e saldi mensili leggermente
in deficit, riassorbiti tra i mesi.

| Giorno feriale | Reparto/g | Presenti/g | Saldo ore medio/medico |
|---|---|---|---|
| **Reale** | ~3,6 | **6,61** | da −1 a −17 |
| **Motore attuale** | ~4,6 | **7,37** | da +5 a +17 |
| **Motore con la patch** | ~3,9 | **6,88** | da −3 a +11 |

La patch (sotto) avvicina presenze e ore alla realtà mantenendo la copertura minima.

---

## 2. Correzione — riempimento reparto feriale "fino al target"

Obiettivo: nei giorni feriali normali riempire il reparto **fino a un target di presenze
parametrico** (default 7, regolabile dal primario), e lasciare il **surplus a `/`** scegliendo di
liberare chi è **più avanti** sul monteore (così le ore convergono verso zero invece che in positivo).

### 2a. Nuovo parametro `DB.req.idealeFeriale`

**Default in `nuovoDB()`** (oggetto `req`, intorno alla riga 950): aggiungi `idealeFeriale: 7`.

```js
req: {notte:1, giorno:1, reparto:3, tot:6, ideale:7, idealeFeriale:7},
```

**Migrazione** (blocco che normalizza `DB.req`, intorno alle righe 1254–1255 e 1292–1293):
aggiungi dopo la normalizzazione di `ideale`:

```js
if(DB.req.idealeFeriale==null) DB.req.idealeFeriale = DB.req.ideale || 7;
```

### 2b. Campo nell'UI Impostazioni

Dopo l'input `reqIdeale` (riga ~623) aggiungi:

```html
<label class="fld">Target presenze giorni feriali <input type="number" id="reqIdealeFeriale" min="0" value="7" style="width:80px"></label>
```

In `renderImpostazioni()` (dove si valorizzano gli input, righe ~2638–2642) aggiungi:

```js
document.getElementById("reqIdealeFeriale").value = DB.req.idealeFeriale;
```

Tra gli `onchange` (righe ~3494–3498) aggiungi:

```js
document.getElementById("reqIdealeFeriale").onchange=e=>{DB.req.idealeFeriale=+e.target.value;save();renderTurni();renderRiepilogo();};
```

### 2c. Logica nel motore — branch "GIORNO LAVORATIVO NORMALE"

In `generaBozza()` **sostituisci** il blocco `else { … }` del giorno lavorativo normale
(attualmente righe ~2792–2808, quello con il commento *"al lavoro tutti i disponibili"*):

**PRIMA:**
```js
    } else {
      // --- GIORNO LAVORATIVO NORMALE (lun–sab): al lavoro tutti i disponibili ---
      // Ogni medico deve chiudere il monteore (≈1N+1G+3M a settimana), quindi riempie
      // il reparto per chi non è già di guardia/smonto/ferie/recupero, tranne chi ha desiderata.
      let repCand=meds.filter(m=>baseElig(m,g,we) && eligDecCalGiorno(m,g) && !wantsFree(m,g));
      repCand.sort((a,b)=> deficit(a)-deficit(b)); // prima chi è più indietro sul monteore
      repCand.forEach(m=>{ setCella(m.id,g,"M"); cntWork[m.id]++; addOre(m,"M"); });

      // --- Garanzia copertura minima: se le desiderate scendono sotto il minimo, riempi anche loro ---
      c=contaGiorno(g);
      let rNeed=Math.max(DB.req.reparto-c.reparto, DB.req.tot-c.presenti);
      if(rNeed>0){
        let fallback=meds.filter(m=>baseElig(m,g,we) && eligDecCalGiorno(m,g));
        fallback.sort((a,b)=> deficit(a)-deficit(b));
        for(let i=0;i<fallback.length && rNeed>0;i++){ setCella(fallback[i].id,g,"M"); cntWork[fallback[i].id]++; addOre(fallback[i],"M"); rNeed--; }
      }
    }
```

**DOPO:**
```js
    } else {
      // --- GIORNO LAVORATIVO NORMALE (lun–sab): riempi il reparto FINO AL TARGET di presenze ---
      // Non si mette più "tutti" a reparto: si raggiunge il target (idealeFeriale, default 7,
      // incl. N+G+SN già presenti) e il surplus va a "/". Si lavora prima chi è più indietro
      // sul monteore, così i saldi ore convergono verso zero invece di accumulare ore in eccesso.
      const targetPres = (DB.req.idealeFeriale!=null ? DB.req.idealeFeriale : (DB.req.ideale||7));
      c=contaGiorno(g);
      let need=Math.max(DB.req.reparto - c.reparto, targetPres - c.presenti);
      let repCand=meds.filter(m=>baseElig(m,g,we) && eligDecCalGiorno(m,g) && !wantsFree(m,g));
      repCand.sort((a,b)=> deficit(a)-deficit(b)); // prima chi è più indietro sul monteore
      for(let i=0;i<repCand.length && need>0;i++){ setCella(repCand[i].id,g,"M"); cntWork[repCand[i].id]++; addOre(repCand[i],"M"); need--; }

      // --- Garanzia copertura minima: se le desiderate scendono sotto il minimo, riempi anche loro ---
      c=contaGiorno(g);
      let rNeed=Math.max(DB.req.reparto-c.reparto, DB.req.tot-c.presenti);
      if(rNeed>0){
        let fallback=meds.filter(m=>baseElig(m,g,we) && eligDecCalGiorno(m,g));
        fallback.sort((a,b)=> deficit(a)-deficit(b));
        for(let i=0;i<fallback.length && rNeed>0;i++){ setCella(fallback[i].id,g,"M"); cntWork[fallback[i].id]++; addOre(fallback[i],"M"); rNeed--; }
      }

      // --- Surplus (chi è più avanti sul monteore) → libero "/" ---
      meds.forEach(m=>{ if(baseElig(m,g,we) && eligDecCalGiorno(m,g) && getCella(m.id,g)==="") setCella(m.id,g,"/"); });
    }
```

**Note di implementazione:**
- L'ordinamento per `deficit` ascendente garantisce che a lavorare resti chi ha meno ore;
  chi è già "a posto" o avanti viene liberato. Si auto-bilancia giorno per giorno.
- Il `targetPres` conta le presenze **complessive** (reparto + guardia diurna + N + SN), quindi su un
  giorno con 1N+1G+1SN bastano ~4 in reparto per arrivare a 7.
- Gli **ambulatori** (blocco `assign()` subito dopo) continuano a funzionare: convertono una `M`
  esistente; con il target ≥7 resta sempre qualcuno in reparto con la competenza richiesta.
- Per i mesi con poche assenze il primario può **abbassare** il target (es. 6) per un reparto più
  snello; per i mesi scarichi può alzarlo.

---

## 3. Aggiornare la documentazione

In `REGOLE-ENGINE.md` §2 ("Giorni feriali normali") sostituire la frase *"obiettivo: tutti i
disponibili al lavoro"* con: *"obiettivo: raggiungere il target di presenze feriali
(`idealeFeriale`, default 7, regolabile); il surplus va a `/`, liberando chi è più avanti sul
monteore"*. Aggiungere `idealeFeriale` alla tabella dei parametri `DB.req`.

---

## 4. Note minori (NON urgenti, valutare a parte)

- **Martedì post-domenica**: 1 caso su 6 mesi in cui il motore ha messo guardia il martedì a chi
  aveva fatto guardia domenica + riposo lunedì. La regola prevede eccezioni straordinarie, quindi
  non è bloccante; se si vuole azzerare, irrigidire il filtro `if(dw===2)` includendo anche il caso
  in cui il lunedì sia codificato `R`/`RF` oltre a `/`.
- **Recupero del lunedì**: il motore scrive `R` per il recupero del lunedì dopo guardia domenica;
  nei calendari veri è quasi sempre `RF` (recupero festivo, 24/28 casi). Valutare se uniformare a `RF`.
- **Giorni consecutivi — NESSUN PROBLEMA.** Un primo controllo segnalava serie di 13–14 giorni, ma
  era un **artefatto del banco di prova** (lo smonto `SN` del lunedì dopo un weekend `MN` non veniva
  applicato, mentre nell'app vera sì). Applicando lo smonto come fa l'app, il massimo reale è
  **7 giorni consecutivi** in tutti i mesi, ben sotto il tetto di 12. Da contare solo N/G/M/ambulatori
  (l'`SN` è riposo e spezza la serie, come `isWorkCode`/`consecBefore`).

---

## 5. Come ri-verificare dopo la modifica

Rigenerare la bozza di un paio di mesi storici (es. gennaio e luglio) con gli stessi input fissi e
controllare nel **Riepilogo & Monteore**: le presenze feriali medie devono scendere verso ~7 e i
saldi ore non devono più essere tutti in positivo. La copertura minima (N≥1, G≥1, reparto≥3,
presenti≥6) deve restare verde su tutti i feriali.

*Validato per simulazione del motore reale su gen–lug 2026 — giugno 2026.*
