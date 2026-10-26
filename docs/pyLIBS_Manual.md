# pyLIBS - Manuale operativo completo

Versione del manuale: 1.2 - 29 settembre 2026  
Software: pyLIBS 1.2.0
Origine: LIBS++ di Vincenzo Palleschi e collaboratori

> Questo manuale descrive l'interfaccia e il flusso scientifico effettivamente implementati. I nomi dei comandi sono riportati come appaiono nel programma. Leggere almeno i capitoli 1-4 prima della prima analisi quantitativa.

## Indice operativo

1. Scopo e limiti del programma
2. Concetti indispensabili
3. Avvio rapido: una misura completa
4. Configurazione iniziale
5. Interfaccia principale
6. File spettrali e caricamento
7. Dark, fondo e funzione strumentale
8. Calibrazione in lunghezza d'onda
9. Listone e righe selezionate
10. Ricerca dei picchi e identificazione
11. Fit Voigt automatico e manuale
12. Densità elettronica da Hα
13. Temperatura Saha-Boltzmann
14. Autoassorbimento e IRSAC
15. Concentrazioni CF-LIBS
16. Spettro teorico
17. Report, salvataggio e batch
18. Controllo di qualità e ripetibilità
19. Risoluzione dei problemi
20. Riferimento completo di menu e campi
21. Formule e glossario

<!-- pagebreak -->

## 1. Scopo e limiti del programma

pyLIBS consente di:

- caricare una o più finestre spettrali;
- sottrarre dark e fondo secondo la configurazione;
- dividere ogni finestra per la propria risposta radiometrica;
- calibrare separatamente l'asse delle lunghezze d'onda;
- unire e visualizzare finestre anche sovrapposte;
- trovare massimi realmente osservati;
- associare i picchi a righe atomiche del database offline;
- eseguire fit Voigt singoli o multipli e integrare le aree;
- ricavare Ne dalla larghezza di H-alpha;
- stimare la temperatura con Saha-Boltzmann;
- valutare e, quando supportato, correggere l'autoassorbimento;
- calcolare percentuali atomiche e in massa con CF-LIBS;
- verificare robustezza, esclusioni e sensibilità del risultato;
- produrre report e risultati Excel.

pyLIBS non rende automaticamente valida una misura. Per una quantificazione affidabile servono almeno: una risposta radiometrica adeguata, una calibrazione in lunghezza d'onda, righe prive di interferenze, aree Voigt controllate, Ne misurata, una temperatura sostenuta da un intervallo energetico sufficiente e il superamento dei controlli di qualità.

> Una percentuale mostrata non deve essere accettata se la finestra CF-LIBS segnala un blocco, una correzione non sicura o una forte sensibilità alla rimozione di una singola riga.

## 2. Concetti indispensabili

### 2.1 Tre lunghezze d'onda diverse

Nel programma possono comparire tre valori distinti:

- `wavelen`: lunghezza d'onda analitica o NIST usata per l'identificazione;
- `fitwavelen`: centro osservato ricavato dal fit Voigt;
- asse spettrale: lunghezza d'onda letta dal file, eventualmente corretta dalla calibrazione.

Il listone deve contenere preferibilmente le lunghezze d'onda NIST. Il fit cerca il massimo osservato nell'intorno e determina il suo centro. Non sostituire sistematicamente il valore NIST con il centro osservato.

### 2.2 Area, altezza e larghezza

Per Boltzmann e CF-LIBS viene usata l'area integrata del profilo Voigt, non la sola altezza del picco. I parametri principali sono:

- `wg`: componente gaussiana della larghezza;
- `wl`: componente lorentziana della larghezza;
- `fitwavelen`: centro del profilo;
- `inte` o area corretta: area integrata usata nei calcoli.

Quando due righe sono vicine, il programma usa un fit Voigt multiplo e assegna a ciascuna componente la propria area. La regione di integrazione deve includere il ritorno alla linea di base su entrambi i lati.

### 2.3 Righe osservate e righe del database

Una riga del database è una transizione possibile. Diventa una riga analitica utilizzabile solo se:

1. cade in una finestra realmente acquisita;
2. esiste un massimo misurato compatibile;
3. l'elemento è stato richiesto in `Trace Lines`;
4. l'assegnazione atomica è completa;
5. il fit Voigt è valido;
6. supera soglia Aki e controlli di qualità.

### 2.4 unità di lunghezza d'onda

Il programma può lavorare in nm o Angstrom. In generale, i file del sistema descritto in questo manuale sono in nm. Non premere `Utilities > Signal Processing > Convert nm to Å` se i dati e le liste sono già coerenti in nm. H-alpha è normalmente indicata come 656.28 nm oppure 6562.8 Angstrom.

### 2.5 Sequenza scientifica corretta

L'ordine di riferimento è:

`dark/fondo -> risposta radiometrica -> calibrazione lambda -> unione finestre -> selezione picchi -> identificazione -> fit Voigt -> Ne -> Saha-Boltzmann -> verifica autoassorbimento -> CF-LIBS -> spettro teorico diagnostico`

Non invertire IRSAC e fit Voigt. IRSAC corregge intensità o aree già misurate; non crea picchi e non sostituisce l'integrazione.

<!-- pagebreak -->

## 3. Avvio rapido: una misura completa

### 3.1 Prima esecuzione

La cartella del programma deve contenere almeno `pyLIBS.py`, la cartella `pylibs`, i database distribuiti e la cartella `docs`. Sono richiesti Python 3.11 o successivo e i pacchetti elencati in `requirements.txt` (`NumPy`, `SciPy`, `Matplotlib`, `OpenPyXL` e dipendenze). Per una nuova installazione, da terminale nella cartella del programma eseguire `python -m pip install -r requirements.txt`; quindi avviare con `python pyLIBS.py` o con il collegamento predisposto. Se compare un errore prima dell'apertura della finestra principale, non iniziare l'analisi: conservare il testo completo dell'errore e verificare ambiente Python, dipendenze e integrità dei file del programma.

Al primo avvio aprire `Help > User Manual > Italiano` per verificare che questo documento sia raggiungibile, quindi impostare `Edit > Options...`. Il programma ricorda la cartella di lavoro usata più di recente, ma non sostituisce un archivio sperimentale ordinato.

### 3.2 Procedura rapida

Questa è la procedura minima per un campione incognito.

1. Avviare `pyLIBS.py`.
2. Aprire `Edit > Options...` e verificare database, dark, risposta, unità e parametri di fit.
3. Caricare tutte le finestre del campione con `File > Load independent windows...` quando si vogliono evitare completamente i raccordi. Usare `File > Append...` solo se si desidera esplicitamente lo spettro unito.
4. Controllare che il grafico mostri solo gli intervalli realmente acquisiti e che non siano presenti segmenti obliqui nei vuoti tra finestre.
5. Aprire `Utilities > Instrument Calibration > Instrument Response...`, caricare tutte le curve di risposta e applicare `signal / response` se non sono già memorizzate.
6. Aprire `Utilities > Instrument Calibration > Wavelength Calibration...`, caricare o incollare righe NIST note, stimare ogni finestra e usare `Apply and remember`.
7. Aprire `Utilities > Analytical Line Lists > Main Analytical-Line Library...` e verificare che il listone principale sia caricato.
8. In `Analyse > Spectral Fitting > Automatic Fit...`, usare `Find visible peaks`; aggiungere manualmente eventuali massimi mancanti con `Add peak from graph`.
9. Aprire `Analyse > Peak and Line Detection > Trace Lines...`, inserire un elemento alla volta, mantenere `Only near selected peaks`, scegliere stato ionico e tolleranza, quindi `OK` e `Assign`.
10. Ripetere il punto 9 esclusivamente per gli elementi che si vogliono analizzare. Se un elemento è stato inserito per errore, selezionarlo e premere `Canc` oppure `Remove element (Del)`.
11. Tornare ad `Auto Fit`, impostare o verificare le ROI e premere `Fit selected peaks (Voigt)`. Controllare centri, area, larghezze, CV delle repliche e qualità.
12. Caricare separatamente H-alpha con `Analyse > Plasma Diagnostics > Electron Density from Hα...`; verificare il massimo corretto, eseguire il fit e confermare Ne.
13. Aprire `Analyse > Plasma Diagnostics > Saha-Boltzmann Plot...`, scegliere `Most reliable element` oppure una specie esplicita e calcolare. Controllare numero di righe, livelli, Delta Ek, R2 e stabilità leave-one-out.
14. Aprire `Analyse > Plasma Diagnostics > Self-Absorption / IRSAC...`. Leggere prima la diagnosi. Applicare la correzione solo se esistono evidenze sperimentali che la giustifichino.
15. Aprire `Analyse > Quantitative Analysis > CF-LIBS...`, usare la T e Ne correnti, calcolare e controllare `Robustness` e `Show Report` prima di accettare le percentuali.
16. Salvare il report con tutte le informazioni della misura.

