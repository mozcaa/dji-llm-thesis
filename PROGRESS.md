

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

### Next steps
- Completare le modifiche al frontend JavaScript, aggiungendo alla sidebar i campi per quota e velocità di ciascun waypoint e collegandoli agli endpoint Flask.
- Commentare il frontend.
- Valutare un refactoring mirato del frontend per migliorarne leggibilità e organizzazione.
- Testare il funzionamento complessivo del planner, verificando la creazione e modifica dei waypoint, Undo/Redo e l'esportazione e reimportazione dei KMZ.
- Eventualmente trovare un modo per visualizzare nomi di città e confini degli Stati sulla mappa.
- Iniziare l'integrazione di un LLM locale per generare missioni a partire da istruzioni in linguaggio naturale.
