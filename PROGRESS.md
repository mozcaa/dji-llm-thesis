

### Cose fatte
- Analizzato (`mission.py`).
- Analizzato (`parser_xml.py`).
- Analizzato (`server.py`).
- Prima analisi (`script.js`).
- Commentato i 3 file .py

- Modificato missione.py in modo da avere quota e velocità non globali, aggiornato il tempo totale considerando anche la distanza verticale e quindi calcolando la distanza totale (assunta v costante). Per la velocità da waypoint a waypoint è stato inserito l' attributo speed ad ogni waypoint, indica la velocità nel tratto che collega il waypoint con quello successivo.
- Adattato server.py per quota e velocità diverse ad ogni tratto.
- Adattato parser_xml.py per quota e velocità diverse ad ogni tratto.
- Appuntate come commenti nel codice le modifiche individuate fino ad ora in script.js per adattarlo a quota e velocità diverse. Alcuni commenti sono ancora provvisori e serviranno come riferimento per il lavoro successivo.

- Modificato script.js per gestire quota e velocità individuali dei waypoint, aggiungendo input e relative chiamate POST.
- Aggiornato server.py per mantenere payloadIndex globale.
- Revisionato il frontend e corretti alcuni errori.

- 11/08/2026
- Completato il primo prototipo del planner, sistemando il CSS.
- Effettuato un leggero refactoring di script.js, riorganizzando le varie componenti e aggiungendo commenti esplicativi.
- Testate le principali funzionalità del planner (importazione ed esportazione KMZ, Undo/Redo, aggiunta e rimozione di waypoint e azioni).
- Creato il primo prototipo di validator.py per verificare i parametri delle azioni. (NON INTEGRATO ANCORA)


### Next steps
- Integrare e testare il validatore nel backend Flask.
- Rendere il frontend più robusto, utilizzando intervalli numerici e menu a tendina nei form delle azioni, così da limitare l'inserimento di valori non validi.
- Verificare la compatibilità dei KMZ generati con l'app Android DJI e il simulatore.
- Valutare la possibilità di visualizzare nomi delle città e confini degli Stati sulla mappa.
- Iniziare l'integrazione di un LLM locale per generare missioni a partire da istruzioni in linguaggio naturale.