> Non usare `OPC` come passaggio obbligatorio per un campione incognito. OPC è una calibrazione con standard noto, utile solo quando si dispone di una composizione nominale affidabile.

## 4. Configurazione iniziale

Aprire `Edit > Options...`. Premere `Save Options` quando le impostazioni devono rimanere disponibili ai successivi avvii. `OK` applica alla sessione corrente; `Cancel` annulla le modifiche non salvate.

### 4.1 Atomic library

- `LIBS++`: database storico del programma originale.
- `NIST ASD 5.12`: database offline costruito dai dati NIST ASD 5.12.
- `Browse...`: seleziona un database SQLite compatibile.

Per il flusso descritto qui usare normalmente `NIST ASD 5.12`. Il database è offline: non è necessario collegarsi a Internet durante l'analisi.

### 4.2 Sottrazione del segnale di buio

- `Automatic from auxiliary columns`: usa una colonna come segnale e le altre colonne compatibili come dark, secondo la struttura del file.
- `Constant dark level`: sottrae il valore indicato in `Constant`.
- `Dark-spectrum file`: sottrae il tracciato indicato con `Dark file...`.
- `No dark subtraction`: non applica sottrazione del dark.

`Signal col. (0=auto)` permette di indicare la colonna del segnale. Con 0 il programma la sceglie automaticamente. `Dark cols.` permette di specificare le colonne dark. Verificare sempre il risultato sul grafico: un dark errato modifica fondo, area e rapporto segnale/rumore.

### 4.3 Correction e Global Correction

`Correction > Apply` abilita la risposta radiometrica. `Load files...` accetta più curve, una per finestra.

- `Apply Before`: divide i dati per la risposta prima del fit. È il flusso consigliato per ottenere direttamente aree radiometricamente corrette.
- `Apply After`: conserva il fit nel dominio del rivelatore e corregge successivamente l'intensità analitica. Usarlo solo quando il flusso è stato impostato deliberatamente in questo modo.

Non applicare la risposta due volte. Il report indica il dominio e la correzione effettivamente usati.

### 4.4 Data Fit

- `Voigt baseline model = Local linear baseline` (predefinita): usa una baseline locale con intercetta e pendenza libere.
- `Adaptive baseline-to-baseline limits`: stima automaticamente i limiti di ritorno alla linea di base.
- `Local constant baseline`: usa una baseline locale costante.
- `Fix wg`, `Fix wl`, `Fix wavelength`: bloccano parametri del fit. Lasciarli disattivati salvo motivo sperimentale preciso.
- `Iterations`: massimo lavoro dell'ottimizzatore.
- `Instr. FWHM @ H-alpha`: larghezza gaussiana strumentale globale, non larghezza totale del picco H-alpha.

### 4.5 Analisi Boltzmann e soglia Aki

In `Boltzmann analysis > Intensity convention` scegliere la convenzione coerente con la risposta strumentale:

- `Energy-domain response (convert with λ/hc)`: usare quando la correzione restituisce un'intensità energetica, per esempio proporzionale a `W·m^-2`. Il programma converte l'energia in numero equivalente di fotoni mediante `λ/(h·c)`;
- `Photon-counting response (original pyLIBS)`: usare quando l'intensità corretta è già espressa in fotoni o conteggi con risposta riferita ai fotoni. In questa modalità non deve essere applicato nuovamente il fattore `λ/(h·c)`.

La modalità energetica è predefinita per preservare la configurazione attuale. Cambiare convenzione invalida i risultati Saha-Boltzmann, IRSAC e CF-LIBS già calcolati, che devono essere ricalcolati. Non scegliere la modalità in base al risultato atteso, ma in base alle unità e alla procedura con cui è stata costruita la risposta strumentale.

`Aki threshold` filtra le righe analitiche deboli. Il valore operativo predefinito è 1e5 s^-1. `Theory Aki threshold` controlla la soglia dello spettro teorico. Aumentare la soglia riduce righe deboli e possibili identificazioni fragili, ma può lasciare troppo pochi livelli energetici per la temperatura.

### 4.6 Wavelength calibration

- `Legacy global Delta lambda`: traslazione unica storica. Non è adeguata quando lo shift cambia tra finestre.
- `Use saved per-window calibration`: applica il profilo salvato in modo indipendente a ciascuna finestra.
- `Per-window calibration...`: apre la procedura descritta al capitolo 8.

### 4.7 H-alpha parameters

I campi `wl1`, `dl1`, `Delta`, `wl2`, `dl2` e `kT` appartengono al calcolo storico della densità elettronica. `Keep active Ne after Clear Graph` conserva esplicitamente Ne tra misure della stessa serie. Lasciarlo disattivato se il nuovo campione o la nuova condizione laser richiedono una nuova Ne.

### 4.8 Validazione quantitativa

`Suppress composition results that fail validation` impedisce di presentare come quantitative percentuali prive di supporto minimo. Le soglie controllano, tra l'altro:

- numero di righe e livelli per la temperatura;
- intervallo Delta Ek e R2;
- errore della pendenza e sensibilità leave-one-out;
- dispersione delle popolazioni di riga;
- qualità e SNR di H-alpha;
- margine di McWhirter;
- frazione dello stadio ionico osservato;
- incertezza relativa di Ne;
- CV delle aree Voigt tra repliche, usato come avviso di precisione e non come filtro automatico della riga;
- sensibilità della composizione a righe, repliche, T e Ne.

Non allentare le soglie per far apparire una percentuale. Correggere prima acquisizione, righe, fit o parametri fisici.

### 4.9 Altri campi di Options

| Campo | Significato e uso |
|---|---|
| Username | nome dell'operatore riportabile nella configurazione; non modifica i calcoli |
| Auto Offset | opzione storica per la gestione automatica dell'offset; verificare sempre il fondo risultante |
| Convert to Angstrom | moltiplica l'asse in nm per 10 durante l'importazione; non attivarlo per dati già in Angstrom |
| Wavelength Limits | limiti usati soprattutto nell'importazione dei formati storici; devono contenere l'intervallo acquisito |
| Temperature Range | intervallo ammesso per kT in eV; un risultato sul bordo richiede controllo, non ampliamento automatico del range |
| Electron Density Range | intervallo ammesso per Ne in cm^-3; non rappresenta la Ne misurata |
| Threshold | soglia generale storica di rilevamento; non sostituisce i controlli locali di picco e SNR |
| Delta min. | semilarghezza minima usata da funzioni di ricerca/associazione; valori eccessivi aumentano associazioni ambigue |
| Range | intervallo di ricerca storico attorno alla posizione attesa |
| Echelle | compatibilità con il flusso echelle; lasciare disattivato per finestre lineari ordinarie |
| Self-absorption Mode | seleziona `Combined Stark-width and IRSAC correction`, `Stark-linewidth correction` o `IRSAC internal-reference correction`; vedere il capitolo 14 |
| Thermometric species | specie dalla quale IRSAC ricava prima la T grezza e poi la T corretta congelata; se vuota usa il riferimento Saha-Boltzmann o la specie con l'intervallo Ek più ampio |
| Fallback T | valore usato soltanto se la specie termometrica non consente di calcolare una pendenza grezza valida |

Gli intervalli sono limiti di validità, non valori da usare per migliorare artificialmente un risultato. Dopo una modifica scientifica premere `Save Options` solo quando si vuole renderla predefinita anche per le sessioni successive.

### 4.10 Ripristino completo

`Edit > Restore Factory Settings...` cancella le personalizzazioni dell'applicazione e ripristina i valori distribuiti. Usarlo quando si sospetta che vecchie impostazioni influenzino una nuova analisi. Dopo il ripristino, ricontrollare database, risposta strumentale e calibrazioni.

<!-- pagebreak -->

## 5. Interfaccia principale

La finestra principale contiene menu, barra rapida, grafico e barra di stato.

### 5.1 Barra rapida essenziale

- `Open`: apre un singolo spettro come spettro principale.
- `Append`: carica più file o finestre nella stessa sessione.
- `Clear`: pulisce il grafico e lo stato della misura; il listone persistente viene ricaricato.
- `Active Spectra`: mostra, nasconde, scala o combina gli spettri caricati.
- `Response`: gestisce le curve radiometriche.
- `Full Scale`: ripristina l'intera vista.
- `Selected Lines`: apre il listone operativo.
- `Trace`: identifica le righe degli elementi richiesti.
- `Ne from H`: calcola Ne da H-alpha.
- `Auto Fit` e `Manual Fit`: eseguono il fit Voigt.
- `Saha-Boltzmann`: calcola la temperatura.
- `CF-LIBS`: calcola le concentrazioni.

