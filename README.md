# Checklist ispezione di cantiere LEED

Dashboard Streamlit in italiano per compilare verifiche di cantiere, aggiungere note ed evidenze e scaricare la checklist in PDF.

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
