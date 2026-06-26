# Prompt per Cursor — Restyling app Turni (sidebar + tema caldo)

Lavori sul file **`index.html`** (singolo file: CSS in `<style>`, JS inline, nessun build). Fai un
**restyling completo** dell'interfaccia desktop **senza cambiare la logica**.

---

## Obiettivo

1. **Sostituire la navigazione a tab orizzontali** (`.tabs` / `.tab` in alto) con una **sidebar
   verticale a sinistra**, ispirata al riferimento qui sotto.
2. Passare dall'attuale tema **blu/grigio** a una **palette calda, chiara e ad alto contrasto**
   (espresso + crema/bianco + bordeaux).
3. Restyling coerente di **card, pulsanti, tab/segmenti, chip, tabelle, input, badge, top bar**.

## Riferimento (stile sidebar da imitare)

Pannello scuro arrotondato a tutta altezza con:
- **Header**: titolo app in due righe — eyebrow piccolo maiuscolo (es. «TURNI REPARTO») + titolo
  in grassetto (es. «Medicina Interna»), con icona di collasso a destra.
- **Voci di navigazione**: ognuna = **icona** + **titolo** (grassetto) + **sottotitolo** piccolo
  attenuato su due righe. Stato **attivo** evidenziato (sfondo più chiaro/tinta bordeaux + barra/accento).
- **Card utente in basso**: avatar con iniziali + nome + ruolo (es. «Alberto · Amministrazione»).

---

## VINCOLI TASSATIVI (non rompere la logica)

- **Mantieni tutti gli `id` esistenti** e gli attributi **`data-view`**. Il JS fa
  `document.querySelectorAll(".tab")` e mostra la sezione `#view-<data-view>`: le voci della
  sidebar **devono conservare `class="tab"` e `data-view="…"`** (oppure aggiorna di conseguenza
  sia il selettore in `setupEventi()` sia `openDesktopView()`), così lo switch continua a funzionare.
- Non toccare nomi di funzioni, handler, `id` di pulsanti (`btnWizard`, `btnAutofill`,
  `btnUndoBozza`, `btnExcel`, `btnIcs`, `btnStampa`, `btnExport`, `btnImport`, `btnTheme`, ecc.)
  né la struttura delle sezioni `#view-…`.
- **Resta un singolo file**, senza dipendenze/build. Niente nuove librerie (icone: usa SVG inline o
  i caratteri/emoji già presenti).
- **Conserva il toggle tema chiaro/scuro** (`btnTheme`, `initTheme`, `.app.dark`): ridefinisci le
  variabili sia per il tema chiaro sia per quello scuro, in versione calda.
- **Mobile invariato nella sostanza**: sotto ~860px la sidebar diventa un drawer a scomparsa (o si
  nasconde) e resta attiva la navigazione mobile esistente (bottom-nav / «Menu reparto»). Non
  rompere `renderMobile*` né i link `.mob-desk-link[data-view]`.

## Voci sidebar (mappa da `data-view` → icona + sottotitolo)

| data-view | Titolo | Sottotitolo | Icona (SVG inline) |
|-----------|--------|-------------|--------------------|
| `turni` | Turni del mese | Griglia del mese | calendario/griglia |
| `organico` | Organico | Medici e competenze | persone |
| `assenze` | Desiderate & Assenze | Ferie, permessi, preferenze | cuore/spunta |
| `weekend` | Weekend bimestre | Rotazione weekend | luna/calendario |
| `riepilogo` | Riepilogo & Monteore | Copertura e ore | grafico a barre |
| `equita` | Equità & Recuperi | Cumulato annuo e recuperi | bilancia |
| `scambi` | Scambi turni | Richieste e approvazioni | frecce ⇄ |
| `storico` | Storico modifiche | Chi ha cambiato cosa | orologio/cronologia |
| `impostazioni` | Impostazioni | Regole, copertura, tema | ingranaggio |

I **selettori mese/anno** e le **azioni** (Wizard bozza, Genera bozza, Annulla bozza, Esporta Excel,
Esporta .ics, Stampa, Esporta/Importa dati, tema) **restano una toolbar in alto** nell'area
contenuti (NON nella sidebar): la sidebar è solo navigazione tra sezioni.

---

## Palette calda (ridefinisci le variabili in `:root`/`.app` e `.app.dark`)

**Tema chiaro (default) — più chiaro e contrastato del riferimento:**
```
--bg:        #f7f2ea;   /* sfondo contenuti, crema chiara */
--panel:     #ffffff;   /* card */
--panel2:    #f3ece1;   /* superfici secondarie / intestazioni tabella */
--border:    #e7ddcd;   /* bordi */
--border2:   #f0e8db;
--ink:       #2a211c;   /* testo principale, espresso quasi nero */
--ink2:      #7c6f63;   /* testo attenuato */
--ink3:      #a89a8b;   /* testo molto attenuato / label */
--accent:    #8a2f2f;   /* bordeaux primario */
--accent-soft:#f3e3e0;  /* sfondo tenue dell'accento */
--hover:     #f1e9dd;
--ok:        #2f8a4e;   /* successo */
--warn:      #c8881f;   /* oro/avviso */
--err:       #c0392b;   /* errore/destructive */
/* Sidebar (scura in entrambi i temi) */
--side-bg:   #2b211b;   /* espresso */
--side-bg2:  #352a22;   /* voce attiva / hover */
--side-ink:  #f4ece1;   /* testo sidebar */
--side-ink2: #b6a596;   /* sottotitoli sidebar */
--side-active:#8a2f2f;  /* accento voce attiva */
```