Passare il mouse sopra un'icona per leggerne il nome.

### 5.2 Navigazione del grafico

Usare gli strumenti Matplotlib per zoom e spostamento. `View > Zoom and Scale > Fit X Axis`, `Fit Y Axis` e `Show Full Spectrum` ripristinano gli assi. `Utilities > Go To Wavelength...` centra il grafico su una lunghezza d'onda comune o inserita manualmente.

### 5.3 Barra di stato

La barra inferiore comunica caricamenti, correzioni, Ne attiva, salvataggi e errori. Leggerla dopo ogni operazione. Un comando senza cambiamento visibile può avere prodotto un messaggio nella barra di stato.

## 6. File spettrali e caricamento

### 6.1 Formati accettati

Il selettore supporta TXT, DAT, ROH, TRT, MCH, JND, ASC, CSV e Andor SIF, incluse le estensioni maiuscole. I file CSV devono contenere due colonne: lunghezza d'onda e intensità. I separatori virgola, punto e virgola e tabulazione vengono rilevati automaticamente; sono accettati intestazione facoltativa, righe vuote e BOM UTF-8. La virgola decimale è accettata con separatori punto e virgola/tabulazione e nei campi CSV tra virgole racchiusi tra virgolette. I valori con virgola decimale separati da virgole senza virgolette sono ambigui e richiedono punto e virgola o tabulazione. Il supporto SIF comprende gli spettri 1D estratti e calibrati (inclusi quelli prodotti dal Mechelle 5000); immagini, acquisizioni multi-frame e altri layout SIF sono segnalati come non supportati.

### 6.2 Open, Append e Compare

- `File > Open...`: sostituisce lo spettro principale con un file.
- `File > Append...`: carica più finestre insieme e costruisce lo spettro unito.
- `File > Load independent windows...`: carica tutte le finestre della stessa misura senza unirle, interpolarle o mediare le sovrapposizioni.
- `File > Compare...`: aggiunge uno spettro come confronto visivo.

Per evitare artefatti nei raccordi, usare `Load independent windows...` e selezionare in una sola volta tutte le finestre della stessa acquisizione media. Ogni file mantiene i propri punti, la propria calibrazione e la propria risposta strumentale. Auto Fit e Manual Fit usano una sola finestra reale per ogni gruppo di righe. Se due finestre coprono la stessa riga, prevale quella selezionata in `Active Spectra`; in assenza di una scelta esplicita viene usata la finestra meglio centrata. Un fit che richiederebbe punti appartenenti a due finestre differenti viene rifiutato.

`Append` rimane disponibile per compatibilità e costruisce lo spettro unito. Il motore conserva comunque le finestre sorgente, ma il grafico principale contiene il raccordo lineare nelle sovrapposizioni.

### 6.3 Finestre sovrapposte e intervalli mancanti

In modalità `Append`, le finestre che si sovrappongono vengono unite con una transizione lineare nella zona comune. In modalità indipendente non viene calcolato alcun raccordo: le curve possono sovrapporsi visivamente, ma i loro campioni restano separati. Intervalli non acquisiti rimangono vuoti e una riga atomica fuori da ogni finestra acquisita non può entrare nei calcoli.

### 6.4 Active Spectra

Aprire `Edit > Spectrum Management > Show Active Spectra`.

- doppio clic: mostra o nasconde uno spettro secondario;
- clic destro: seleziona uno spettro per operazioni multiple;
- `Shift copy`: crea una copia spostata verticalmente del valore `Offset`;
- `Scale copy`: crea una copia moltiplicata per `Scale`;
- `Average selected`: media punto per punto gli spettri selezionati;
- `Max selected` e `Min selected`: calcolano inviluppi massimo e minimo;
- `Delete selected`: elimina le copie selezionate, mai lo spettro principale.

### 6.5 Clear Graph e memoria della sessione

`Edit > Spectrum Management > Clear Graph` rimuove spettri, fit, marcatori e risultati della misura corrente. Il listone principale persistente resta disponibile e viene ripristinato. Ne viene cancellata, salvo che `Keep active Ne after Clear Graph` sia stato esplicitamente attivato per una serie omogenea.

## 7. Dark, fondo e funzione strumentale

### 7.1 Ordine delle correzioni

Per ogni finestra il flusso è:

1. scelta della colonna segnale;
2. sottrazione dark o fondo configurato;
3. divisione per la risposta radiometrica della finestra;
4. calibrazione dell'asse lambda;
5. unione con le altre finestre.

### 7.2 Caricare la risposta radiometrica

1. Aprire `Utilities > Instrument Calibration > Instrument Response...`.
2. Premere `1. Load response files...`.
3. Selezionare insieme tutte le curve misurate con tungsteno/deuterio.
4. Verificare nella tabella `Matched window(s)` che ogni curva sia associata alla finestra corretta.
5. Premere `2. Apply signal / response`.
6. Controllare il grafico e il messaggio di stato.

Le curve devono rappresentare la sensibilità spettrale da dividere. Non sono profili di allargamento della riga.

### 7.3 Bordi della risposta

Il programma elimina i bordi non affidabili della curva e non prolunga artificialmente la risposta fuori dal suo intervallo. Se manca una curva compatibile, la finestra viene segnalata. L'unica eccezione intenzionale è il caricamento dedicato di H-alpha per Ne, che può ignorare la risposta radiometrica perché usa principalmente la larghezza.

### 7.4 Larghezza strumentale globale

`Global width @ 656 nm...` memorizza la FWHM attribuita allo strumento, determinata indipendentemente. Nel metodo H-alpha originale di Palleschi viene usata per correggere la larghezza lorentziana misurata:

`FWHM_L,corr = max(FWHM_L,fit - FWHM_strumento^2 / FWHM_L,fit, 0)`

Lo stesso valore resta disponibile come approssimazione globale per lo spettro teorico. Non inserire la FWHM totale H-alpha dominata da Stark. Se la larghezza strumentale non è nota, usare 0.

## 8. Calibrazione in lunghezza d'onda

Aprire `Utilities > Instrument Calibration > Wavelength Calibration...` prima dell'identificazione automatica.

### 8.1 Preparare le righe di riferimento

Usare lunghezze d'onda NIST certe e presenti nel campione. Si può:

- premere `Load NIST line list...` e caricare un file;
- incollare una serie di valori in `or paste wavelengths` e premere `Add`;
- usare righe NIST già presenti nel listone selezionato.

Sono accettati valori con punto o virgola decimale. Una lista può contenere intestazioni di elemento e stato ionico.

### 8.2 Stimare la calibrazione

1. Impostare `Maximum initial shift`, per esempio 0.8 nm se lo shift atteso è inferiore.
2. Scegliere `Model = auto`.
3. Premere `Estimate from selected NIST lines`.
4. Verificare per ogni finestra numero di righe, Delta lambda al centro, scala `b`, RMS e `Quality`.
5. Se sono già disponibili centri Voigt affidabili, usare `Use identified Voigt fits`.

Con una o due righe il modello automatico applica solo un offset. Per una scala lineare `lambda_corrected = a + b * lambda_raw` servono almeno tre righe coerenti distribuite su almeno 5 nm.

### 8.3 Escludere un riferimento errato

Selezionare una finestra nella tabella superiore. Nella tabella inferiore selezionare la riga sospetta e premere `Include / exclude selected line`, oppure fare doppio clic. Ripetere la stima e controllare che RMS e residui migliorino per ragioni fisiche, non soltanto numeriche.

### 8.4 Applicare e ricordare

- `Apply to loaded spectra`: applica soltanto ai dati correnti.
- `Apply and remember`: applica e salva i profili per misure successive con finestre compatibili.
- `Clear saved calibration`: cancella i profili persistenti.

Una calibrazione per finestra è preferibile a uno shift globale quando lo scostamento cambia tra i rivelatori.

### 8.5 Shift manuale e altri interventi sull'asse

`Utilities > Instrument Calibration > Manual Wavelength Shift...` serve per una correzione controllata quando è nota una singola riga. In `Move Point at` inserire la posizione osservata; in `to` inserire la posizione di riferimento. Il programma applica `shift = riferimento - osservato`.

1. Premere `Pick` e fare clic prima sul punto osservato, poi sulla posizione di destinazione, oppure digitare entrambi i valori.
2. Attivare `Shift all spectra` solo se lo stesso offset è valido per tutti gli spettri visualizzati.
3. Attivare `Shift Identifications` solo se anche marcatori, righe assegnate e centri di fit devono seguire lo spostamento.
4. Premere `OK`, controllare una seconda riga indipendente e salvare il profilo per finestra quando possibile.

