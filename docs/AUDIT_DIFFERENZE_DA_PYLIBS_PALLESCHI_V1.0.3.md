# Audit delle differenze rispetto a pyLIBS ufficiale di Palleschi

Data dell'audit: 25 settembre 2026

## Riferimento usato

Il confronto e' stato eseguito contro il repository pubblico `Vince1960/pyLIBS`,
tag `v1.0.3`, commit `cd781f3a09e9b93eb5deac9eb217bc1075b66b2a`.

Questo dettaglio e' importante: per "procedura ufficiale" in questo documento si
intende il programma Python pubblicato su GitHub a quel tag, non una ricostruzione
a memoria, non il vecchio programma locale LIBS+ e non direttamente i sorgenti
storici Borland di LIBS++.

File confrontati:

- ufficiale: checkout pulito del tag GitHub `v1.0.3`
- versione corrente: radice della presente distribuzione

Il solo `pyLIBS.py` passa da 9.294 a 20.680 righe. Le definizioni top-level
passano da 186 a 289: 104 sono state aggiunte, 55 definizioni preesistenti sono
state modificate e la classe `ResponseCurve` e' stata spostata in un modulo
dedicato. Il confronto seguente separa le modifiche matematiche dalle estensioni
operative e dalle parti rimaste uguali.

## 1. Modifiche dirette alla catena quantitativa

### 1.1 Ordinata del diagramma di Boltzmann

Ufficiale v1.0.3:

```text
x = Ek[cm^-1] * 1.23985e-4
Icorr = I / risposta_strumentale(lambda_centro_osservato)
y = ln(Icorr / abs(Aki * gk))
```

Versione corrente:

```text
x = Ek[cm^-1] * 1.23985e-4
Icorr = I / risposta_strumentale(lambda_NIST)
y = ln(5.0341166e15 * Icorr * lambda_NIST_nm / abs(Aki * gk))
```

Questa e' una modifica matematica sostanziale. Introduce la conversione da
energia radiometrica a numero di fotoni e il fattore `lambda`. Non e' la stessa
ordinata del tag ufficiale. Cambia certamente l'intercetta e puo' cambiare anche
la pendenza quando le righe coprono un intervallo spettrale ampio.

### 1.2 Lunghezza d'onda usata nella quantificazione

- Ufficiale: per la risposta e per il punto veniva usato il centro osservato/
  fittato della riga.
- Corrente: il centro osservato serve a localizzare e fittare il picco; per la
  risposta strumentale e per l'ordinata Boltzmann viene usata la lunghezza d'onda
  tabulata assegnata, cioe' la lunghezza d'onda NIST.
- Sono scartate le righe che cadono fuori dagli intervalli realmente acquisiti o
  nei vuoti tra finestre.

### 1.3 Intensita' ammessa nel Boltzmann/Saha-Boltzmann

- Ufficiale: usa `inte` se positiva, altrimenti puo' ripiegare su `templint`, che
  puo' essere l'altezza/marcatura del picco.
- Corrente: accetta esclusivamente l'area di un profilo realmente fittato con
  centro e larghezze validi. Non usa piu' l'altezza del picco come sostituto
  dell'area.
- La versione corrente ammette aree da profilo Voigt e anche dal Gaussian fit
  esplicito; il percorso guidato predefinito resta Voigt.

### 1.4 Soglia Aki

- Ufficiale: valore predefinito `0`, quindi nessun taglio Aki.
- Corrente: valore predefinito e attualmente configurato `1.0e5 s^-1`.
- Le righe sotto soglia vengono escluse da Boltzmann, Saha-Boltzmann e spettro
  teorico. Questo puo' ridurre il numero di punti rispetto all'ufficiale.

### 1.5 Database atomico

- Ufficiale: database storico `LIBS.db` e metadati secondo il suo schema.
- Corrente: database selezionabile; la configurazione attiva usa
  `LIBS_NIST_5_12.db`, costruito per uso offline da dati NIST.
- Sono stati aggiunti controllo dello schema e dei metadati, riconoscimento delle
  unita' di lunghezza d'onda e normalizzazione di `Aki` dai valori legacy in
  unita' `10^8 s^-1` ai valori fisici in `s^-1`.
