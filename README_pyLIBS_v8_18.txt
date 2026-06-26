pyLIBS v8.18

Modifica rispetto a v8.17:
- Il template mantiene la stessa struttura/colonne della v8.17.
- La ricerca automatica dei picchi aggiorna il template esistente invece di ricrearlo da zero.
- Le righe già presenti vengono aggiornate se coincidono in lunghezza d'onda entro la tolleranza usata dal programma.
- Le nuove righe vengono aggiunte al template già presente.
- I dati già acquisiti da identificazione e fit Voigt vengono preservati quando si aggiorna il template con una nuova ricerca.
- Il fit Voigt continua a scrivere i parametri nelle righe template corrispondenti.

File principale:
pyLIBS.py