`Utilities > Signal Processing > Intensity Offset...` applica allo spettro principale lo spostamento verticale `valore desiderato - valore corrente`. Non è una sottrazione fisica del dark e non deve essere usato per mascherare un fondo errato.

`Utilities > Signal Processing > Smooth Spectrum` modifica i valori Y dello spettro principale: usa Savitzky-Golay con finestra 11 e ordine 4 quando SciPy è disponibile, altrimenti una media mobile. Il dato smussato può alterare altezza e larghezza; per aree quantitative partire normalmente dal dato non smussato.

`Utilities > Signal Processing > Convert nm to Å` moltiplica l'asse per 10. Usarlo una sola volta e solo quando l'asse corrente è realmente in nanometri. `Go To Wavelength...` cambia soltanto la vista del grafico.

## 9. Listone e righe selezionate

Aprire `Utilities > Analytical Line Lists > Main Analytical-Line Library...` o il pulsante `Selected Lines`.

### 9.1 Che cosa contiene il listone

Il listone persistente contiene righe analitiche candidate, normalmente con lunghezze d'onda NIST e metadati atomici. La tabella aperta è lo spazio di lavoro della misura corrente: oltre all'assegnazione può contenere centro, larghezze e area Voigt osservati.

### 9.2 Comandi principali

- `Import lines...`: importa una lista per l'analisi corrente.
- `Save lines`: salva le righe correnti.
- `Clear fit`: cancella i risultati Voigt ma conserva le righe.
- `Delete row`: elimina la riga selezionata.
- `Saha-Boltzmann`: apre direttamente l'analisi della temperatura.
- `More > Line summary`: mostra un riepilogo.
- `More > Clear selected lines`: svuota lo spazio di lavoro corrente.
- `More > Close line list`: chiude la lista attiva secondo il flusso storico.
- `More > Delete saved list`: elimina la lista salvata selezionata.

### 9.3 Gestione della libreria persistente

Nel menu `Manage library`:

- `Reload main library`: ricarica il listone principale dal disco;
- `Add secondary list...`: fonde una lista aggiuntiva evitando duplicati;
- `Replace main library...`: sostituisce il listone principale;
- `Save current lines as main`: rende persistenti le righe correnti, rimuovendo risultati di fit e intensità specifici della misura;
- `Restore included library`: ripristina la lista distribuita col programma.

Il listone non autorizza automaticamente tutti gli elementi alla quantificazione. L'insieme degli elementi analizzati è definito esplicitamente da `Trace Lines` nella sessione corrente.

## 10. Ricerca dei picchi e identificazione

### 10.1 Find Peaks

`Analyse > Peak and Line Detection > Find Peaks` individua massimi locali nello spettro visibile. Serve a costruire candidati osservati; non assegna da solo elemento e stato ionico.

### 10.2 Trace Lines: procedura corretta

1. Se necessario, ingrandire il grafico sull'intervallo da analizzare.
2. Aprire `Analyse > Peak and Line Detection > Trace Lines...`.
3. Inserire il simbolo in `Trace Species`, per esempio `Cu`, `Sn` o `Pb`.
4. Scegliere `I`, `II`, `Both` oppure `All`.
5. Lasciare attivo `Only near selected peaks` per accettare soltanto transizioni vicine a massimi osservati già selezionati.
6. Impostare `Tolerance` nell'unità mostrata.
7. Premere `OK` e controllare la tabella.
8. Premere `Assign` soltanto se le righe sono coerenti.
9. Ripetere per ogni elemento effettivamente richiesto.

`Max Lines (all mode)` limita il numero di righe quando si esplora `All`. Disattivare `Only near selected peaks` soltanto per consultare il database: le righe attese ma prive di massimo non devono diventare aree analitiche.

### 10.3 Rimuovere un elemento errato

Se un elemento è stato tracciato per errore, selezionare una sua riga nella tabella e premere `Canc`, oppure `Remove element (Del)`. Vengono rimossi i marcatori e le assegnazioni di quell'elemento senza distruggere i fit Voigt degli altri elementi.

### 10.4 Identifications

La finestra di identificazione permette una ricerca puntuale:

1. attivare il database con `Use LIBS.db` oppure caricare un CSV atomico;
2. scegliere `Datalibs` o `Daticerti`;
3. inserire lambda e `range`;
4. premere `Search`;
5. fare doppio clic sulla transizione corretta per assegnarla al picco selezionato più vicino.

Controllare sempre `Aki`, energie `Ei/Ek`, pesi statistici `gi/gk` e stato ionico. Una vicinanza in lambda da sola non dimostra l'identificazione.

### 10.5 Auto Element Identification

Questa funzione classifica elementi candidati usando corrispondenza spettrale e intensità di database. È uno strumento esplorativo, non un sostituto di `Trace Lines`, del fit e del controllo scientifico. Non usare automaticamente i primi risultati per una quantificazione incognita senza verifica.

## 11. Fit Voigt automatico e manuale

### 11.1 Auto Fit

1. Portare il grafico sull'intervallo utile oppure usare la vista completa.
2. Aprire `Analyse > Spectral Fitting > Automatic Fit...`.
3. Premere `1. Find visible peaks` per selezionare massimi misurati.
4. Se manca un picco evidente, premere `Add peak from graph` e fare clic sul massimo.
5. Normalmente lasciare che Auto Fit cerchi i ritorni alla baseline del campione corrente. Usare `Select ROI limits` soltanto per correggere manualmente una regione problematica, scegliendo il limite sinistro e destro sul grafico.
6. Premere `2. Fit selected peaks (Voigt)`.
7. Controllare la tabella dei risultati e il profilo sovrapposto.

La ricerca automatica non deve piazzare un punto soltanto perché il database prevede una riga. Se non esiste un massimo locale compatibile, la riga non è un picco osservato.

### 11.2 ROI e linea di base

- `Select ROI limits`: imposta manualmente entrambi i bordi.
- `Save current zoom`: usa i limiti X correnti come ROI.
- `Reset ROI`: elimina la ROI memorizzata per la regione.

La ROI deve comprendere sufficiente baseline su entrambi i lati, ma non regioni lontane dominate da altri picchi o curvature del fondo. Auto Fit la ricava nuovamente dallo spettro corrente; una ROI manuale vale soltanto per la sessione che l'ha creata, perché lo shift e la forma del picco possono cambiare fra campioni. Il risultato quantitativo predefinito usa la baseline lineare locale. Con `Adaptive baseline-to-baseline limits` i limiti riportati possono restringersi fino ai piedi del profilo; il fit Voigt resta definito sulla regione usata dall'ottimizzatore.

La scelta della baseline non cambia la definizione quantitativa dell'area: ogni componente è una Voigt normalizzata e il parametro di ampiezza è la sua area integrale completa. I limiti mostrati nel grafico servono alla diagnostica del ritorno alla baseline, non troncono l'area usata da Boltzmann e CF-LIBS.

### 11.3 Picchi doppi o multipli

Quando più righe ricadono nella stessa regione, inserirle tutte prima del fit. Il modello è la somma di componenti Voigt più baseline. Verificare che:

- i centri rimangano vicini ai massimi o alle transizioni assegnate;
- nessuna componente riempia artificialmente tutta la ROI;
- i residui non conservino un secondo massimo strutturato;
- l'area della riga selezionata non venga attribuita al vicino sbagliato.

Nel risultato quantitativo entrano esclusivamente le righe selezionate. Il programma non aggiunge automaticamente Voigt non assegnate: un massimo strutturato nei residui segnala che occorre verificare la regione e, se fisicamente giustificato, selezionare esplicitamente anche la riga interferente prima di rifare il fit multiplo.

### 11.4 Manual Fit

`Analyse > Spectral Fitting > Manual Fit...` permette di modificare centro, componente gaussiana e lorentziana e di fissare singoli parametri. Usarlo per regioni problematiche, non per forzare un risultato desiderato.

- `Fit`: esegue la regione corrente.
- `Next Region` e `Previous Region`: scorrono le regioni del listone.
- `Refresh`: rilegge i dati correnti.
- `Show Residuals`: apre i residui del fit.
- casella `Fix` accanto a un parametro: impedisce all'ottimizzatore di modificarlo.

Un residuo casuale intorno a zero è preferibile. Strutture, picchi residui o andamento curvo indicano componenti mancanti, baseline inadatta o ROI errata.

### 11.5 Fit Gaussiano originale

`Analyse > Spectral Fitting > Manual Fit...` apre il pannello storico con entrambe le scelte. `Fit Gaussian` usa una somma di Gaussiane con baseline lineare:

`G(lambda) = H exp[-((lambda-lambda0)/sigma)^2]`