- La ricerca rispetta esplicitamente elemento e stadio di ionizzazione; non deve
  ripiegare su una riga dello stadio sbagliato quando lo stadio e' specificato.
- La funzione di partizione puo' essere calcolata direttamente dalla tabella dei
  livelli NIST, `Z(T) = sum_i g_i exp(-E_i/kT)`, invece di dipendere soltanto
  dall'interpolazione della tabella storica `partfunctPay`.

Quindi, anche lasciando invariate le equazioni finali, database, Aki e funzioni
di partizione possono produrre numeri diversi dall'ufficiale.

### 1.6 Fit dei picchi e area

La v1.0.3 contiene gia' sia il multi-Gaussian storico sia un multi-Voigt. Il
Voigt ufficiale e' normalizzato ad area:

```text
y = baseline + slope*x + sum(area_i * Voigt_unitario_i)
```

Nella versione corrente il significato dell'area Voigt e' rimasto quello
dell'integrale analitico completo del profilo, ma e' cambiata la procedura che
stima i parametri:

- ricerca del massimo misurato attorno alla lunghezza NIST;
- limiti sul centro del picco;
- inizializzazioni multiple e scelta della soluzione stabile;
- fit simultaneo dei doppietti/multipli esplicitamente selezionati;
- nessun vicino nascosto aggiunto automaticamente al fit quantitativo;
- ROI manuali salvate per singola riga o gruppo;
- espansione automatica della ROI finche' entrambi i lati tornano alla baseline;
- controllo di punti disponibili, area, FWHM, centro, S/N e qualita' del residuo;
- supporto a fit separati delle repliche e CV dell'area;
- supporto alle finestre detector indipendenti.

La baseline predefinita resta lineare locale. La forma corrente
`b + s*(x-x_centro)` e' matematicamente equivalente alla forma ufficiale
`b + s*x`, ma meglio condizionata numericamente. Sono state aggiunte anche:

- `origin_constant`, baseline costante;
- `libs_auto`, integrazione fino al ritorno alla baseline;
- confronto BIC fra baseline costante e lineare, solo diagnostico.

Queste opzioni e la selezione della ROI possono cambiare parecchio l'area anche
se il segnale grezzo e' identico. L'algoritmo IRSAC corrente non rilancia il fit
dei picchi quando si preme Apply: usa le aree gia' memorizzate. Esiste ancora una
funzione interna `refit_irsac_voigt_areas`, ma nel flusso attuale non e' chiamata.

### 1.7 Gaussian fit

- Il modello Gaussian ufficiale `A*exp(-((x-x0)/sigma)^2)` e' disponibile anche
  nella versione corrente.
- L'area salvata e' `A*sigma*sqrt(pi)`.
- E' stato aggiunto al gestore di fit manuale con ROI, controlli e risultati
  persistenti. Questa e' un'estensione dell'interfaccia, non una nuova formula.

### 1.8 Unione delle finestre

- Ufficiale: nell'intervallo sovrapposto interpola entrambe le finestre e ne fa
  la media aritmetica punto per punto.
- Corrente: usa un cross-fade lineare, dando progressivamente meno peso alla
  prima finestra e piu' peso alla seconda lungo la sovrapposizione.
- E' stata aggiunta la modalita' `Independent windows`: nessuna interpolazione,
  media o cross-fade; ogni riga viene fittata nella finestra sorgente scelta.
- Nelle zone sovrapposte la finestra attiva puo' avere priorita'.

Cross-fade e media ufficiale non sono equivalenti e possono cambiare intensita'
e forma dei picchi nelle giunzioni.

### 1.9 Funzione strumentale

- Ufficiale: una sola curva di risposta; correzione tramite divisione; esempio
  configurato per applicazione dopo il caricamento/merging.
- Corrente: libreria di piu' curve, abbinate una a una alle finestre per nome e
  intervallo; correzione tramite divisione prima del merging per impostazione
  corrente.
