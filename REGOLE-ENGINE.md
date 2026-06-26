# Regole dell'engine per la creazione dei turni

Documento di riferimento per il motore automatico di bozza (`generaBozza`), la rotazione weekend, i controlli e le regole operative del reparto.  
Include le regole originali (`regole turni.txt`), quelle aggiunte durante lo sviluppo dell'app e la loro implementazione in `index.html`.

---

## 1. Flusso di generazione (ordine consigliato)

L'engine non lavora in isolamento: prima si fissano vincoli «duri», poi la bozza riempie il resto.

1. **Weekend del bimestre** — compilati in anticipo (tab *Weekend* o Wizard passo 1), poi **Applica al bimestre**.
2. **Assenze e desiderate** — ferie, permessi, malattia, congresso, desiderate (Wizard passo 2).
3. **Genera bozza** — riempie **solo le celle vuote**; non sovrascrive turni già inseriti.
4. **Controllo regole** — avvisi in griglia e nel riepilogo; correzioni manuali.
5. **Export / stampa** — settimane complete lun–dom (anche giorni fuori mese).

---

## 2. Copertura giornaliera

Parametri di default (`DB.req`):

| Voce | Valore | Significato |
|------|--------|-------------|
| **Notte (N)** | 1 | Monto / guardia notte |
| **Guardia diurna (G)** | 1 | Guardia 8–20 (anche da mezze guardie) |
| **In reparto (M)** | 3 | Mattine in reparto |
| **Minimo presenti** | 6 | 3 reparto + 1 guardia + 1 N + 1 SN |
| **Ideale presenti** | 7 | Target della bozza oltre il minimo (festivi) |
| **Ideale feriali** | 7 | Target presenze giorni feriali normali (`idealeFeriale`) |

**Formula presenti:** reparto + guardia diurna + monto (N) + **smonto (SN)**.  
Etichetta in app: *Presenti compreso smonto notte*.

### Domenica (regola speciale)

- C'è **solo il medico di guardia** (N e/o G, eventualmente GM/GP/AR/GP smezzate).
- **Nessun giro in reparto** (M, ambulatori, M/AI, M/AD, M/AR, AR…).
- I requisiti **minimo 6** e **ideale 7** **non si applicano**.
- Chi non è di guardia va a `/` (libero).
- Assegnare reparto di domenica genera avviso bloccante.

### Festivi infrasettimanali

- Copertura **ridotta** verso minimo/ideale, non tutto l'organico al lavoro.
- Chi lavora il festivo matura **recupero festivo (RF)**.

### Giorni feriali normali (lun–sab, non festivo)

- Obiettivo: raggiungere il **target di presenze feriali** (`idealeFeriale`, default 7, regolabile); il surplus va a `/`, liberando chi è più avanti sul monteore.
- Se le desiderate fanno scendere sotto il minimo, la bozza **forza comunque** il riempimento fino al minimo.

---

## 3. Regole di guardia e recupero

Regole operative del reparto (da `regole turni.txt` e implementazione engine):

### Lunedì

1. **Recupero prioritario** a chi ha fatto **guardia diurna (G) la domenica** → automaticamente **RF** il lunedì (recupero festivo, come nei calendari reali).
2. **Guardia diurna** preferita a chi ha avuto **weekend libero** (sabato e domenica senza turno lavorativo).

### Venerdì

- **Guardia diurna** preferita a chi ha **sabato notte (N)** o **weekend libero**.

### Martedì

- **Evitare guardia** a chi ha fatto **guardia domenica (G)** e **riposo lunedì (R, RF o /)**.  
  Eccezioni possibili solo in casi straordinari (avviso, non blocco assoluto in inserimento manuale).

### Recuperi da assegnare

| Tipo | Codice | Quando matura | Dove si colloca |
|------|--------|---------------|-----------------|
| Recupero generico | **R** | Recupero compensativo generico | Assegnato a mano se serve |
| Recupero festivo | **RF** | Lavoro in giorno festivo (M, G, ambulatori) **e lunedì dopo guardia domenica** | Lun–ven non festivo, cella vuota / lunedì post-domenica |
| Recupero notte | **RN** | Notte di sabato, domenica o su festivo | Lun–ven non festivo, cella vuota |

**Mezzi festivi:** chi fa la **mattina del festivo** matura recupero festivo (RF).

