from datetime import date, timedelta, time
from html import escape
from io import BytesIO

import requests
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import (
    Paragraph,
    Image as ReportImage,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
import io
from PIL import Image
try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
except ImportError:
    pass

CHECKLIST_DATA = {
    "ESC Inspection Checklist": [
        "Recinzione (SE- 1) / Perimeter control: silt fence",
        "Pulizia delle strade (SE-7) / Street Sweeping and Vacuuming",
        "Protezione tombini (SE-10) / Storm drain inlet protection",
        "Entrata-uscita stabilizzata (TC-1) / Stabilized Construction Entry-Exit",
        "Piste di cantiere stabilizzata (TC-2) / Stabilized Construction roadway",
        "Lavaggio ruote (TC-3) / Tire wash",
        "Scarico e stoccaggio materiali (WM-1) / Material delivery and storage",
        "Gestione dei cumuli (WM-3) / Stockpile management",
        "Gestione dei rifiuti solidi (WM-5) / Solid waste management",
        "Lavaggio del calcestruzzo (WM-8) / Concrete waste management",
        "Rifornimento di veicoli e mezzi (NS-9) / Vehicle and equipment fueling"
    ],
    "CDWM Inspection Checklist": [
        "Identificazione di un’area dedicata all’interno del cantiere destinata allo stoccaggio e separazione dei rifiuti di costruzione. / Identification of a dedicated area inside the construction site for the storage and separation of construction waste",
        "I rifiuti pericolosi sono stoccati separatamente e opportunamente segnalati. / Hazardous waste is stored separately and properly reported.",
        "I cassoni/ cumuli omogeni dei rifiuti sono opportunamente contrassegnati da cartellonistica indicante il codice CER. / Homogeneous waste bins are properly identified by signage indicating the CER code.",
        "L’area di raccolta dei rifiuti è mantenuta pulita e ordinata. / Waste collection area is properly kept clean and organized.",
        "Cestini per la raccolta differenziata dei rifiuti prodotti dai lavoratori sono presenti in sito. / Bins for recycling waste produced by workers are present on site."
    ],
    "IAQ Inspection Checklist": [
        "I prodotti chimici sono stoccati in contenitori sigillati e chiaramente identificati. / Chemicals are stored in sealed and clearly identified containers",
        "I prodotti chimici sono stoccati in aree ventilate e/o a diretto contatto con l’esterno. / Chemicals are stored in naturally ventilated areas and/or directly linked to outside areas.",
        "I materiali sono forniti in cantiere con proprio imballaggio. / Building materials are delivered on site with proper packaging.",
        "I materiali isolanti, cartongessi, etc. sono stoccati in luoghi asciutti, coperti e sollevati da terra ai fini di proteggerli dall’umidità e sporcizia. / Porous and absorbing materials (insulation, plaster boards,..) are stored in dry covered areas, packaged and raised up from the floor to protect them from dirt and moisture.",
        "Utilizzo di appropriate procedure anti-polvere. / Procedures to avoid dust are implemented.",
        "Delimitazione aree per lavorazioni che producono polvere. / Delimitation of area for activities that produce dust.",
        "Divieto di fumo correttamente indicato. / Smoking ban is clearly indicated.",
        "Aree fumatori delimitate. / Bounded smoking areas.",
        "Le apparecchiature degli impianti HVAC sono consegnate sigillate con i propri imballaggi. / HVAC systems equipment and components are delivered on site with proper packaging.",
        "Le apparecchiature ed i canali sono debitamente stoccati prima dell'installazione in modo da prevenire contaminazione da polveri e umidità. / HVAC systems equipment and components (ducts) are properly stored on site before installation to prevent dust and moisture contamination.",
        "Le apparecchiature ed i canali sono debitamente sigillati con plastica o simile dopo l'installazione a prevenire contaminazione da polveri e umidità. / HVAC systems equipment and components (ducts) are properly sealed with taped plastic after installation to prevent dust and moisture contamination."
    ]
}

STATUSES = ("Da verificare / TBD", "Sì / Yes", "No", "N/A")
STATUS_COLORS = {
    "Da verificare / TBD": colors.HexColor("#FFF0C2"),
    "Sì / Yes": colors.HexColor("#DDF3E5"),
    "No": colors.HexColor("#FCE1DF"),
    "N/A": colors.HexColor("#E9EDF2"),
}

INSPECTION_TYPES = (
    "Regolare (mensile) / Regular (monthly)",
    "Prima di un evento meteorico / Pre-storm event",
    "Durante un evento meteorico / During Storm Event",
    "Dopo un evento meteorico / Post-storm event"
)

WEATHER_CODES = {
    0: "Sereno / Clear sky",
    1: "Prevalentemente sereno / Mainly clear",
    2: "Parzialmente nuvoloso / Partly cloudy",
    3: "Coperto / Overcast",
    45: "Nebbia / Fog",
    48: "Nebbia con brina / Depositing rime fog",
    51: "Pioviggine leggera / Light drizzle",
    53: "Pioviggine moderata / Moderate drizzle",
    55: "Pioviggine intensa / Dense drizzle",
    56: "Pioviggine gelata leggera / Light freezing drizzle",
    57: "Pioviggine gelata intensa / Dense freezing drizzle",
    61: "Pioggia debole / Slight rain",
    63: "Pioggia moderata / Moderate rain",
    65: "Pioggia intensa / Heavy rain",
    66: "Pioggia gelata debole / Light freezing rain",
    67: "Pioggia gelata intensa / Heavy freezing rain",
    71: "Neve debole / Slight snow fall",
    73: "Neve moderata / Moderate snow fall",
    75: "Neve intensa / Heavy snow fall",
    77: "Granuli di neve / Snow grains",
    80: "Rovesci deboli / Slight rain showers",
    81: "Rovesci moderati / Moderate rain showers",
    82: "Rovesci violenti / Violent rain showers",
    85: "Rovesci deboli di neve / Slight snow showers",
    86: "Rovesci intensi di neve / Heavy snow showers",
    95: "Temporale / Thunderstorm",
    96: "Temporale con grandine debole / Thunderstorm with slight hail",
    99: "Temporale con grandine intensa / Thunderstorm with heavy hail",
}
RECENT_HISTORY_DAYS = 92


class WeatherLookupError(Exception):
    pass


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_weather(address: str, inspection_day: str) -> dict:
    selected_date = date.fromisoformat(inspection_day)
    today = date.today()
    if selected_date > today + timedelta(days=15):
        raise WeatherLookupError(
            "Le previsioni sono disponibili in una finestra di 16 giorni, incluso oggi. / Forecasts are available in a 16-day window, including today."
        )
    if selected_date < today - timedelta(days=RECENT_HISTORY_DAYS):
        weather_endpoint = "https://archive-api.open-meteo.com/v1/archive"
        weather_dates = {
            "start_date": inspection_day,
            "end_date": inspection_day,
        }
        data_source = "archivio climatico / climate archive"
    elif selected_date < today:
        weather_endpoint = "https://api.open-meteo.com/v1/forecast"
        weather_dates = {
            "past_days": (today - selected_date).days,
            "forecast_days": 1,
        }
        data_source = "dati meteo recenti / recent weather data"
    else:
        weather_endpoint = "https://api.open-meteo.com/v1/forecast"
        weather_dates = {
            "start_date": inspection_day,
            "end_date": inspection_day,
        }
        data_source = "previsioni meteo / weather forecast"

    try:
        geocoding_response = requests.get(
            "https://geocoding-api.open-meteo.com/v1/search",
            params={"name": address, "count": 1, "language": "it", "format": "json"},
            timeout=10,
        )
        geocoding_response.raise_for_status()
        locations = geocoding_response.json().get("results", [])
        if not locations:
            raise WeatherLookupError(
                "Località non trovata. Prova a inserire città e provincia. / Location not found. Try entering city and province."
            )

        location = locations[0]
        weather_response = requests.get(
            weather_endpoint,
            params={
                "latitude": location["latitude"],
                "longitude": location["longitude"],
                **weather_dates,
                "daily": (
                    "weather_code,temperature_2m_max,temperature_2m_min,"
                    "precipitation_sum,wind_speed_10m_max"
                ),
                "timezone": "auto",
            },
            timeout=15,
        )
        weather_response.raise_for_status()
        daily = weather_response.json().get("daily", {})
    except WeatherLookupError:
        raise
    except (requests.RequestException, ValueError, KeyError) as error:
        raise WeatherLookupError(
            "Non è stato possibile recuperare i dati meteo. Controlla la connessione e riprova. / Weather data could not be retrieved. Check your connection and try again."
        ) from error

    try:
        day_index = daily.get("time", []).index(inspection_day)
    except ValueError as error:
        raise WeatherLookupError(
            "Il servizio meteo non ha dati disponibili per la data selezionata. / The weather service has no data available for the selected date."
        ) from error

    def daily_value(field: str):
        values = daily.get(field, [])
        return values[day_index] if