- Viene selezionato il blocco contiguo positivo e affidabile della curva; le code
  sotto il 5% del 95-esimo percentile vengono eliminate e una copertura
  insufficiente viene rifiutata.
- Sono memorizzati provenienza e stato della correzione per evitare una doppia
  divisione.
- Sono supportate larghezze strumentali per finestra, oltre al valore globale.

La divisione e' la stessa operazione fisica richiesta dall'utente, ma gestione,
ordine di applicazione, matching e taglio dei bordi sono diversi dall'ufficiale.

### 1.10 Dark e lettura degli spettri

Funzioni assenti dalla catena ufficiale e aggiunte:

- dark da colonne della stessa acquisizione;
- dark da file separato;
- dark costante;
- riconoscimento di file ASCII multicolonna e della colonna spettrale;
- separatori decimali con virgola;
- tracciamento del dark gia' applicato per evitare doppie sottrazioni.

La configurazione attiva usa `dark_mode=constant` e `dark_constant=525.0`.
Questo e' un cambiamento numerico a monte di tutte le aree.

### 1.11 Calibrazione in lunghezza d'onda

L'ufficiale dispone di shift/offset manuali generali. La versione corrente
aggiunge una calibrazione persistente per ciascuna finestra:

- ricerca del massimo vicino alle righe NIST selezionate;
- raffinamento del centro con profilo Voigt;
- con una o due ancore viene usato un offset;
- con almeno tre ancore coerenti e distribuite si puo' usare una relazione
  lineare `lambda_cal = a + b*lambda_raw`;
- RMS, residui e righe usate sono mostrati e salvati.

La calibrazione corrente e' applicata automaticamente (`auto=1`) e quindi puo'
cambiare quali campioni entrano nella ROI e il centro fittato, pur mantenendo la
lambda NIST nell'ordinata Boltzmann.

### 1.12 Temperatura Saha-Boltzmann

Sono rimaste le coordinate energetiche e la regressione lineare di base del
programma ufficiale, ma sono cambiati selezione e uso del risultato:

- solo gli elementi esplicitamente selezionati in Trace Lines entrano
  nell'analisi quantitativa;
- sono escluse righe fuori dalle finestre acquisite;
- prima di IRSAC ogni elemento conserva la propria pendenza libera;
- la specie termometrica puo' essere scelta manualmente;
- la scelta automatica privilegia affidabilita', numero di livelli e soprattutto
  ampiezza `Delta Ek`, con controlli R2 e leave-one-out;
- dopo IRSAC la temperatura della specie termometrica viene fissata e le altre
  specie sono rifittate con pendenza comune `-1/kT` per la concentrazione;
- sono state aggiunte diagnostica riga per riga e una finestra Check Lines.

La v1.0.3 aveva gia' funzioni di fit libero e di refit a temperatura fissata; la
modifica sta soprattutto nel criterio esplicito di scelta, nei filtri e nel
workflow obbligato fra le due fasi.

### 1.13 Densita' elettronica da H-alpha

La relazione numerica di Palleschi e' conservata:

```text
w_corr = w_L - w_inst^2 / w_L
Ne = 8.02e12 * (w_corr / alpha(T))^1.5
```

Il fit utente resta quello ufficiale a una o due Lorentziane. Sono state aggiunte:

- conversione esplicita nm/angstrom prima della formula;
- ricerca del vero massimo vicino a H-alpha, tenendo conto dello shift;
- controlli di ambiguita', S/N e R2;
- incertezza della larghezza dalla covarianza e propagazione a Ne;
- caricamento dedicato della sola finestra H-alpha senza risposta radiometrica,
  ma con dark e calibrazione di lambda;
- associazione di Ne alla sessione/provenienza, invece di usare un valore
  implicito o casuale;
- ricalcolo di Ne quando cambia la temperatura usata da `alpha(T)`.

Esiste un metodo Voigt interno di compatibilita', ma il pulsante esposto nella
finestra Ne usa il percorso Lorentziano Palleschi.

### 1.14 Correzione dell'autoassorbimento

La procedura ufficiale v1.0.3 usa il metodo Palleschi/Stark:

