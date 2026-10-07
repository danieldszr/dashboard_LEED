# Checklist ispezione di cantiere LEED

Dashboard Streamlit in italiano per compilare verifiche di cantiere, aggiungere note, evidenze e foto, recuperare automaticamente il meteo e scaricare la checklist in PDF.

> La checklist è uno strumento operativo generale: non sostituisce i requisiti ufficiali LEED, il piano di progetto o le indicazioni del LEED AP. Adattare le domande alla versione LEED e ai crediti perseguiti.

## Avvio locale

Richiede Python 3.10 o successivo.

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
streamlit run home.py
```

Aprire l'indirizzo locale mostrato da Streamlit, normalmente `http://localhost:8501`.

## Pubblicazione online con Streamlit Community Cloud

1. Pubblicare questo progetto in un repository GitHub.
2. In Streamlit Community Cloud creare una nuova app e selezionare il repository e il branch.
3. Impostare `home.py` come file principale.
4. Distribuire: Cloud installerà le dipendenze indicate in `requirements.txt`.

Non sono necessari segreti o servizi esterni. Per aggiornare le dipendenze, modificare `requirements.txt` e ridistribuire l'app.

## Meteo automatico

Inserendo un indirizzo e selezionando la data, l'app geocodifica la località e recupera automaticamente condizioni giornaliere, temperature, precipitazioni e vento da [Open-Meteo](https://open-meteo.com/). Non serve una chiave API; è necessaria una connessione Internet. Per date passate recenti (fino a 92 giorni) usa il servizio meteo con dati retrospettivi; per le date precedenti usa l'archivio storico. Le previsioni future coprono una finestra di 16 giorni incluso oggi. Le osservazioni retrospettive sono stime del modello, non misure ufficiali della stazione locale. Il PDF riporta l'attribuzione della fonte Open-Meteo (CC BY 4.0).

## Foto nelle verifiche

Ogni domanda accetta più foto in formato JPG o PNG. Le immagini sono mostrate direttamente sotto la domanda e inserite nello stesso punto nella checklist PDF, separate dal campo note. Ogni immagine può avere dimensione massima di 10 MB.