**Notti da recuperare:** sabato, domenica e notti che cadono su festivo → RN.

I recuperi (R/RF/RN) valgono **0 ore** nel monteore.

### Riposo post-turno

- **Niente guardia diurna il giorno dopo una notte (N) o una guardia (G)** (`riposatoIeri`).
- Inserendo **N** manualmente (o da weekend), il giorno dopo si imposta automaticamente **SN** (smonto).

### Giorni lavorativi consecutivi

- **Massimo 12** giorni lavorativi consecutivi (N, G, M, ambulatori).
- Oltre 12 → avviso **err** (bloccante nei controlli).
- Obiettivo operativo: restare **molto sotto** (≈1 notte + 1 guardia a settimana per medico).

---

## 4. Guardie smezzate con le reumatologhe

Accordo operativo codificato in tabella:

| Codice | Significato | Ore |
|--------|-------------|-----|
| **GM** | Guardia diurna mattina (8–14) — chi viene alle 8 | 6 |
| **GP** | Guardia diurna pomeriggio (14–20) | 6 |
| **AR/GP** | Ambulatorio reumato mattina + guardia pomeriggio (reumatologa) | 11 |

- **GM + GP** oppure **GM + AR/GP** contano insieme come **1 guardia diurna** nel conteggio copertura.
- L'accordo su *chi* viene alle 8 resta **a voce**; in tabella si registrano i codici.
- **AR/GP** di domenica è ammessa (non è «giro reparto»).