```text
w_Stark(T,Ne) = 2 * (Ne/1e17) * interpolazione(w5000,w10000,T)
SA = (w_L_osservata / w_Stark)^(-1.85)  se il rapporto >= 1, altrimenti 1
SAC = SA^(-0.46)
I_corretto = I * SAC
```

Questo percorso e' ancora presente. Sono pero' stati aggiunti metodi non presenti
nella v1.0.3:

- IRSAC Yang/Aslam basato su rapporti di intensita' rispetto a una riga interna;
- IRSAC iterativo;
- workflow Aslam a stadi, attualmente predefinito;
- modalita' ibrida che usa Palleschi/Stark dove disponibili i dati Stark e IRSAC
  negli altri casi;
- scelta manuale della specie termometrica e delle righe di riferimento;
- riferimenti automatici per specie;
- correzione selettiva riga per riga;
- controlli indipendenti che distinguono una correzione consigliata da un
  semplice fattore numerico disponibile;
- possibilita' di visualizzare una correzione non consigliata, con conferma
  esplicita, senza confonderla con prova di autoassorbimento;
- blocco delle incoerenze fra configurazione IRSAC corrente e risultato salvato.

Nel workflow `staged` corrente:

1. si stima la T grezza della specie termometrica;
2. si correggono con IRSAC le sue righe;
3. si ricalcola e si fissa la T corretta della specie termometrica;
4. si calcolano le correzioni delle altre specie a quella T fissata;
5. la CF-LIBS finale usa la pendenza comune corrispondente a quella T.

Questa e' la maggiore estensione scientifica rispetto alla procedura ufficiale.

### 1.15 Concentrazioni CF-LIBS e ionizzazione

Le formule finali principali sono rimaste quelle della v1.0.3:

```text
N_I  = exp(q_I)  * Z_I(T)
N_II = exp(q_II) * Z_II(T)
N_tot(elemento) = N_I + N_II
number_% = N_tot / sum(N_tot) * 100
mass_% = M_atomica * N_tot / sum(M_atomica * N_tot) * 100
```

Se manca uno stadio, il rapporto e' completato con la stessa forma Saha-Eggert:

```text
N_II/N_I = (6.04e21/Ne) * (kT)^1.5 * (Z_II/Z_I) * exp(-Eion/kT)
```

Differenze operative correnti:

- modalita' di default `Saha-Eggert (database)`;
- esiste anche una modalita' manuale di frazione neutra, assente dall'ufficiale,
  ma non e' quella configurata;
- la quantificazione finale usa per default intercette a T comune fissata;
- il fit con pendenze libere resta disponibile come diagnostica, non come
  procedura quantitativa finale;
- sono aggiunti audit delle righe, sensibilita' leave-one-out, robustezza alle
  repliche, sensibilita' a T/Ne, interferenze e criteri McWhirter;
- il quality gate mostra sempre le percentuali calcolate ma le marca PASS/CHECK;
  puo' impedire di trattare un risultato instabile come calibrazione OPC.

La formula massa/numero non e' stata inventata nella versione corrente: entrambe
erano gia' presenti nella v1.0.3. Le differenze nelle percentuali derivano dagli
ingressi a monte (`I`, lambda, risposta, database, T, Ne, IRSAC, righe ammesse e
intercette), non dalla moltiplicazione finale per la massa atomica.

### 1.16 One Point Calibration e Standard Correction

- `CFLibsOPCWindow._calibration_rows` e' stato ripristinato con lo stesso corpo
  logico/AST del tag ufficiale v1.0.3.
- Il fattore elementare resta `percentuale_nominale / percentuale_CF-LIBS`.
- La risposta OPC per riga resta
  `Iraw / (SAC * Aki * gk * exp(y_previsto))`.
- Anche la finestra Standard Correction conserva il calcolo ufficiale.

Attenzione: la formula OPC e' identica, ma riceve aree, punti Boltzmann, T, Ne e
percentuali prodotti dalla catena corrente; quindi il risultato complessivo puo'
comunque differire dal tag ufficiale. Il changelog contiene ancora una frase
storica che include OPC fra i percorsi radiometrici uniformati: dopo il ripristino
dell'OPC quella frase non e' piu' completamente aggiornata.

