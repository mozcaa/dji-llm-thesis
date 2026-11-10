

### Diario

- 30/10/2026
- Analizzato (`mission.py`).
- Analizzato (`parser_xml.py`).
- Analizzato (`server.py`).
- Prima analisi (`script.js`).
- Commentato i 3 file .py

- 03/11/2026
- Modificato missione.py in modo da avere quota e velocità non globali, aggiornato il tempo totale considerando anche la distanza verticale e quindi calcolando la distanza totale (assunta v costante). Per la velocità da waypoint a waypoint è stato inserito l' attributo speed ad ogni waypoint, indica la velocità nel tratto che collega il waypoint con quello successivo.
- Adattato server.py per quota e velocità diverse ad ogni tratto.
- Adattato parser_xml.py per quota e velocità diverse ad ogni tratto.
- Appuntate come commenti nel codice le modifiche individuate fino ad ora in script.js per adattarlo a quota e velocità diverse. Alcuni commenti sono ancora provvisori e serviranno come riferimento per il lavoro successivo.

- 06/11/2026
- Modificato script.js per gestire quota e velocità individuali dei waypoint, aggiungendo input e relative chiamate POST.
- Aggiornato server.py per mantenere payloadIndex globale.
- Revisionato il frontend e corretti alcuni errori.

- 08/11/2026
- Completato il primo prototipo del planner, sistemando il CSS.
- Effettuato un leggero refactoring di script.js, riorganizzando le varie componenti e aggiungendo commenti esplicativi.
- Testate le principali funzionalità del planner (importazione ed esportazione KMZ, Undo/Redo, aggiunta e rimozione di waypoint e azioni).
- Creato il primo prototipo di validator.py per verificare i parametri delle azioni. (NON INTEGRATO ANCORA)

- 10/11/2026
- Completata la prima versione di validator.py, con controlli su coordinate, quota, velocità, indici dei waypoint, sei azioni supportate e parametro globale payloadIndex.
- Aggiunti messaggi di errore specifici per valori non validi, parametri mancanti e azioni non supportate.
- Integrata la validazione in cinque route Flask: add_waypoint, add_waypoint_at, update_waypoint, update_waypoint_speed e update_waypoint_quote.
- Implementato il rifiuto delle richieste non valide prima di modificare la missione o registrare lo stato Undo.

### Next steps
- Completare l'integrazione del validatore in server.py per rimozione waypoint, gestione delle azioni e parametri globali.
- Migliorare il frontend con controlli sugli input e visualizzazione dei messaggi di errore.
- Testare le richieste valide e non valide.
- Verificare la compatibilità dei KMZ generati con l'app Android DJI e il simulatore.
- Valutare la possibilità di visualizzare nomi delle città e confini degli Stati sulla mappa.
- Iniziare l'integrazione di un LLM locale per generare missioni a partire da istruzioni in linguaggio naturale.