e salva per ogni riga l'area `A = H sigma sqrt(pi)`. Questa è un'alternativa esplicita: `Auto Fit` e `Manual Fit` continuano a usare il Voigt normalizzato. Non mescolare aree Gaussiane e Voigt nello stesso Boltzmann plot.

### 11.6 Tabella del fit

Controllare per ogni riga:

- `Fit Center Wavelength`;
- `Fit Intensity` e `Fit Integral`;
- `Fit Lorentzian Width` e `Fit Gaussian Width`;
- `Replicate area CV`;
- `Quality`.

`Mean only` indica che non sono disponibili abbastanza repliche individuali per stimare la dispersione. Nei percorsi `Auto Fit` e `Manual Fit`, l'area quantitativa è l'integrale Voigt dello spettro medio. Il CV delle repliche misura la ripetibilità: se supera la soglia configurata compare un avviso, ma la riga resta nel Boltzmann plot quando il fit dello spettro medio è valido. Solo un fit Voigt realmente non valido viene marcato `ERROR` ed escluso dalla quantificazione.

## 12. densità elettronica da H-alpha

H-alpha si usa per la densità elettronica attraverso l'allargamento Stark. Il file a 656 nm può essere caricato anche senza curva radiometrica, esclusivamente in questa procedura.

### 12.1 Procedura

1. Aprire `Analyse > Plasma Diagnostics > Electron Density from Hα...`.
2. Verificare che `wl1` corrisponda a 6562.8 A se l'interfaccia usa Angstrom, oppure al valore coerente con l'unità corrente.
3. Premere `Load H-alpha spectrum (no radiometric response)`.
4. Controllare sul grafico che il massimo scelto sia realmente H-alpha.
5. Se lo spettro è shiftato di 0.3-0.4 nm, applicare prima la calibrazione salvata o confermare lo scostamento osservato quando richiesto.
6. Eseguire `Fit Hα and estimate Ne`, unico metodo disponibile e corrispondente al flusso originale di Palleschi.
7. Leggere Ne, qualità del fit, SNR e incertezza.

### 12.2 Quale larghezza usa Ne

Il metodo Palleschi esegue il fit di una o due componenti lorentziane. La FWHM della componente H-alpha principale viene corretta con la larghezza strumentale configurata e quindi inserita nella relazione Stark per Ne. La risposta radiometrica non è necessaria per la sola larghezza, ma dark, fondo e asse lambda devono essere corretti.

### 12.3 Quale Ne usa il programma

La sessione mantiene una Ne attiva con una sorgente esplicita. Saha-Boltzmann e CF-LIBS usano la Ne corrente, non un valore casuale. `Clear Graph` la cancella per impostazione predefinita; conservarla è corretto soltanto per una serie sperimentale omogenea.

> Ricalcolare Ne quando cambiano potenza laser, ritardo, gate, geometria, matrice o condizioni del plasma.

## 13. Temperatura Saha-Boltzmann

### 13.1 Prerequisiti

Prima di aprire il grafico servono:

- elementi ammessi con `Trace Lines`;
- righe assegnate con stato ionico corretto;
- dati atomici completi;
- aree Voigt valide;
- Ne attiva;
- risposta radiometrica coerente.

### 13.2 Calcolo

1. Aprire `Analyse > Plasma Diagnostics > Saha-Boltzmann Plot...`.
2. Lasciare `Initial kT (eV) = 1` salvo informazione migliore.
3. Scegliere la modalità `Temperature`.
4. Premere `Compute Plot`.

