from datetime import date, timedelta, time
from html import escape
from io import BytesIO
from pathlib import Path

import requests
import streamlit as st
from reportlab.lib import colors
from reportlab.lib.enums import TA_CENTER
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib.utils import ImageReader
from reportlab.platypus import (
    Paragraph,
    Image as ReportImage,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)
import io
from PIL import Image, ImageDraw, ImageFont, ImageOps

try:
    from pillow_heif import register_heif_opener
    register_heif_opener()
    HEIF_SUPPORTED = True
except ImportError:
    HEIF_SUPPORTED = False

BASE_DIR = Path(__file__).resolve().parent
LOGO_PATH = BASE_DIR / "GET-Consulting-LOGO.jpg"

ADDITIONAL_SECTION_TITLE = "Misure addizionali / Additional measures (CAM dm 23.06.2022 n.256 – criteri 2.6)"

CHECKLIST_DATA = {
    "ESC Inspection Checklist": [
        "Recinzione (SE- 1) / Perimeter control: silt fence",
        "Pulizia delle strade (SE-7) / Street Sweeping and Vacuuming",
        "Protezione tombini (SE-10) / Storm drain inlet protection",
        "Entrata-uscita stabilizzata (TC-1) / Stabilized Construction Entry-Exit",
        "Piste di cantiere stabilizzata (TC-2) / Stabilized Construction roadway",
        "Lavaggio ruote (TC-3) / Tire wash",
        "Controllo delle polveri (EC-3) / Dust control",
        "Scarico e stoccaggio materiali (WM-1) / Material delivery and storage",
        "Gestione dei cumuli (WM-3) / Stockpile management",
        "Gestione dei rifiuti solidi (WM-5) / Solid waste management",
        "Lavaggio del calcestruzzo (WM-8) / Concrete waste management",
        "Rifornimento di veicoli e mezzi (NS-9) / Vehicle and equipment fueling",
        "Protezione della vegetazione esistente (EC-2) / Preservation of Existing Vegetation",
    ],
    ADDITIONAL_SECTION_TITLE: [
        "Uso efficiente dell’energia in cantiere (CAM 2.6.1) / Efficient use on energy on construction site",
        "Abbattimento delle emissioni gassose delle macchine (CAM 2.6.1) / Reduction of gaseous emissions from machines",
        "Risparmio idrico (CAM 2.6.1) / Water saving",
        "Conservazione dello strato superficiale del terreno (CAM 2.6.2) / Preservation of the soil surface layer",
        "Rinterri e riempimenti (CAM 2.6.3) / Backfills and fills",
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

GREEN_FILL = colors.HexColor("#DDF3E5")
RED_FILL = colors.HexColor("#FCE1DF")
HEADER_TEAL = colors.HexColor("#4FA8BA")

BMP_INSTALLED_COLORS = {
    "Sì / Yes": GREEN_FILL,
    "No": RED_FILL,
}

BMP_MAINTENANCE_COLORS = {
    "Sì / Yes": RED_FILL,
    "No": GREEN_FILL,
}

INSPECTORS_DIRECTORY = {
    "Alessandra Viotti": "alessandra.viotti@get-consulting.it",
    "Andrea Pizza": "andrea.pizza@get-consulting.it",
    "Daniel Suarez": "daniel.suarez@get-consulting.it",
    "Daniele Guglielmino": "daniele.guglielmino@get-consulting.it",
    "Dario Prando": "dario.prando@get-consulting.it",
    "Davide Borello": "davide.borello@get-consulting.it",
    "Elia Lupo": "elia.lupo@get-consulting.it",
    "Elisa Sirombo": "elisa.sirombo@get-consulting.it",
    "Gaetana Battaglia": "gaetana.battaglia@get-consulting.it",
    "Giulia Tarantino": "giulia.tarantino@get-consulting.it",
    "Ilaria Colombo": "ilaria.colombo@get-consulting.it",
    "Laura Arteaga Albarello": "laura.arteaga@get-consulting.it",
    "Laura Gualdron": "laura.gualdron@get-consulting.it",
    "Lina Garcia": "lina.garcia@get-consulting.it",
    "Marco Bonanno": "marco.bonanno@get-consulting.it",
    "Simone Massini": "simone.massini@get-consulting.it",
    "Sofia Mori": "sofia.mori@get-consulting.it",
    "Staff GET": "staff@get-consulting.it",
    "Stefano Esposito": "stefano.esposito@get-consulting.it",
}

INSPECTOR_TITLES = (
    "LEED AP",
    "LEED GA",
    "Sustainability consultant",
)

CONSTRUCTION_PHASES = (
    "Allestimento cantiere / Site Mobilization",
    "Demolizioni / Demolition",
    "Scavi e movimenti terra / Excavation & Earthworks",
    "Strutture e fondazioni / Foundations & Structure",
    "Involucro edilizio / Building Envelope",
    "Impianti (MEP) / MEP Rough-in",
    "Finiture interne / Interior Finishes",
    "Sistemazioni esterne / Site Works & Landscaping",
    "Collaudi e pre-consegna / Commissioning & Handover",
)

INSPECTION_TYPES = (
    "Regolare (mensile) / Regular (monthly)",
    "Prima di un evento meteorico / Pre-storm event",
    "Durante un evento meteorico / During Storm Event",
    "Dopo un evento meteorico / Post-storm event",
    "Altro / Other"
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


def _sync_inspector_emails():
    """Aggiorna automaticamente le email in base agli ispettori selezionati."""
    selected = st.session_state.get("inspectors", [])
    emails = [INSPECTORS_DIRECTORY[name] for name in selected if name in INSPECTORS_DIRECTORY]
    st.session_state["inspector_email"] = ", ".join(emails)


def _sync_na_maintenance(question_key: str):
    """Imposta automaticamente la manutenzione su N/A se BMP installata è N/A."""
    if st.session_state.get(f"{question_key}_bmp_inst") == "N/A":
        st.session_state[f"{question_key}_bmp_maint"] = "N/A"


def _load_font(size: int):
    for font_name in (
        "DejaVuSans-Bold.ttf",
        "DejaVuSans.ttf",
        "LiberationSans-Bold.ttf",
        "LiberationSans-Regular.ttf",
        "Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
        "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    ):
        try:
            return ImageFont.truetype(font_name, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


def watermark_photo(photo_bytes: bytes, project_name: str, insp_date: str, place: str) -> bytes:
    """Applica una didascalia proporzionata e ben leggibile in basso a destra con commessa, data e luogo."""
    img = Image.open(io.BytesIO(photo_bytes))
    try:
        img = ImageOps.exif_transpose(img)
    except Exception:
        pass
    img = img.convert("RGBA")

    lines = [p.strip() for p in (project_name, insp_date, place) if p and p.strip()]
    if not lines:
        out_io = io.BytesIO()
        img.convert("RGB").save(out_io, format="JPEG", quality=90)
        return out_io.getvalue()

    width, height = img.size

    overlay = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay)

    # Dimensione bilanciata: 3.5% del lato corto (minimo 42px)
    font_size = max(42, int(min(width, height) * 0.035))
    font = _load_font(font_size)

    margin = max(16, int(min(width, height) * 0.02))
    pad_x = max(18, int(font_size * 0.35))
    pad_y = max(12, int(font_size * 0.25))
    line_spacing = max(8, int(font_size * 0.18))
    max_box_width = int(width * 0.85)
    max_box_height = int(height * 0.35)

    def measure_lines(fnt, l_sp):
        bboxes = [draw.textbbox((0, 0), line, font=fnt) for line in lines]
        max_w = max(b[2] - b[0] for b in bboxes)
        heights = [b[3] - b[1] for b in bboxes]
        total_h = sum(heights) + l_sp * (len(lines) - 1)
        return bboxes, max_w, heights, total_h

    bboxes, text_w, line_heights, text_h = measure_lines(font, line_spacing)

    # Scala proporzionalmente se troppo largo o alto
    scale_w = (max_box_width - 2 * pad_x) / text_w if (text_w + 2 * pad_x > max_box_width and text_w > 0) else 1.0
    scale_h = (max_box_height - 2 * pad_y) / text_h if (text_h + 2 * pad_y > max_box_height and text_h > 0) else 1.0
    scale_ratio = min(scale_w, scale_h)

    if scale_ratio < 1.0:
        font_size = max(20, int(font_size * scale_ratio))
        font = _load_font(font_size)
        pad_x = max(12, int(font_size * 0.35))
        pad_y = max(8, int(font_size * 0.25))
        line_spacing = max(6, int(font_size * 0.18))
        bboxes, text_w, line_heights, text_h = measure_lines(font, line_spacing)

    box_right = width - margin
    box_bottom = height - margin
    box_left = max(margin, box_right - text_w - 2 * pad_x)
    box_top = max(margin, box_bottom - text_h - 2 * pad_y)

    draw.rectangle(
        [box_left, box_top, box_right, box_bottom],
        fill=(23, 59, 53, 220),
    )

    current_y = box_top + pad_y
    for line, bbox, lh in zip(lines, bboxes, line_heights):
        line_w = bbox[2] - bbox[0]
        text_x = box_right - pad_x - line_w - bbox[0]
        draw.text(
            (text_x, current_y - bbox[1]),
            line,
            font=font,
            fill=(255, 255, 255, 255),
        )
        current_y += lh + line_spacing

    watermarked = Image.alpha_composite(img, overlay).convert("RGB")
    out_io = io.BytesIO()
    watermarked.save(out_io, format="JPEG", quality=90)
    return out_io.getvalue()


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
        return values[day_index] if day_index < len(values) else None

    code = daily_value("weather_code")
    description = WEATHER_CODES.get(code, f"Condizioni variabili / Variable conditions (code {code})")
    location_name = ", ".join(
        part for part in (location.get("name"), location.get("admin1"), location.get("country")) if part
    )
    max_temp = daily_value("temperature_2m_max")
    min_temp = daily_value("temperature_2m_min")
    precipitation = daily_value("precipitation_sum")
    max_wind = daily_value("wind_speed_10m_max")

    def formatted(value, suffix: str) -> str:
        return f"{value:g}{suffix}" if isinstance(value, (int, float)) else "n/d"

    summary = (
        f"{location_name} — {description}; "
        f"max {formatted(max_temp, ' °C')}, min {formatted(min_temp, ' °C')}; "
        f"precipitazioni / precipitation {formatted(precipitation, ' mm')}; "
        f"vento / wind max {formatted(max_wind, ' km/h')}."
    )
    return {
        "summary": summary,
        "location": location_name,
        "description": description,
        "data_source": data_source,
        "max_temp": max_temp,
        "min_temp": min_temp,
        "precipitation": precipitation,
        "max_wind": max_wind,
    }


def format_bilingual(text: object, bold_all: bool = False) -> str:
    """Formatta i testi bilingue rendendo in corsivo (<i>) la parte in inglese."""
    s = str(text)
    if s == "Sì / Yes":
        res = "Sì / <i>Yes</i>"
    elif s.startswith("Sì / Yes:"):
        res = f"Sì / <i>Yes:</i> {escape(s[9:].strip())}"
    elif " / " in s:
        it_part, en_part = s.split(" / ", 1)
        res = f"{escape(it_part)} / <i>{escape(en_part)}</i>"
    else:
        res = escape(s)
    res = res.replace("\n", "<br/>")
    return f"<b>{res}</b>" if bold_all else res


def make_pdf(metadata: dict, answers: dict, active_checklists: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=22 * mm,
        bottomMargin=18 * mm,
        title="Ispezione di cantiere LEED / LEED Construction Site Inspection",
        author="Dashboard checklist LEED",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ChecklistTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=16,
            leading=20,
            alignment=TA_CENTER,
            textColor=colors.HexColor("#173B35"),
            spaceAfter=5 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SectionHeading",
            parent=styles["Heading2"],
            fontSize=11,
            leading=14,
            textColor=colors.HexColor("#173B35"),
            spaceBefore=5 * mm,
            spaceAfter=2 * mm,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallCell",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
            spaceAfter=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="SmallCellCenter",
            parent=styles["BodyText"],
            fontSize=8,
            leading=10,
            spaceAfter=0,
            alignment=TA_CENTER,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeader",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            spaceAfter=0,
        )
    )
    styles.add(
        ParagraphStyle(
            name="TableHeaderCenter",
            parent=styles["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=8,
            leading=10,
            textColor=colors.white,
            alignment=TA_CENTER,
            spaceAfter=0,
        )
    )

    def para(value: object, style="SmallCell", bilingual: bool = True, bold: bool = False) -> Paragraph:
        if bilingual:
            formatted = format_bilingual(value, bold_all=bold)
        else:
            escaped = escape(str(value)).replace("\n", "<br/>")
            formatted = f"<b>{escaped}</b>" if bold else escaped
        return Paragraph(formatted, styles[style])

    story = [
        Paragraph(
            "Ispezione di cantiere LEED / <i>LEED Construction Site Inspection</i>",
            styles["ChecklistTitle"],
        ),
        Spacer(1, 4 * mm),
    ]

    metadata_rows = [
        [para("Commessa / Project"), para(metadata["project"], bilingual=False), para("Data ispezione / Date"), para(metadata["inspection_date"], bilingual=False)],
        [para("Ora / Time (Start-End)"), para(metadata["time_range"], bilingual=False), para("Ispettore / Inspector"), para(metadata["inspector"], bilingual=False)],
        [para("Titolo(i) / Title(s)"), para(metadata["inspector_titles"], bilingual=False), para("Email ispettore / Insp. Email"), para(metadata["inspector_email"], bilingual=False)],
        [para("Fase costr. / Phase"), para(metadata["phase"]), para("Tipo Ispez. / Insp. Type"), para(metadata["inspection_type"])],
        [para("Indirizzo / Address"), para(metadata["address"], bilingual=False), "", ""],
        [para("Meteo / Weather"), para(metadata["weather"]), "", ""],
    ]
    metadata_table = Table(metadata_rows, colWidths=[31 * mm, 54 * mm, 31 * mm, 54 * mm])
    metadata_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EDF3F1")),
                ("BACKGROUND", (2, 0), (2, -3), colors.HexColor("#EDF3F1")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D6DEDA")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("SPAN", (1, 4), (3, 4)),
                ("SPAN", (1, 5), (3, 5)),
            ]
        )
    )
    story.extend([metadata_table, Spacer(1, 3 * mm)])

    events_rows = [
        [para("Evento meteorico dall'ultima ispezione? / Storm event since last inspection?"), para(metadata["storm_event"])],
        [para("Fuoriuscita dall'ultima ispezione? / Discharges since the last inspection?"), para(metadata["spill_past"])],
        [para("Fuoriuscita al momento dell'ispezione? / Discharges at the time of inspection?"), para(metadata["spill_current"])],
    ]
    events_table = Table(events_rows, colWidths=[80 * mm, 90 * mm])
    events_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EDF3F1")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D6DEDA")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
            ]
        )
    )
    story.extend([events_table, Spacer(1, 3 * mm)])

    ENGLISH_ONLY_SECTIONS = {
        "ESC Inspection Checklist",
        "CDWM Inspection Checklist",
        "IAQ Inspection Checklist",
    }

    for section, questions in active_checklists.items():
        if section in ENGLISH_ONLY_SECTIONS:
            section_heading_html = f"<i>{escape(section)}</i>"
        else:
            section_heading_html = format_bilingual(section)
        story.append(Paragraph(section_heading_html, styles["SectionHeading"]))

        rows = [[
            para("BMP o attività / BMP or activity", "TableHeader"),
            para("BMP inst.?", "TableHeaderCenter", bilingual=False),
            para("Manut. / Maint.?", "TableHeaderCenter"),
        ]]
        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), HEADER_TEAL),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D6DEDA")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]

        section_index = list(CHECKLIST_DATA.keys()).index(section)
        current_row = 1
        row_heights = [None]

        for question_index, question in enumerate(questions):
            key = f"q_{section_index}_{question_index}"
            answer = answers.get(key, {})
            bmp_inst = answer.get("bmp_installed", "Da verificare / TBD")
            bmp_maint = answer.get("bmp_maintenance", "Da verificare / TBD")
            note = answer.get("note", "").strip()
            photos = answer.get("photos", [])

            rows.append([
                para(question, "SmallCell", bilingual=True, bold=True),
                para(bmp_inst, "SmallCellCenter", bilingual=True),
                para(bmp_maint, "SmallCellCenter", bilingual=True),
            ])
            row_heights.append(None)

            if bmp_inst in BMP_INSTALLED_COLORS:
                table_style.append(("BACKGROUND", (1, current_row), (1, current_row), BMP_INSTALLED_COLORS[bmp_inst]))
            if bmp_maint in BMP_MAINTENANCE_COLORS:
                table_style.append(("BACKGROUND", (2, current_row), (2, current_row), BMP_MAINTENANCE_COLORS[bmp_maint]))
            current_row += 1

            note_display = escape(note).replace("\n", "<br/>") if note else "—"
            rows.append([
                Paragraph(f"<b>Note-Evidenze / <i>Notes</i>:</b> {note_display}", styles["SmallCell"]),
                "",
                "",
            ])
            row_heights.append(None)
            table_style.append(("SPAN", (0, current_row), (2, current_row)))
            table_style.append(("BACKGROUND", (0, current_row), (2, current_row), colors.HexColor("#FAFBFB")))
            current_row += 1

            if photos:
                photos_per_row = 3
                photo_col_width = 54 * mm
                for chunk_start in range(0, len(photos), photos_per_row):
                    chunk = photos[chunk_start:chunk_start + photos_per_row]
                    photo_cells = []
                    for photo in chunk:
                        img = ReportImage(
                            BytesIO(photo["data"]),
                            width=50 * mm,
                            height=32 * mm,
                            kind="bound",
                        )
                        img.hAlign = "LEFT"
                        photo_cells.append(img)
                    while len(photo_cells) < photos_per_row:
                        photo_cells.append("")

                    photo_grid = Table([photo_cells], colWidths=[photo_col_width] * photos_per_row)
                    photo_grid.setStyle(
                        TableStyle(
                            [
                                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                                ("LEFTPADDING", (0, 0), (-1, -1), 0),
                                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                                ("TOPPADDING", (0, 0), (-1, -1), 2),
                                ("BOTTOMPADDING", (0, 0), (-1, -1), 2),
                            ]
                        )
                    )
                    rows.append([photo_grid, "", ""])
                    row_heights.append(None)
                    table_style.append(("SPAN", (0, current_row), (2, current_row)))
                    current_row += 1

            # Riga di separazione pulita (senza colore e senza bordi laterali) tra una domanda e la successiva
            if question_index < len(questions) - 1:
                rows.append(["", "", ""])
                row_heights.append(3 * mm)
                table_style.append(("SPAN", (0, current_row), (2, current_row)))
                table_style.append(("BACKGROUND", (0, current_row), (2, current_row), colors.white))
                table_style.append(("LINEBEFORE", (0, current_row), (0, current_row), 0, colors.white))
                table_style.append(("LINEAFTER", (2, current_row), (2, current_row), 0, colors.white))
                table_style.append(("TOPPADDING", (0, current_row), (2, current_row), 0))
                table_style.append(("BOTTOMPADDING", (0, current_row), (2, current_row), 0))
                current_row += 1

        table = Table(rows, colWidths=[128 * mm, 22 * mm, 23 * mm], rowHeights=row_heights, repeatRows=1)
        table.setStyle(TableStyle(table_style))
        story.append(table)

    story.extend(
        [
            para("Osservazioni generali / General Notes", "SectionHeading"),
            para(metadata["general_notes"] or "Nessuna osservazione aggiuntiva. / No additional notes.", bilingual=not bool(metadata["general_notes"])),
            Spacer(1, 5 * mm),
        ]
    )

    def build_nc_box(header_text: str, content_text: str) -> Table:
        display_text = (
            escape(content_text).replace("\n", "<br/>")
            if content_text.strip()
            else "<br/><br/><br/>"
        )
        box = Table(
            [
                [para(header_text, "TableHeader")],
                [Paragraph(display_text, styles["SmallCell"])],
            ],
            colWidths=[173 * mm],
        )
        box.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (0, 0), HEADER_TEAL),
                    ("GRID", (0, 0), (-1, -1), 0.5, colors.HexColor("#A9B8B2")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 6),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 6),
                    ("TOPPADDING", (0, 0), (-1, -1), 6),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                ]
            )
        )
        return box

    story.append(
        build_nc_box(
            "Non conformità rilevate / Non-compliance",
            metadata.get("non_compliance", ""),
        )
    )
    story.append(Spacer(1, 4 * mm))
    story.append(
        build_nc_box(
            "Risoluzione non conformità rilevate precedentemente / Previous non-compliance resolution",
            metadata.get("prev_non_compliance_res", ""),
        )
    )
    story.extend(
        [
            Spacer(1, 7 * mm),
            para("Firma ispettore / Inspector Signature: ____________________________________"),
        ]
    )

    footer_codes = []
    if "ESC Inspection Checklist" in active_checklists:
        footer_codes.append("ESC")
    if "CDWM Inspection Checklist" in active_checklists:
        footer_codes.append("CDWM")
    if "IAQ Inspection Checklist" in active_checklists:
        footer_codes.append("IAQ")
    footer_suffix = "/".join(footer_codes) if footer_codes else "LEED"
    footer_caption = f"Checklist cantiere LEED - {footer_suffix}"

    logo_reader = ImageReader(str(LOGO_PATH)) if LOGO_PATH.is_file() else None

    def add_header_footer(canvas, document):
        canvas.saveState()

        # Logo in alto a sinistra
        if logo_reader is not None:
            img_w, img_h = logo_reader.getSize()
            target_height = 11 * mm
            target_width = target_height * (img_w / img_h)
            canvas.drawImage(
                logo_reader,
                17 * mm,
                A4[1] - 16 * mm,
                width=target_width,
                height=target_height,
                preserveAspectRatio=True,
                mask="auto",
            )
        else:
            canvas.setFont("Helvetica", 8)
            canvas.setFillColor(colors.HexColor("#68756F"))
            canvas.drawString(17 * mm, A4[1] - 12 * mm, "GET Consulting Srl")

        # Piè di pagina
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#68756F"))
        canvas.drawString(17 * mm, 10 * mm, footer_caption)
        canvas.drawRightString(A4[0] - 17 * mm, 10 * mm, f"Pagina / Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_header_footer, onLaterPages=add_header_footer)
    return buffer.getvalue()


st.set_page_config(page_title="Checklist cantiere LEED / LEED Site Checklist", page_icon="✅", layout="wide")

st.markdown(
    """
    <style>
    .stApp { background: #f5f7f5; }
    [data-testid="stMetric"] {
        background: white; padding: 14px 18px; border-radius: 12px;
        border: 1px solid #e2e9e5;
    }
    .intro { color: #52645e; margin-top: -0.5rem; }
    </style>
    """,
    unsafe_allow_html=True
)

st.title("Ispezione di cantiere / Construction Site Inspection · LEED")
st.markdown(
    '<p class="intro">Compila le verifiche, registra evidenze e azioni correttive, poi scarica il verbale in PDF. / '
    "Complete the verifications, record evidence and corrective actions, then download the PDF report.</p>",
    unsafe_allow_html=True,
)

with st.expander("Dati del progetto e dell'ispezione / Project and Inspection Data", expanded=True):
    # Riga 1: Commessa | Data ispezione | Ora inizio/fine
    r1_col1, r1_col2, r1_col3 = st.columns(3)
    with r1_col1:
        project = st.text_input("Commessa / Project Name *", key="project")
    with r1_col2:
        inspection_date = st.date_input("Data ispezione / Inspection Date", value=date.today(), key="inspection_date")
    with r1_col3:
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            start_time = st.time_input("Ora inizio / Start time", value=time(8, 0), key="start_time")
        with col_t2:
            end_time = st.time_input("Ora fine / End time", value=time(17, 0), key="end_time")

    # Riga 2: Ispettore | Titolo dell'ispettore | Email ispettore
    r2_col1, r2_col2, r2_col3 = st.columns(3)
    with r2_col1:
        selected_inspectors = st.multiselect(
            "Ispettore / Inspector(s) *",
            list(INSPECTORS_DIRECTORY.keys()),
            placeholder="Seleziona... / Select...",
            key="inspectors",
            on_change=_sync_inspector_emails,
        )
    with r2_col2:
        inspector_titles = st.multiselect(
            "Titolo(i) di chi effettua l'ispezione / Inspector Title(s)",
            INSPECTOR_TITLES,
            placeholder="Seleziona... / Select...",
            key="inspector_titles",
        )
    with r2_col3:
        inspector_email = st.text_input(
            "Email ispettore / Inspector Email(s)",
            key="inspector_email",
        )

    # Riga 3: Fase costruttiva | Indirizzo (+ Meteo) | Tipo di ispezione
    r3_col1, r3_col2, r3_col3 = st.columns(3)
    with r3_col1:
        phase = st.selectbox(
            "Fase costruttiva / Construction Phase",
            CONSTRUCTION_PHASES,
            key="phase",
        )
    with r3_col2:
        address = st.text_input("Indirizzo / Address", key="address")
        weather = "Non disponibile / Not available"
        weather_source = ""
        if address.strip():
            try:
                with st.spinner("Recupero automatico del meteo... / Fetching weather automatically..."):
                    weather_data = fetch_weather(address.strip(), inspection_date.isoformat())
                weather = weather_data["summary"]
                weather_source = weather_data["data_source"]
                weather_label = (
                    "Meteo storico stimato / Estimated historical weather"
                    if inspection_date < date.today()
                    else "Meteo previsto / Weather forecast"
                )
                st.success(f"**{weather_label}:** {weather}")
                st.caption(
                    f"Fonte / Source: Open-Meteo, {weather_source}. I dati passati sono stime "
                    "retrospettive del modello / Past data are retrospective model estimates."
                )
            except WeatherLookupError as error:
                st.warning(str(error))
        else:
            st.caption("Inserisci l'indirizzo per recuperare automaticamente il meteo della data selezionata. / Enter the address to automatically retrieve the weather for the selected date.")
    with r3_col3:
        inspection_type = st.selectbox("Tipo di ispezione / Inspection type", INSPECTION_TYPES, key="inspection_type")

    st.markdown("---")
    st.markdown("##### Eventi meteorici e fuoriuscite / Storm events and discharges")
    
    col_e1, col_e2 = st.columns([1, 2])
    with col_e1:
        storm_event = st.radio("Evento meteorico dall'ultima ispezione? / Storm event since last inspection?", ["No", "Sì / Yes"], key="storm_event", horizontal=True)
    with col_e2:
        storm_details = st.text_input("Data/ora inizio, durata (ore), mm precipitazione / Start date/time, duration (hrs), mm precipitation:", disabled=(storm_event == "No"), key="storm_details")
        
    col_e3, col_e4 = st.columns([1, 2])
    with col_e3:
        spill_past = st.radio("Fuoriuscita dall'ultima ispezione? / Discharges since the last inspection?", ["No", "Sì / Yes"], key="spill_past", horizontal=True)
    with col_e4:
        spill_past_details = st.text_input("Descrivere la fuoriuscita passata / Describe the past discharge:", disabled=(spill_past == "No"), key="spill_past_details")
        
    col_e5, col_e6 = st.columns([1, 2])
    with col_e5:
        spill_current = st.radio("Fuoriuscita al momento dell'ispezione? / Discharges at the time of inspection?", ["No", "Sì / Yes"], key="spill_current", horizontal=True)
    with col_e6:
        spill_current_details = st.text_input("Descrivere la fuoriuscita attuale / Describe the current discharge:", disabled=(spill_current == "No"), key="spill_current_details")

st.divider()
st.subheader("Tipologia di Ispezione / Type of Inspection")
st.write("Seleziona le checklist che vuoi compilare in questa sessione: / Select the checklists you want to complete in this session:")
col1, col2, col3 = st.columns(3)
with col1:
    esc_active = st.checkbox("ESC Inspection Checklist", value=True)
    esc_additional = False
    if esc_active:
        esc_additional = st.checkbox(
            ADDITIONAL_SECTION_TITLE,
            value=False,
            key="esc_additional",
        )
with col2:
    cdwm_active = st.checkbox("CDWM Inspection Checklist", value=True)
with col3:
    iaq_active = st.checkbox("IAQ Inspection Checklist", value=True)

active_checklists = {}
if esc_active:
    active_checklists["ESC Inspection Checklist"] = CHECKLIST_DATA["ESC Inspection Checklist"]
    if esc_additional:
        active_checklists[ADDITIONAL_SECTION_TITLE] = CHECKLIST_DATA[ADDITIONAL_SECTION_TITLE]
if cdwm_active:
    active_checklists["CDWM Inspection Checklist"] = CHECKLIST_DATA["CDWM Inspection Checklist"]
if iaq_active:
    active_checklists["IAQ Inspection Checklist"] = CHECKLIST_DATA["IAQ Inspection Checklist"]

if not active_checklists:
    st.warning("Seleziona almeno una tipologia di ispezione per continuare. / Select at least one type of inspection to continue.")
else:
    answered_count = 0
    no_count = 0
    applicable_count = 0
    total_count = 0

    current_project = st.session_state.get("project", "").strip()
    current_address = st.session_state.get("address", "").strip()
    formatted_date_str = inspection_date.strftime("%d/%m/%Y")

    for section, questions in active_checklists.items():
        section_index = list(CHECKLIST_DATA.keys()).index(section)
        total_count += len(questions)
        with st.expander(section, expanded=True):
            for question_index, question in enumerate(questions):
                key = f"q_{section_index}_{question_index}"
                question_col, status_col1, status_col2 = st.columns([2, 1, 1])
                with question_col:
                    st.markdown(f"**{question}**")
                    uploaded_photos = st.file_uploader(
                        "Foto della verifica / Verification photo",
                        type=["jpg", "jpeg", "png", "heic", "heif"],
                        accept_multiple_files=True,
                        key=f"{key}_photos",
                        help="Supporta JPG, PNG, e formati iPhone HEIC/HEIF. / Supports JPG, PNG, and iPhone HEIC/HEIF formats.",
                    )
                    photos = []
                    for uploaded_photo in uploaded_photos or []:
                        photo_data = uploaded_photo.getvalue()
                        photo_name = uploaded_photo.name
                        
                        if len(photo_data) > 10 * 1024 * 1024:
                            st.error(
                                f"{photo_name}: supera il limite di 10 MB / exceeds 10 MB limit."
                            )
                            continue

                        if photo_name.lower().endswith(('.heic', '.heif')) and not HEIF_SUPPORTED:
                            st.error(f"{photo_name}: libreria 'pillow-heif' non installata nell'ambiente / 'pillow-heif' library not installed.")
                            continue

                        try:
                            photo_data = watermark_photo(
                                photo_data,
                                current_project,
                                formatted_date_str,
                                current_address,
                            )
                            if photo_name.lower().endswith(('.heic', '.heif')):
                                photo_name = photo_name.rsplit('.', 1)[0] + ".jpg"
                        except Exception as e:
                            st.warning(f"Impossibile elaborare o applicare la didascalia a {photo_name}: {e}")
                            continue
                        
                        photos.append({"data": photo_data})
                        try:
                            st.image(photo_data, width=220)
                        except Exception:
                            st.error(f"Errore nella visualizzazione dell'immagine {photo_name}")
                            
                with status_col1:
                    bmp_installed = st.selectbox(
                        "BMP installata? / BMP installed?",
                        STATUSES,
                        key=f"{key}_bmp_inst",
                        on_change=_sync_na_maintenance,
                        args=(key,),
                    )
                with status_col2:
                    bmp_maintenance = st.selectbox(
                        "Necessaria manutenzione alla BMP? / BMP maintenance required?",
                        STATUSES,
                        key=f"{key}_bmp_maint",
                    )
                
                note = st.text_area(
                    "Note / evidenze / azione correttiva / Notes / evidence / corrective action",
                    key=f"{key}_note",
                    height=68,
                    placeholder="Aggiungi riferimenti, dettagli, responsabile e scadenza se necessario. / Add references, details, responsible person and deadline if necessary.",
                )
                st.divider()
                st.session_state[key] = {
                    "bmp_installed": bmp_installed,
                    "bmp_maintenance": bmp_maintenance,
                    "note": note,
                    "photos": photos,
                }
                
                if bmp_installed != "Da verificare / TBD" or bmp_maintenance != "Da verificare / TBD":
                    answered_count += 1
                if bmp_installed != "N/A" or bmp_maintenance != "N/A":
                    applicable_count += 1
                if bmp_installed == "No" or bmp_maintenance == "Sì / Yes":
                    no_count += 1

    st.subheader("Riepilogo / Summary")
    metric1, metric2, metric3 = st.columns(3)
    metric1.metric("Verifiche completate / Completed verifications", f"{answered_count}/{total_count}")
    metric2.metric("Allerte (No BMP / Sì Manutenzione)", no_count)
    metric3.metric("Verifiche applicabili / Applicable verifications", applicable_count)
    st.progress(answered_count / total_count if total_count else 0.0)

    general_notes = st.text_area(
        "Osservazioni generali / General Notes",
        key="general_notes",
        placeholder="Annotazioni conclusive, priorità o riferimenti agli allegati. / Concluding notes, priorities or references to attachments.",
    )

    col_nc1, col_nc2 = st.columns(2)
    with col_nc1:
        non_compliance = st.text_area(
            "Non conformità rilevate / Non-compliance",
            key="non_compliance",
            height=110,
            placeholder="Elencare eventuali non conformità riscontrate durante l'ispezione. / List any non-compliances identified during the inspection.",
        )
    with col_nc2:
        prev_non_compliance_res = st.text_area(
            "Risoluzione non conformità rilevate precedentemente / Previous non-compliance resolution",
            key="prev_non_compliance_res",
            height=110,
            placeholder="Descrivere le azioni correttive attuate per chiudere le non conformità precedenti. / Describe corrective actions taken to close previous non-compliances.",
        )

    if not current_project:
        st.caption("Inserisci il nome del progetto per abilitare il download del PDF. / Enter the project name to enable PDF download.")

    selected_titles = st.session_state.get("inspector_titles", [])
    metadata = {
        "project": current_project or "—",
        "site": st.session_state.get("site", "").strip() or "—",
        "address": current_address or "—",
        "phase": st.session_state.get("phase", "").strip() or "—",
        "inspection_date": formatted_date_str,
        "time_range": f"{st.session_state.get('start_time', '—')} - {st.session_state.get('end_time', '—')}",
        "inspection_type": st.session_state.get("inspection_type", "—"),
        "inspector": ", ".join(selected_inspectors) if selected_inspectors else "—",
        "inspector_titles": ", ".join(selected_titles) if selected_titles else "—",
        "inspector_email": st.session_state.get("inspector_email", "").strip() or "—",
        "weather": f"{weather}\nData: {weather_source or 'N/A'}\nSource: Open-Meteo (CC BY 4.0)",
        "storm_event": f"Sì / Yes: {st.session_state.get('storm_details', '')}" if st.session_state.get('storm_event') == "Sì / Yes" else "No",
        "spill_past": f"Sì / Yes: {st.session_state.get('spill_past_details', '')}" if st.session_state.get('spill_past') == "Sì / Yes" else "No",
        "spill_current": f"Sì / Yes: {st.session_state.get('spill_current_details', '')}" if st.session_state.get('spill_current') == "Sì / Yes" else "No",
        "general_notes": general_notes.strip(),
        "non_compliance": non_compliance.strip(),
        "prev_non_compliance_res": prev_non_compliance_res.strip(),
    }
    
    answers = {
        f"q_{list(CHECKLIST_DATA.keys()).index(section)}_{question_index}": st.session_state.get(
            f"q_{list(CHECKLIST_DATA.keys()).index(section)}_{question_index}",
            {"bmp_installed": "Da verificare / TBD", "bmp_maintenance": "Da verificare / TBD", "note": "", "photos": []},
        )
        for section, questions in active_checklists.items()
        for question_index, _ in enumerate(questions)
    }

    if current_project:
        pdf_bytes = make_pdf(metadata, answers, active_checklists)
        safe_name = "".join(
            char.lower() if char.isalnum() else "_" for char in current_project
        ).strip("_")
        selected_codes = []
        if esc_active:
            selected_codes.append("ESC")
        if cdwm_active:
            selected_codes.append("CDWM")
        if iaq_active:
            selected_codes.append("IAQ")
        codes_str = "-".join(selected_codes) if selected_codes else "LEED"

        st.download_button(
            "Scarica checklist in PDF / Download PDF checklist",
            data=pdf_bytes,
            file_name=f"{safe_name or 'cantiere'}_checklist {codes_str}_{inspection_date:%Y%m%d}.pdf",
            mime="application/pdf",
            type="primary",
        )
    else:
        st.button("Scarica checklist in PDF / Download PDF checklist", disabled=True, type="primary")