### 1.17 Spettro teorico

Funzione interamente aggiunta:

- genera le intensita' delle righe del database dalle intercette e dalla T;
- usa profili Voigt;
- applica un'unica FWHM strumentale misurata su H-alpha a tutte le righe, oppure
  i dati per finestra quando disponibili;
- puo' sintetizzare nel dominio corretto per risposta o nel dominio detector;
- puo' riscalare il modello solo per confronto visivo;
- e' marcata come diagnostica successiva alla decisione sull'autoassorbimento e
  non sostituisce le concentrazioni CF-LIBS.

## 2. Selezione delle righe e gestione dei dati

Sono state aggiunte rispetto alla v1.0.3:

- libreria persistente di righe analitiche incorporata nel programma;
- importazione e fusione di listoni secondari;
- arricchimento delle righe con dati NIST;
- Trace Lines limitato agli elementi scelti;
- eliminazione di un elemento tracciato con Canc/Delete;
- persistenza della libreria dopo Clear Graph;
- esclusione automatica di righe fuori dal dominio acquisito;
- gestione esplicita di finestre sovrapposte e scelta della finestra sorgente;
- caricamento multiplo degli spettri;
- riconoscimento delle repliche per stimare la variabilita' delle aree;
- metadati di provenienza per spettro, risposta, dark e calibrazione.

Queste funzioni non cambiano da sole un'equazione, ma cambiano quali righe e quali
campioni arrivano alle equazioni.

## 3. Interfaccia, visualizzazione e report

Modifiche non direttamente matematiche:

- scaling DPI e resa meno sfocata su Windows;
- zoom centrato sul cursore e limiti di zoom migliorati;
- legenda delle finestre spostabile;
- grafici segmentati sui vuoti reali, senza linee artificiali fra finestre;
- tabella CF-LIBS scorrevole;
- aree mostrate in notazione scientifica;
- schermate dedicate a sorgenti, calibrazione di lambda, diagnostica delle righe
  e spettro teorico;
- finestre e impostazioni persistenti;
- ripristino delle impostazioni di fabbrica;
- help contestuale e manuali italiano/inglese;
- report estesi con provenienza di T, Ne, risposta, IRSAC e quality audit;
- numerosi test automatici e strumenti di verifica aggiunti al repository.

## 4. Moduli aggiunti integralmente

Questi moduli non esistono nel tag ufficiale v1.0.3:

- `pylibs/core/analysis_workflow.py`
- `pylibs/core/boltzmann.py`
- `pylibs/core/instrument_response.py`
- `pylibs/core/preprocessing.py`
- `pylibs/core/self_absorption.py`
- `pylibs/core/theoretical_spectrum.py`
- `pylibs/core/wavelength_calibration.py`

Sono inoltre nuovi il database NIST offline, la libreria persistente delle righe,
i manuali bilingui, gli strumenti di build/probe e la suite di test.

## 5. File ufficiali modificati

Oltre a `pyLIBS.py`, sono stati modificati:

- `pylibs/core/models.py`: profilo del fit e metadati aggiuntivi;
- `pylibs/db/libs_database.py`: metadati, unita', Aki, NIST e funzioni di
  partizione;
- `pylibs/gui/helpers.py`, `simple_dialogs.py`, `toolbar.py`: DPI, help e comandi;
- `pylibs/io/ini.py`: nuove sezioni e opzioni persistenti;
- `pylibs/io/report_io.py`: report scientifico e provenienza estesi;
- `pylibs/io/spectrum_io.py`: ASCII multicolonna, dark e parsing piu' robusto;
- `pylibs/utils/formatting.py`, `paths.py`: formattazione scientifica e risorse;
- `pyLIBS.ini.example`, README e documentazione.

## 6. Classi principali modificate

- `AppOptions`: molte nuove opzioni scientifiche e di persistenza.
- `Spectrum`: sorgenti, segmenti, risposta, calibrazione e metadati.
- `OptionsWindow`: database, dark, risposte multiple, baseline e workflow.
- `LineIdentificationWindow` e `AutoElementIdentificationWindow`: ricerca NIST,
  matching di ione e dominio acquisito.