Nell'ordinata radiometrica il programma usa esclusivamente la lunghezza d'onda NIST assegnata (`asswavelen`, con ripiego sulla lunghezza d'onda NIST preselezionata). Il centro Voigt osservato (`fitwavelen`) serve solo a localizzare e verificare il picco. Quando la risposta strumentale viene applicata dopo il fit, anche il relativo fattore viene valutato alla lunghezza d'onda NIST.

Modalità disponibili:

- `Most reliable element`: sceglie la specie termometrica più sostenuta dai dati;
- `Single element temperature`: usa l'elemento selezionato nella tabella;
- `Mean temperature`: combina le temperature ammesse.

### 13.3 Criterio della specie termometrica

Il criterio privilegia una distribuzione energetica ampia, con almeno il numero minimo di righe e livelli, un buon R² e stabilità leave-one-out. A parità di qualità, un maggiore `dEk eV` fornisce più informazioni sulla pendenza. Una specie con pochi punti quasi alla stessa Ek non è una buona specie termometrica, anche se il suo R² è alto.

### 13.4 Significato delle colonne

- `Use / role`: Fit, Reference, No o ruolo diagnostico.
- `lines`: righe utilizzabili.
- `levels`: livelli energetici superiori distinti.
- `dEk eV`: intervallo tra Ek minimo e massimo.
- `kT eV`: temperatura elettronica espressa come energia.
- `R2`: coefficiente di determinazione del fit.
- `LOO dT/T`: variazione massima rimuovendo una riga alla volta.
- `q`, `Z I`, `Z II`: parametri Saha e funzioni di partizione.

Fare doppio clic o premere spazio su una riga per includere/escludere un elemento quando previsto. `Check Lines` spiega perché ogni riga è stata usata o scartata.

### 13.5 Prima e dopo IRSAC

Prima della correzione, le specie possono avere pendenze diverse e il programma le mostra come diagnostica. Dopo la scelta della temperatura comune, CF-LIBS impone la pendenza `-1/kT` alle altre specie e rifitta soltanto le intercette. Non interpretare rette parallele post-correzione come misure indipendenti di temperatura.

### 13.6 Conversione

La relazione è:

`T(K) = kT(eV) * 11604.518`

Una variazione di 0.02 eV corrisponde a circa 232 K.

## 14. Autoassorbimento e IRSAC

L'autoassorbimento non deve essere applicato automaticamente a ogni campione. Prima si valuta l'evidenza, poi si sceglie la correzione.

### 14.1 modalità

- `Combined Stark-width and IRSAC correction`: combina il controllo basato sulla larghezza Stark con IRSAC per le righe supportate.
- `Stark-linewidth correction`: usa soltanto la correzione basata sulla larghezza Stark prevista e osservata.
- `IRSAC internal-reference correction`: applica l'IRSAC a riferimenti interni di ciascuna specie; la specie termometrica determina la temperatura corretta congelata usata nelle correzioni successive.

La correzione basata sulla larghezza Stark richiede una corrispondenza specifica di riga nel database `Stark.db`. L'assenza di quella riga non dimostra assenza di autoassorbimento: significa che quel controllo non è disponibile per quella transizione.

### 14.2 Diagnosi prima della correzione

Aprire `Check SA` da Saha-Boltzmann oppure `Analyse > Plasma Diagnostics > Self-Absorption / IRSAC...`. Controllare:

- coerenza di righe con stesso livello superiore;
- andamento dell'ordinata rispetto a Ek;
- larghezza osservata e larghezza Stark disponibile;
- qualità del fit e interferenze;
- fattori di correzione fisicamente plausibili;
- risultato `No significant evidence`, `Self-absorption compatible`, `Not assessable` o `Correction unsafe`.

`Not assessable` non equivale a `no autoassorbimento`. Significa che i dati non consentono una decisione solida.

### 14.3 Temperatura iniziale di fallback

`Initial-T fallback` può essere:

- `Auto (from Saha)`: riusa la riga di riferimento selezionata in Saha-Boltzmann solo quando serve una T iniziale di ripiego;
- una specie esplicita, per esempio `Cd I`, `Sn I` o `Pb I`.

La specie termometrica selezionata determina sia la T grezza sia la T corretta che viene poi congelata durante IRSAC. In `Auto (from Saha)` viene riutilizzata la specie di riferimento Saha-Boltzmann; una scelta esplicita, per esempio `Cd I`, resta fissa. Conviene usare una specie con ampio intervallo Ek, almeno tre livelli superiori indipendenti e fit stabile. Le altre specie non possono spostare la T IRSAC.

### 14.4 Riga di riferimento IRSAC

Per ogni specie atomica o ionica, una riga funge da riferimento interno. `Automatic line references` applica l'equazione (7) di Yang: scarta le accuratezze Aki peggiori del 50%, considera i candidati con l'accuratezza migliore e assegna peso 0,5 al rango crescente di Ei e 0,5 al rango decrescente di Aki. Per imporre un riferimento, selezionare la riga nella tabella e premere `Use selected line as IRSAC reference`. Una scelta manuale deve essere documentata e rende più severo il controllo quantitativo.

### 14.5 Metodo IRSAC a T termometrica congelata

La modalità quantitativa è `Staged Aslam IRSAC (internal references)`. Mantiene le aree integrate già misurate e applica questa sequenza una sola volta:

1. calcola la temperatura grezza dalla retta della sola specie termometrica, `y = ln(lambda_NIST I / Aki gk)`; usa il valore di fallback soltanto se questa retta non è calcolabile;
2. sceglie per ogni specie una riga di riferimento interna con l'equazione (7), oppure usa quella impostata manualmente;
3. alla T grezza calcola per ogni riga della specie termometrica `f_k = I_k (A_ref g_ref)/(I_ref A_k g_k) exp[-(E_ref-E_k)/(0,69503476 T)]`;
4. corregge l'area con `I_corr,k = I_k/f_k`; per la riga di riferimento `f_ref=1` per costruzione;
5. esegue nuovamente il fit del solo Boltzmann plot corretto della specie termometrica e ottiene la T IRSAC finale;
6. congela questa T e calcola, con la stessa equazione, i fattori di tutte le altre specie usando per ciascuna la propria riga di riferimento interna;
7. non aggiorna più la T con le altre specie e non forza le loro pendenze libere a diventare parallele;
8. nel CF-LIBS finale impone a tutti la pendenza fisica comune `m=-1/(kB T_IRSAC)` e stima soltanto l'intercetta `q = media(y_corr - m E)`.

La lambda NIST assegnata compare nell'ordinata di Boltzmann e nella risposta strumentale, ma non viene introdotta una seconda volta nell'equazione (6). Il centro osservato resta un risultato del fit e non sostituisce la lambda della transizione. Un moltiplicatore relativo `1/f_k` inferiore a 1 è ammesso: descrive la normalizzazione rispetto alla riga di riferimento scelta, non una misura assoluta della profondità ottica.

Per confrontare pyLIBS con un foglio esterno occorrono le stesse aree integrate, risposta strumentale, lambda NIST, Aki, gk, Ek, righe di riferimento e specie termometrica.

### 14.6 Ricalcolo

- `Recalculate IRSAC`: riusa le aree già misurate e ricalcola soltanto la correzione. IRSAC non rifitta mai lo spettro e non modifica le aree.
- Se cambiano baseline o ROI, ripetere esplicitamente il fit nella finestra di fitting e solo dopo ricalcolare IRSAC.
- `Apply correction`: rende attivi i fattori accettati.
- `Remove correction`: torna alle aree non corrette.

La finestra mostra T grezza, T IRSAC finale, specie termometrica, reference, fattori relativi e controlli diagnostici. Se la T corretta della specie termometrica non è calcolabile, i fattori non possono essere applicati. I controlli di qualità restano visibili, ma non modificano di nascosto l'equazione o le aree.

### 14.7 Quando non usare la correzione

Non applicare IRSAC se:

- la diagnosi non mostra evidenza significativa;
- le righe sono interferite o il fit è instabile;
- la riga di riferimento è stata imposta senza un supporto indipendente;
- i fattori sono non fisici o marcati unsafe;
- la correzione peggiora coerenza tra righe dello stesso elemento;
- il risultato dipende quasi interamente da una sola riga.

Una correzione può essere visualizzata a scopo diagnostico ma essere bloccata per la produzione di percentuali.

### 14.8 Finestra SAC storica

`Analyse > Plasma Diagnostics > SAC Factors...` calcola fattori diagnostici con `kT`, `Ne`, cammino ottico `path lu` e densità totale `N total`. Se esiste un risultato CF-LIBS, usa le sue `Number %`; altrimenti assegna percentuali uguali agli elementi presenti. La tabella restituisce `SAC`, larghezze e coefficiente al centro riga.

Questa finestra non sostituisce `Self-Absorption / IRSAC` e non costituisce da sola una misura della concentrazione o del cammino ottico. Usarla soltanto come strumento specialistico quando `lu` e `N total` sono giustificati sperimentalmente.

## 15. Concentrazioni CF-LIBS

### 15.1 Prerequisiti

CF-LIBS richiede una temperatura comune valida, Ne esplicita, aree Voigt corrette, funzioni di partizione e insieme degli elementi definito da `Trace Lines`.

### 15.2 Procedura

1. Aprire `Analyse > Quantitative Analysis > CF-LIBS...`.
2. Premere `Use current T / Ne` se la finestra era già aperta prima dell'ultimo calcolo.
3. Verificare `kT eV` e `Ne cm^-3` e la sorgente indicata nello stato.
4. Lasciare `Intercepts` nella modalità quantitativa a temperatura comune.
5. Premere `Compute CF-LIBS`.
6. Controllare la tabella, poi `Robustness` e `Show Report`.

La modalità a pendenze libere è soltanto diagnostica e non produce percentuali quantitative. Con temperatura comune il programma fissa la pendenza `-1/kT` e stima un'intercetta per ogni elemento.

### 15.3 Ionizzazione

Il rapporto ionizzato/neutro non viene preso come percentuale manuale dal NIST. Viene calcolato automaticamente con Saha-Eggert usando T, Ne, energia di ionizzazione e funzioni di partizione. La frazione neutra è:

`f_neutra = 1 / (1 + N_II/N_I)`

La popolazione totale dell'elemento combina quindi gli stadi osservati secondo quel rapporto.

### 15.4 Number % e Mass %

`Number %` è la frazione atomica o molare:

`x_i = N_i / sum(N_j) * 100`

`Mass %` è calcolata dai pesi atomici:

`w_i = N_i * M_i / sum(N_j * M_j) * 100`

Non moltiplicare o dividere nuovamente per il peso atomico dopo aver letto `Mass %`. Confrontare percentuali teoriche molari con `Number %` e percentuali teoriche in massa con `Mass %`.

### 15.5 Colonne di robustezza

- `q spread factor` e `Line check`: coerenza delle popolazioni ricavate dalle righe;
- `LOO max %`: massima variazione eliminando una riga;
- `Replicate CV %`: dispersione tra composizioni ottenute dalle repliche;
- `T/Ne max %`: sensibilità alle incertezze di temperatura e densità elettronica.

Per campioni con tre o più elementi questi controlli sono indispensabili: la chiusura al 100% può nascondere un elemento sovrastimato che comprime tutti gli altri.

### 15.6 Audit delle righe

`Show Report` contiene l'elenco delle righe usate ed escluse con motivo. Controllare che:

- compaiano soltanto gli elementi richiesti;
- non compaiano righe fuori dalle finestre acquisite;
- stato ionico e metadati siano corretti;
- nessun risultato dipenda da righe con fit `ERROR`;
- l'Aki soddisfi la soglia.

### 15.7 OPC della repository

Il pulsante `OPC` della finestra CF-LIBS esegue la One Point Calibration su uno standard noto. Come nella repository ufficiale di Palleschi, il calcolo OPC confronta lo standard e il risultato CF-LIBS sulla stessa base in `Number %` (percentuale atomica o molare). La finestra consente però di inserire la composizione nominale certificata direttamente come `Mass %`: pyLIBS la converte internamente in `Number %` usando le masse atomiche del database, senza modificare l'equazione OPC. Il file `.opc` è la curva correttiva ottenuta dalla procedura. I file `.STD` appartengono invece alla funzione separata `Standard Correction` e non devono essere caricati nella finestra OPC.

1. Selezionare `Apply After` e caricare la funzione strumentale fisica. La scelta non viene modificata dal caricamento del file. Se lo spettro era già stato corretto con `Apply Before`, pyLIBS ripristina automaticamente i dati sorgente grezzi e cancella le vecchie misure di fit, che devono essere ripetute.
2. Eseguire una sola volta il fit delle righe dello standard e completare CF-LIBS senza applicare SAC/IRSAC alla OPC.
3. Aprire `OPC`, scegliere `Nominal composition: Mass %` oppure `Number %` e inserire la composizione nominale nella base selezionata. Per esempio, uno standard Cd/Ni/Pb con `29,72 / 15,51 / 54,77 Mass %` viene convertito in circa `33,34 / 33,32 / 33,33 Number %`.
4. Premere `Compute OPC`: con input in massa pyLIBS calcola `x_i=(w_i/M_i)/sum(w/M)`, quindi usa sempre il rapporto `Number % nominale / Number % CF-LIBS` previsto dall'OPC.
5. Premere `Save Calibration...`. Il file `.opc` contiene un'intestazione di tracciabilità e, per ogni riga, lunghezza d'onda NIST, fattore composito, elemento e specie.
6. Per l'incognito, partire dallo spettro grezzo ed eseguire il fit una sola volta. Non applicare prima la funzione strumentale fisica.
7. Aprire `Calibration > Instrument Response`, scegliere `Load response files...` e selezionare soltanto il file `.opc`. pyLIBS imposta automaticamente `Apply After`.
8. Ricalcolare Saha-Boltzmann e CF-LIBS. La OPC divide le aree integrate; lo spettro, i profili e le aree fittate non vengono modificati.

Con `Apply After`, il file esportato contiene `risposta strumentale fisica × correzione OPC residua`. Per questo la `.opc` sostituisce le curve fisiche e non deve essere caricata insieme a esse. Una OPC è una calibrazione sparsa sulle righe analitiche: non deve essere applicata punto per punto allo spettro. Il programma blocca `Apply Before`, le miscele tra `.opc` e risposta fisica e la generazione di una OPC da aree già corrette prima del fit. L'autoassorbimento rimane una correzione separata.

OPC non è autonomo per campioni completamente incogniti e non deve essere usato per costringere una lega sconosciuta verso una composizione attesa.

### 15.8 Standard Correction (`.STD`)

`Analyse > Quantitative Analysis > Standard Correction...` corrisponde alla finestra `Unit31` presente nella repository e usa i file `.STD` con le `Mass %` correnti. `Refresh from CF-LIBS` ricarica la tabella; con doppio clic su un elemento si inserisce la percentuale in massa certificata. `Apply correction` usa il fattore `Mass % riferimento / Mass % misurata` e rinormalizza la tabella al 100%. `Save .STD` e `Load .STD` conservano o richiamano le percentuali di riferimento.

`Standard Correction` corregge soltanto la tabella corrente in `Mass %`. `OPC` è una procedura distinta: usa internamente `Number %` nominali per generare una curva applicabile, dopo integrazione, ad altri spettri acquisiti nelle stesse condizioni. Il selettore `Mass %` della finestra OPC è soltanto un ingresso assistito con conversione automatica. Entrambe richiedono uno standard noto e non fanno parte del percorso CF-LIBS senza calibrazione.

## 16. Spettro teorico

`Analyse > Quantitative Analysis > Theoretical Spectrum...` genera un confronto diagnostico dopo la decisione sull'autoassorbimento.

1. Completare Saha-Boltzmann e la valutazione SA.
2. Aprire la finestra dello spettro teorico.
3. Verificare la T di analisi, che è in sola lettura.
4. Impostare `Aki min`.
5. Scegliere il dominio: `Auto`, `Response-corrected` o `Detector counts`.
6. Inserire la FWHM strumentale globale misurata vicino a H-alpha, oppure 0 se ignota.
7. Premere `Calculate diagnostic spectrum`.

`Display-only least-squares scale` ridimensiona il modello per confronto visivo e non modifica CF-LIBS. Nel dominio del rivelatore la risposta strumentale viene applicata in avanti; nel dominio corretto si confrontano intensità radiometriche.

Lo spettro teorico è una verifica a valle. Non sostituisce IRSAC e non fornisce da solo una correzione quantitativa dell'autoassorbimento.

## 17. Report, salvataggio e batch

### 17.1 Salvataggio del grafico e dei dati

- `File > Save`: salva lo spettro principale come due colonne X/Y.
- `File > Save with Labels`: salva un CSV con colonne `wavelength`, `intensity` e `label`; l'etichetta è associata al campione X più vicino.
- `File > Print`: esporta il grafico in PNG o PDF.
- `Edit > Copy`: nella versione corrente informa di usare `File > Print`; non copia il grafico negli appunti.

### 17.2 Report CF-LIBS

`Show Report` genera una relazione HTML/testuale con metadati dello spettro, risposta, righe, fit, H-alpha, Saha-Boltzmann, parametri di plasma, autoassorbimento, robustezza e concentrazioni. Salvare il report insieme ai dati grezzi e alla configurazione sperimentale.

### 17.3 Batch Operations

Aprire `Utilities > Batch and Statistics > Batch Operations...`.

- `Add Files`: carica una lista di file; si possono scegliere tutti, dispari o pari.
- `MultiFit`: applica il listone corrente ai file e salva una cartella di lavoro Excel.
- `Join`: unisce i file a coppie e crea `.jnd`.
- `Average`: interpola su una griglia comune, calcola la media e crea `.avg`.
- `Calculate SD`: aggiunge la deviazione standard `.sd`.
- `Load List` e `Save List`: gestiscono elenchi `.lst` o storici `.fls`.
- `Convert Andor SIF to ASCII XY`: seleziona più file SIF e una cartella di destinazione, quindi crea un `.txt` senza intestazione per ogni file, con colonne tabulate di lunghezza d'onda e intensità e lo stesso nome base. Gli errori sono riportati per singolo file.
- `Convert CSV to ASCII XY`: seleziona più file CSV e una cartella di destinazione, quindi crea un `.txt` senza intestazione per ogni file, con colonne tabulate di lunghezza d'onda e intensità e lo stesso nome base. Gli errori sono riportati per singolo file.

Le medie tra acquisizioni sono corrette solo se i file appartengono alla stessa finestra e hanno condizioni sperimentali equivalenti. Non mediare insieme finestre centrali diverse.

### 17.4 Archivio minimo della misura

Per rendere l'analisi riproducibile conservare insieme:

- file grezzi di tutte le repliche e di tutte le finestre;
- file dark o descrizione delle colonne dark;
- curve di risposta radiometrica e data della loro misura;
- profili di calibrazione in lunghezza d'onda;
- listone analitico e versione del database atomico;
- file medio eventualmente prodotto, senza eliminare le repliche;
- report CF-LIBS, T, Ne, decisione SA e opzioni usate;
- identificativo del campione, energia laser, delay, gate, numero di colpi e data.

## 18. Controllo di qualità e ripetibilità

### 18.1 Checklist prima di accettare un risultato

1. Tutte le finestre richieste sono state caricate insieme.
2. Dark e risposta radiometrica sono corretti per ciascuna finestra.
3. La calibrazione lambda ha residui accettabili in ogni finestra.
4. Gli elementi presenti nei grafici sono esattamente quelli richiesti in Trace Lines.
5. Ogni riga analitica coincide con un massimo osservato.
6. I fit Voigt raggiungono la baseline e separano i doppi picchi.
7. Le repliche hanno CV accettabile.
8. Ne proviene dalla misura H-alpha pertinente.
9. La specie termometrica ha Delta Ek ampio e leave-one-out stabile.
10. La decisione SA è sostenuta dai dati.
11. CF-LIBS supera il controllo di qualità e l'audit di robustezza.
12. Number % o Mass % sono confrontate con la grandezza nominale corretta.

### 18.2 Campioni multielemento

Con più di due elementi controllare in particolare chiusura degli elementi selezionati, righe non osservate, stadi ionici dominanti non misurati e sensibilità alla rimozione di una riga. Un solo elemento sovrastimato altera tutte le percentuali normalizzate.

### 18.3 Confronti tra potenze laser

Non riusare automaticamente T e Ne tra potenze diverse. Cambiano grado di ionizzazione, allargamento Stark, autoassorbimento e rapporto segnale/fondo. Eseguire Ne, Saha-Boltzmann e diagnosi SA per ciascuna condizione.

### 18.4 Campione incognito, standard e serie

Per un campione completamente incognito usare il flusso CF-LIBS senza OPC o Standard Correction. Per uno standard certificato eseguire prima lo stesso flusso senza calibrazione, quindi valutare separatamente OPC o Standard Correction. Per una serie dello stesso campione e identiche condizioni si possono riusare listone, risposta e calibrazione per finestra; Ne può essere mantenuta solo con scelta esplicita e deve comunque essere verificata quando il plasma cambia.

<!-- pagebreak -->

## 19. Risoluzione dei problemi

| Problema | Causa probabile | Azione |
|---|---|---|
| Una riga appare dove non esiste una finestra acquisita | listone o marcatori non filtrati, sessione sporca | Clear Graph, ricaricare le finestre e verificare il report; la riga non deve entrare nei calcoli |
| Compare un elemento non richiesto | elemento tracciato in precedenza o assegnazione residua | Trace Lines, selezionare l'elemento e premere Canc; poi ricalcolare |
| Il picco evidente non viene selezionato | soglia, zoom o lista osservata incompleta | ingrandire la zona, Auto Fit > Add peak from graph, poi Trace Lines |
| Viene selezionata una riga senza picco | filtro `Only near selected peaks` disattivato | riattivarlo e cancellare l'assegnazione |
| Il programma sembra bloccato nel fit | ROI troppo ampia, troppi parametri o poche informazioni | premere Stop, restringere ROI, controllare componenti e riprovare |
| R2 = 1 con due punti | una retta passa esattamente per due punti | non considerarlo prova di buona temperatura; servono più righe e livelli |
| Le rette sono parallele in CF-LIBS | pendenza comune imposta da T | comportamento previsto dopo la scelta della T comune |
| Le rette sono parallele prima di IRSAC | vista quantitativa invece che diagnostica o stato non aggiornato | ricalcolare Saha-Boltzmann e verificare modalità/ruolo |
| Nessuna Ne disponibile | Hα non calcolata o cancellata | ripetere `Plasma Diagnostics > Electron Density from Hα...` oppure mantenere Ne solo per la stessa serie |
| Nessuna risposta per 656 nm | manca curva radiometrica H-alpha | usare il caricatore dedicato H-alpha; l'eccezione vale solo per Ne |
| Temperatura cambia molto dopo un nuovo fit | aree o ROI sono cambiate | confrontare centro, baseline, area e righe usate nel report |
| IRSAC cambia troppo le percentuali | fattori instabili, riga di riferimento inadatta o assenza di evidenze | rimuovere la correzione, leggere la diagnosi e controllare che l'equazione coincida con quella del foglio |
| Excel e programma differiscono | aree, lambda, Aki, gk, equazione o neutral fraction differenti | esportare il report e confrontare riga per riga gli input |
| Percentuali molari non coincidono con Mass % | confronto tra basi diverse | usare Number % per moli e Mass % per massa |
| CF-LIBS blocca la percentuale | controllo di qualità non superato | aprire Robustness e Show Report; correggere il dato, non la soglia |
| Clear Graph perde Ne | comportamento predefinito di sicurezza | attivare Keep active Ne soltanto per la stessa serie sperimentale |

## 20. Riferimento completo di menu e campi

### 20.1 File

| Comando | Scorciatoia | Funzione |
|---|---|---|
| Open... | Ctrl+O | apre lo spettro principale |
| Compare... | Ctrl+M | aggiunge uno spettro di confronto |
| Append... | Ctrl+A | carica più finestre/spettri |
| Save | Ctrl+S | salva lo spettro |
| Save with Labels | Ctrl+L | esporta CSV con etichette |
| Print | Ctrl+P | esporta il grafico in PNG o PDF |
| Exit | Ctrl+X | chiude il programma |

### 20.2 Edit

| Comando | Scorciatoia | Funzione |
|---|---|---|
| Copy | Ctrl+C | indica di esportare con File > Print; gli appunti non sono disponibili |
| Spectrum Management > Swap Spectra | Ctrl+W | scambia gli spettri di confronto |
| Spectrum Management > Show Active Spectra | Ctrl+Shift+A | gestisce gli spettri caricati |
| Spectrum Management > Clear Graph | Ctrl+Del | pulisce la misura corrente |
| Options... | Ctrl+Alt+O | apre la configurazione |
| Restore Factory Settings... | - | ripristina la configurazione distribuita |

### 20.3 View

| Comando | Scorciatoia | Funzione |
|---|---|---|
| Appearance > Background Color... | Ctrl+B | cambia lo sfondo del grafico |
| Appearance > X-axis Grid / Y-axis Grid | Ctrl+Alt+X / Y | attiva o disattiva le griglie degli assi |
| Appearance > Logarithmic X Axis / Y Axis | Ctrl+Alt+G / L | attiva o disattiva le scale logaritmiche |
| Zoom and Scale > Fit X Axis / Fit Y Axis | - | adatta un asse ai dati |
| Zoom and Scale > Expand X by 50% | F2 | amplia del 50% la vista sull'asse X |
| Zoom and Scale > Full Y Scale | F3 | adatta l'asse Y |
| Zoom and Scale > Show Full Spectrum | F4 | ripristina la vista completa |
| Window Layout > Save Window Positions | - | salva le posizioni delle finestre |
| Window Layout > Restore Window Positions | - | ripristina le posizioni salvate |

### 20.4 Utilities

| Comando | Scorciatoia | Funzione |
|---|---|---|
| Instrument Calibration > Instrument Response... | Ctrl+Alt+R | carica e controlla le risposte |
| Instrument Calibration > Apply Instrument Response | - | applica il rapporto segnale/risposta |
| Instrument Calibration > Wavelength Calibration... | - | calibra ogni finestra |
| Instrument Calibration > Manual Wavelength Shift... | Ctrl+F1 | applica uno spostamento scelto |
| Signal Processing > Intensity Offset... | Ctrl+F2 | modifica il livello verticale |
| Signal Processing > Smooth Spectrum | Ctrl+F3 | leviga lo spettro visualizzato |
| Signal Processing > Convert nm to Å | Ctrl+F4 | converte i nanometri in ångström |
| Batch and Statistics > Batch Operations... | - | esegue elaborazioni batch, medie, unioni e MultiFit |
| Analytical Line Lists > Import Lines for Current Analysis... | Ctrl+F5 | importa la lista corrente |
| Analytical Line Lists > Main Analytical-Line Library... | Ctrl+F6 | gestisce il listone e le righe operative |
| Analytical Line Lists > Selected-Line Summary | Ctrl+F7 | riepiloga le righe selezionate |
| Analytical Line Lists > Clear Selected Lines | - | svuota le righe correnti |
| Batch and Statistics > Statistics | Shift+Ctrl+F4 | mostra le statistiche X/Y |
| Go To Wavelength... | Ctrl+F9 | centra una lunghezza d'onda |

### 20.5 Analyse

| Comando | Funzione |
|---|---|
| Peak and Line Detection > Find Peaks | trova i massimi osservati |
| Peak and Line Detection > Trace Lines... | identifica gli elementi richiesti |
| Spectral Fitting > Manual Fit... | esegue un fit Voigt controllato manualmente |
| Spectral Fitting > Automatic Fit... | seleziona e adatta automaticamente i profili Voigt |
| Plasma Diagnostics > Electron Density from Hα... | calcola la densità elettronica |
| Plasma Diagnostics > Saha-Boltzmann Plot... | calcola la temperatura e gli stadi di ionizzazione |
| Plasma Diagnostics > Self-Absorption / IRSAC... | diagnostica e corregge l'autoassorbimento |
| Plasma Diagnostics > SAC Factors... | apre la finestra storica dei fattori SAC |
| Quantitative Analysis > CF-LIBS... | calcola concentrazioni e robustezza |
| Quantitative Analysis > Theoretical Spectrum... | genera il confronto teorico diagnostico |
| Quantitative Analysis > Standard Correction... | applica la correzione con uno standard esterno |

`SAC Factors` e `Standard Correction` sono strumenti specialistici o storici. Nel flusso ordinario usare `Self-Absorption / IRSAC`; applicare la correzione con standard solo quando esiste uno standard appropriato e documentato.

### 20.6 Help

| Comando | Scorciatoia | Funzione |
|---|---|---|
| User Manual > Italiano / English | - | sceglie e apre il manuale nella lingua desiderata |
| About pyLIBS... | Ctrl+T | mostra versione, crediti e informazioni sul programma |

## 21. Formule e glossario

### 21.1 Ordinata Boltzmann e convenzione d'intensità

Con una risposta in energia il programma usa:

`y = ln[(1e-9/(h*c)) * I_corr * lambda_NIST,nm / |Aki * gk|]`

La costante `1e-9/(h*c) = 5.0341166e15 J^-1 nm^-1` e `lambda_NIST,nm` convertono l'energia radiativa in un numero equivalente di fotoni. Con una risposta già espressa in fotoni o conteggi corretti, il programma usa invece la convenzione originale di pyLIBS:

`y = ln[I_corr / |Aki * gk|]`

In entrambe le formule `I_corr` è l'area Voigt corretta con la risposta strumentale, `Aki` è espresso in s^-1 e `gk` è il peso statistico del livello superiore. Una costante moltiplicativa comune a tutte le righe trasla verticalmente il grafico ma non ne cambia la pendenza; il fattore dipendente da `lambda`, invece, deve essere applicato una sola volta e coerentemente con il dominio della risposta strumentale.

La relazione lineare è:

`y = intercetta - Ek/kT`

per cui la pendenza è `m = -1/kT`.

### 21.2 Saha-Eggert

Il rapporto tra popolazione ionizzata e neutra dipende da T, Ne, energia di ionizzazione e funzioni di partizione. pyLIBS lo calcola automaticamente per ciascun elemento e lo usa per ricostruire la popolazione totale.

### 21.3 Termini

| Termine | Significato operativo |
|---|---|
| Aki | probabilità di transizione in s^-1 |
| Ei / Ek | energia inferiore / superiore |
| gi / gk | pesi statistici inferiore / superiore |
| kT | temperatura elettronica espressa in eV |
| Ne | densità elettronica in cm^-3 |
| FWHM | larghezza a metà altezza |
| Voigt | convoluzione di contributi gaussiano e lorentziano |
| ROI | intervallo usato per fit e integrazione |
| IRSAC | correzione iterativa dell'autoassorbimento |
| SA | self-absorption, autoassorbimento |
| LOO | leave-one-out, ricalcolo eliminando una riga |
| CV | coefficiente di variazione |
| OPC | One-Point Calibration con standard noto |
