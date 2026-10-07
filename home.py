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
    """Erro