**Generazione automatica (opt-in):** in Impostazioni si può attivare *«Smezza guardie del martedì con la
reumatologa»* (`DB.req.smezzaGuardie`, default **off**). Quando attiva, la bozza converte la guardia
diurna del **martedì** (giorno dell'amb. reumato di mattina) in **GM** (a un medico) + **AR/GP** (alla
reumatologa, preferendo chi già fa l'amb. reumato quel giorno, poi Marotta). La copertura resta invariata
(0,5 + 0,5 = 1 guardia). Senza il flag il comportamento è quello standard (guardia intera).

---

## 5. Ambulatori

Assegnazione automatica in bozza (converte una **M** nel codice ambulatorio).  
Solo medici con **competenza** abilitata (AI / AD / AR in Organico).

| Giorno | Orario | Ambulatorio | Codice bozza | Note |
|--------|--------|-------------|--------------|------|
| **Lunedì** | Pomeriggio | Medicina interna | **M/AI** | Di solito Campagnol, Virdis, Verardo; a volte Lovero |
| **Martedì** | Mattina | Reumatologico | **M/AR** | |
| **Mercoledì** | Pomeriggio | Doppler | **M/AD** | Soprattutto Campagnol; 1–2 anche Lovero |
| **Giovedì** | Pomeriggio | Reumatologico | **M/AR** o **AR** | |
| **1° giovedì del mese** | Pomeriggio | Reumatologico (capillaroscopie) | **AR** alla **Marotta** | Se Marotta ha competenza AR ed è in reparto |

**Regola organizzativa (non automatizzata):** chiedere a Marotta quanti ambulatori servono nel mese; nei giorni in cui si è in 5 si aggiunge seduta ambulatorio.

L'ambulatorio va preferibilmente a chi è **più indietro sul monteore** (deficit ore).

---

## 6. Rotazione weekend

I weekend si pianificano **per bimestre** (gen–feb, mar–apr, mag–giu, lug–ago, set–ott, nov–dic) ma il criterio **non** è «8 fissi per calendario»: dipende dai **medici in rotazione**.

### Medici in rotazione

Entrano se:

- Attivi, **non Dec. Calabria**, **può weekend**
- **Non** assenti tutto il bimestre per **MAL** o **C** (es. maternità/congedo lungo — fuori rotazione finché dura)

Ordine rotazione (da calendari Excel):  
Campagnol → Piccoli → Verardo → Della Libera → Lovero → Marotta → Virdis → Brondolin → Teso.

### Blocchi consecutivi

- **N weekend = N medici** in rotazione (es. 7 medici → 7 weekend; 8 medici → 8 weekend).
- I blocchi sono **sabato consecutivi senza buchi** (finisce 25–26 apr → inizia 2–3 mag → … → 20–21 giu → 27–28 giu → …).
- Il blocco successivo **si incatena** al precedente (non «ultimo WE del mese prima» come regola fissa, ma effetto della catena).
- Blocchi esemplificativi memorizzati:
  - **14 mar 2026** — 7 WE, 7 medici (Mar–Apr, senza Teso in maternità)
  - **2 mag 2026** — 8 WE, 8 medici (Mag–Giu, Teso rientrata)
  - **27 giu 2026** — 8 WE, 8 medici (Lug–Ago)

### Schema rotazione standard (↻ Proponi rotazione)

Ogni weekend, tra i N medici:

| Ruolo | Codice WE | Effetto in griglia |
|-------|-----------|-------------------|
| Venerdì notte | **VN** | N venerdì + SN sabato |
| Sabato notte | **SN** | N sabato + SN domenica |
| Sabato giorno | **SG** | G sabato |
| Sab matt + dom notte | **MN** | M sabato, N domenica, SN lunedì |
| Sab matt + dom giorno | **MG** | M sabato, G domenica |
| Libero | **/** | Nessuna scrittura |
| Libero tassativo | **//** | Nessuna scrittura |
| Ferie | **F** | F sabato e domenica (se ferie in assenze) |

In **N settimane** ogni medico fa **esattamente i 5 turni** (VN, SN, SG, MN, MG); gli altri sono `/`.

### Gestione ferie (ferie-aware)

Se un medico è in **ferie (F)** nel weekend in cui gli toccherebbe un turno lavorativo (VN/SN/SG/MN/MG),
quel turno **non viene perso**: viene **ricoperto automaticamente** da un medico libero quel weekend,
scelto tra i **meno caricati** del bimestre (equità). Così ogni weekend mantiene sempre i 5 ruoli
coperti. Se le ferie superano i medici disponibili (meno di 5 liberi), i turni non copribili sono
**segnalati** ("⚠ turni scoperti") per intervento manuale. Senza ferie il risultato è **identico**
alla rotazione standard. (Convalidato sui calendari reali gen–lug 2026: 0 buchi di copertura.)

L'**offset** di settimana si calcola da:

1. Allineamento al **weekend precedente** (se già compilato), oppure
2. Blocco **esemplificativo** se coincide, oppure
3. Catena dall'ancora **14 mar 2026**.

Malattia/congresso su tutto il bimestre **invalida** i periodi weekend salvati (ricalcolo blocchi).

---

## 7. Vincoli per medico (Organico)

| Flag | Effetto sulla bozza |
|------|---------------------|
| **Attivo** | Partecipa ai turni |
| **No notte** (`puoNotte: false`) | Non riceve N in bozza; avviso se assegnato a mano |
| **No weekend** (`puoWeekend: false`) | Sab/dom → `/` automatico in bozza |
| **Dec. Calabria** | 32 h/sett., **5 giorni** (lun–ven); **no** N, G, GM, GP, weekend in bozza; competenze ambulatorio sì |
| **Competenze AI/AD/AR** | Obbligatorie per ambulatori corrispondenti |

**Decreto Calabria:** specializzando con orario ridotto; in bozza solo turni **lun–ven**, mai guardie/notti/weekend.

---

## 8. Assenze e desiderate

| Tipo | Comportamento in bozza |
|------|------------------------|
| **Ferie (F)** | Scritte in griglia prima della bozza; bloccano la cella |
| **Permesso (P)** | Idem |
| **Malattia (MAL)** | Idem; se tutto il bimestre → fuori rotazione WE |
| **Congresso (C)** | Idem |
| **Desiderata (DES)** | **Preferenza**, non scrive codice; bozza **cerca** di lasciare libero; se serve per copertura minima può comunque assegnare |

Weekend: se ferie sab/dom → codice **F** nella proposta rotazione.

---

## 9. Monteore e settimana tipo

### Obiettivo settimanale (regola operativa)

Ogni medico, in media, fa circa **1 notte + 1 guardia diurna a settimana** (oltre alle mattine reparto).

### Calcolo ore

- **Ore dovute mese** = `(oreSett ÷ giorniLavSett) × giorniDovutiMese`
  - Standard: **38 h ÷ 6** × giorni lun–sab non festivi
  - Dec. Calabria: **32 h ÷ 5** × stessi giorni
- **Domeniche ed festivi** non contano nei «giorni dovuti».
- Ferie / malattia / congresso: **6,33 h** ciascuno.
- Recuperi R/RF/RN: **0 h**.

### Bilanciamento bozza

La bozza ordina i candidati per **deficit monteore** (chi ha lavorato meno ore rispetto al dovuto viene scelto prima), per evitare disparità tra prime/ultime righe organico.

### Visualizzazione calendario (regola Excel)

- Griglia per **settimane complete lun–dom**; se il mese non inizia/finisce di lunedì, si mostrano giorni del mese precedente/successivo (grigio, *fuori mese*).
- **Conteggio ufficiale ore:** solo giorni del **mese corrente**.
- **Mese arricchito:** conteggio trasparente che include i giorni fuori mese visibili nelle settimane estese.

---

## 10. Cosa fa e cosa non fa `generaBozza`

### Rispetta (senza sovrascrivere celle piene)

- Weekend già applicati
- Assenze (F/P/MAL/C)
- Vincoli no-notte / no-weekend / Dec. Calabria
- Desiderate (come preferenza)
- Festivi e recuperi
- Regole guardia lun/ven/mar
- Max 12 giorni consecutivi
- Copertura minima/ideale (con eccezione domenica)
- Ambulatori per giorno settimana
- Bilanciamento monteore

### Non fa (richiede intervento manuale)

- Sedute ambulatorio extra quando si è in 5 (da concordare con Marotta)
- Eccezioni straordinarie (guardia mar post-domenica)
- Decisione definitiva sui blocchi weekend se non si usa *Proponi rotazione* o compilazione manuale

### Funzioni correlate (fuori dal motore bozza)

- **Smezzare guardie GM + AR/GP**: ora generabili in automatico col flag opt-in (vedi §4).
- **Scambi tra colleghi**: gestiti dalla scheda *Scambi turni* (richiesta → approvazione turnista/primario → applicazione automatica, tracciata nello storico).
- **Equità annuale & registro recuperi**: scheda *Equità & Recuperi* (cumulato annuo notti/guardie/weekend/festivi; recuperi maturati vs goduti).
- **Annulla bozza** e **Export .ics**: ripristino della griglia pre-bozza ed esportazione calendario.

---

## 11. Controlli e avvisi (`Controllo regole`)

| Severità | Esempi |
|----------|--------|
| **err** (blocco) | Manca N o G; reparto sotto minimo; presenti < 6; giro reparto di domenica; > 12 giorni consecutivi |
| **warn** | Guardia mar post-domenica+riposo lun; troppe notti; manca smonto |
| **info** | Presenti sotto ideale 7 (non domenica) |

---

## 12. Riferimenti nel codice

| Area | Funzione / sezione |
|------|-------------------|
| Bozza automatica | `generaBozza()` |
| Copertura | `contaGiorno()` / `contaGiornoRef()` |
| Avvisi | `collectAlerts()` |
| Rotazione WE | `proponiRotazioneWeekend()`, `weekendsInPeriodo()` |
| Applicazione WE → griglia | `applicaWeekendForMonth()`, `WE_MAP` |
| Ambulatori | blocco `assign()` in `generaBozza` |
| Recuperi | `assignRec()`, earnedFest / earnedNight |
| Monteore | `oreDovuteMese()`, `oreLavorateMese()` |

---

## 13. Promemoria testuale (note reparto)

Testo predefinito in Impostazioni → *Note / regole*:

```
REGOLE PROMEMORIA:
- Domenica: solo medico di guardia (N/G); nessun giro in reparto; minimo 6 e ideale 7 non valgono.
- Lunedì: recupero a chi fa guardia domenica; guardia a chi ha weekend libero.
- Venerdì: guardia a chi ha sabato notte o weekend libero.
- Evitare guardia il martedì dopo riposo del lunedì (di chi ha fatto guardia domenica).
- Recupero per festivi, mezzi festivi, notti di sab/dom e notti su festivo.
- Max 12 giorni lavorativi consecutivi (meglio meno).

AMBULATORI:
- Lun pom: amb. medicina interna
- Mar mattina: amb. reumato
- Mer pom: amb. doppler
- Gio pom: amb. reumato (1° giovedì del mese alla Marotta per capillaroscopie)
```

---

*Ultimo aggiornamento: giugno 2026 — allineato a `index.html` e regole reparto Medicina Interna.*