**Tema scuro (`.app.dark`) — caldo, non blu:**
```
--bg:#181311; --panel:#221b17; --panel2:#1d1714; --border:#34291f; --border2:#2a211b;
--ink:#f0e7da; --ink2:#b7a899; --ink3:#7c6e60; --accent:#c96a5f; --accent-soft:#3a221f;
--hover:#241c17; --ok:#5cc06d; --warn:#e0b15a; --err:#e08074;
--side-bg:#160f0c; --side-bg2:#241a14; --side-ink:#f0e7da; --side-ink2:#9b8a7b; --side-active:#c96a5f;
```

Obiettivo percezione: **più aria, più bianco nelle card, contrasto testo alto**, accenti decisi.
Aggiorna eventuali colori hardcoded che stonano (azzurri/blu residui) usando le variabili.

---

## Gerarchia componenti (rendi i pulsanti leggibili e non tutti uguali)

Oggi ci sono troppe «pill» indistinguibili. Definisci ruoli chiari:

- **`.btn.primary`** — azione principale: pieno **bordeaux** (`--accent`), testo bianco.
- **`.btn`** (secondario) — sfondo `--panel`, bordo `--border`, testo `--ink`; hover `--hover`.
- **`.btn.ghost`** — solo testo `--ink2`, nessun bordo; hover tenue.
- **`.btn.danger`** — bordo/testo `--err`, pieno su hover (per azioni distruttive).
- **`.btn.small`** — variante compatta (già usata negli scambi).
- **Segmenti/tab interni** (es. *Tabella/Catalogo*, *In revisione/Pubblicati/…*, *Elenco corsi/Categorie*):
  trasformali in un **segmented control** unico (gruppo con sfondo `--panel2`, pillola attiva piena),
  visivamente **diverso** dai pulsanti-azione.
- **Chip conteggio** (es. «0 nel tab», «0 visibili»): piccoli, sfondo `--panel2`, numero in `--ink`,
  etichetta in `--ink3`. Non sembrino pulsanti cliccabili.
- **Badge** (DEV, Bozze, ADMIN, notifiche): pill piene a colore semantico (oro `--warn`, rosso `--err`,
  bordeaux), testo ad alto contrasto.

## Card, tabelle, input, top bar

- **Card** (`.card`, `.panel`): sfondo `--panel`, bordo `--border`, **raggio 14–16px**, **ombra
  morbida** (`0 1px 2px rgba(0,0,0,.04), 0 8px 24px -16px rgba(0,0,0,.12)`), padding generoso (20–24px).
- **Tabelle** (`.grid-wrap table`, ecc.): intestazioni `--panel2`, righe con hover `--hover`,
  bordi `--border2`, prima colonna sticky mantenuta. Migliora leggibilità (line-height, padding 11–14px).
- **Input/select** (`.sel`, `input`, `textarea`): raggio 10px, bordo `--border`, focus con
  `border-color:var(--accent)` + lieve ring (`box-shadow:0 0 0 3px var(--accent-soft)`).
- **Top bar**: barra contenuti con titolo sezione a sinistra e toolbar azioni a destra; sobria,
  sfondo `--panel`/`--bg`, bordo inferiore `--border`. (La barra scura del brand può restare in cima
  o essere assorbita dalla sidebar — scegli la soluzione più pulita mantenendo gli `id`.)
- **Tipografia**: mantieni il font **Geist** già caricato; scala coerente (titoli sezione ~18–20px/700,
  testo 13.5–14px, label 11px maiuscolo `--ink3`). Aumenta leggermente gli spazi verticali tra blocchi.

## Layout

- Griglia a due colonne: **sidebar fissa** (larghezza ~248px, `position:sticky`/`fixed`, scroll interno)
  + **area contenuti** che scorre. Su mobile la sidebar collassa (drawer) e riappare la nav mobile.
- Larghezza massima leggibile per i contenuti testuali; le tabelle restano a piena larghezza con scroll.

---

## Checklist di accettazione

- [ ] Cliccando ogni voce della sidebar si apre la sezione giusta (lo switch `data-view` → `#view-…` funziona).
- [ ] Tutti gli `id` e gli handler esistenti sono intatti; nessun errore in console.
- [ ] Tema chiaro **e** scuro funzionano, entrambi in versione calda; il toggle `btnTheme` opera.
- [ ] Le azioni in toolbar (Wizard, Genera/Annulla bozza, Esporta Excel/.ics, Stampa, Esporta/Importa) restano accessibili e funzionanti.
- [ ] Mobile: la navigazione esistente continua a funzionare; la sidebar diventa drawer/nascosta sotto ~860px.
- [ ] Pulsanti con gerarchia chiara (primario/secondario/ghost/danger); segmenti e chip distinti dai pulsanti-azione.
- [ ] Nessun colore blu/azzurro residuo: tutto coerente con la palette calda.
- [ ] Stampa (`.noprint`, `print-active`) ancora corretta.

> Procedi modificando **solo** `<style>` e il markup di navigazione/struttura necessario, conservando
> contenuti e logica. Se rinomini classi di navigazione, aggiorna in parallelo `setupEventi()` e
> `openDesktopView()` perché lo switch delle viste resti funzionante.