- `TraceLinesWindow`: selezione esclusiva e rimozione elementi.
- `MultiGaussianFitWindow`: Gaussian e Voigt con gestione area/ROI estesa.
- `RetroFitManagerWindow`: fit manuale/automatico, multipicco, ROI e repliche.
- `NeHalphaWindow`: loader dedicato, identificazione picco, incertezza e sessione.
- `SahaBoltzmannWindow`: selezione termometrica, fit liberi e diagnostica.
- `SelfAbsorptionCheckWindow`: Palleschi/Stark piu' IRSAC e workflow a stadi.
- `CFLibsWindow`: T comune, filtri, robustezza e quality audit.
- `MainWindow`: finestre indipendenti, librerie, calibrazioni e nuovi strumenti.

Classi interamente nuove:

- `SpectrumSourceWindow`
- `WavelengthCalibrationWindow`
- `SahaLineDiagnosticsWindow`
- `TheoreticalSpectrumWindow`

## 7. Impostazioni attive che differiscono dai default ufficiali

Questa sezione descrive lo stato del file `pyLIBS.ini` corrente, non solo il
codice disponibile:

- database: `LIBS_NIST_5_12.db`;
- risposta: attiva, applicata prima, sei curve per finestra;
- dark: costante `525`;
- larghezza strumentale: `0.0255960032` nelle unita' correnti;
- baseline Voigt: `local_linear`;
- soglia Aki: `1.0e5 s^-1`;
- IRSAC: modalita' `irsac`, workflow `staged`, 100 iterazioni, tolleranza 0.001;
- specie termometrica IRSAC: `Cd I`;
- CF-LIBS: intercette a T fissata, ionizzazione Saha-Eggert;
- calibrazione automatica di lambda: attiva e salvata per sei finestre;
- `delta_min`: 0.5 invece di 8.0 nell'esempio ufficiale;
- intervalli T e Ne e numero di iterazioni diversi dai default ufficiali.

Queste impostazioni sono specifiche dell'ultima sessione e possono cambiare il
risultato anche senza ulteriori modifiche al sorgente.

## 8. Parti matematiche rimaste uguali

- conversione `Ek[cm^-1] -> eV`;
- regressione lineare di base e relazione `slope = -1/kT`;
- costruzione delle popolazioni da `exp(q)*Z(T)`;
- completamento dello stadio mancante con Saha-Eggert;
- normalizzazione della percentuale atomica;
- conversione a percentuale in massa con la massa atomica;
- relazione H-alpha di Palleschi esposta all'utente;
- metodo Palleschi/Stark per l'autoassorbimento, quando selezionato;
- Standard Correction;
- One Point Calibration, dopo l'ultimo ripristino.

## 9. Sintesi delle differenze che possono cambiare davvero i risultati

In ordine di impatto potenziale:

1. ordinata Boltzmann con `5.034e15 * lambda_NIST`;
2. aree ottenute dal nuovo fit/ROI/baseline e divieto del fallback all'altezza;
3. risposta strumentale multipla applicata prima del merging;
4. dark costante o da acquisizione;
5. database NIST, unita' Aki e funzioni di partizione;
6. calibrazione per finestra e scelta della sorgente nelle sovrapposizioni;
7. cross-fade del merging oppure analisi a finestre indipendenti;
8. soglia Aki e filtri sulle righe realmente acquisite/selezionate;
9. scelta della specie termometrica e refit finale a T comune;
10. IRSAC Yang/Aslam a stadi o ibrido;
11. uso e provenienza della Ne di sessione;
12. quality gate e diagnostiche, che non cambiano la formula ma cambiano la
    classificazione e l'uso successivo del risultato.

La versione corrente, quindi, non e' matematicamente identica alla v1.0.3 lungo
l'intera catena. Le formule finali Saha/percentuali, H-alpha Palleschi, Standard
Correction e OPC sono conservate; le maggiori deviazioni sono a monte:
pretrattamento, area, lambda nell'ordinata, database, selezione delle righe e
IRSAC.
