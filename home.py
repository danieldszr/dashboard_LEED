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


def make_pdf(metadata: dict, answers: dict, active_checklists: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=20 * mm,
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

    def para(value: object, style="SmallCell") -> Paragraph:
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles[style])

    story = [
        Paragraph("Ispezione di cantiere LEED / LEED Construction Site Inspection", styles["ChecklistTitle"]),
        Paragraph(
            "Strumento operativo di supporto. Verificare sempre i requisiti applicabili "
            "nella versione LEED, nei crediti perseguiti e nei documenti approvati del progetto. / "
            "Supporting operational tool. Always verify the applicable requirements in the LEED version, "
            "pursued credits, and approved project documents.",
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm),
    ]

    metadata_rows = [
        [para("Progetto / Project"), para(metadata["project"]), para("Ispettore / Inspector"), para(metadata["inspector"])],
        [para("Cantiere-sito / Site"), para(metadata["site"]), para("Email ispettore / Insp. Email"), para(metadata["inspector_email"])],
        [para("Fase costr. / Phase"), para(metadata["phase"]), para("Referente / Site Contact"), para(metadata["contact"])],
        [para("Indirizzo / Address"), para(metadata["address"]), para("Versione LEED / LEED Ver."), para(metadata["leed_version"])],
        [para("Data ispezione / Date"), para(metadata["inspection_date"]), para("Ora / Time (Start-End)"), para(metadata["time_range"])],
        [para("Tipo Ispez. / Insp. Type"), para(metadata["inspection_type"]), "", ""],
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
                ("SPAN", (1, 5), (3, 5)),
                ("SPAN", (1, 6), (3, 6)),
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

    for section, questions in active_checklists.items():
        story.append(Paragraph(escape(section), styles["SectionHeading"]))
        rows = [[para("Verifica / Verification"), para("BMP inst.?"), para("Manut. / Maint.?"), para("Note-Evidenze / Notes")]]
        row_statuses = []
        section_index = list(CHECKLIST_DATA.keys()).index(section)
        for question_index, question in enumerate(questions):
            key = f"q_{section_index}_{question_index}"
            answer = answers.get(key, {})
            bmp_inst = answer.get("bmp_installed", "Da verificare / TBD")
            bmp_maint = answer.get("bmp_maintenance", "Da verificare / TBD")
            note = answer.get("note", "").strip() or "—"
            rows.append([para(question), para(bmp_inst, "SmallCellCenter"), para(bmp_maint, "SmallCellCenter"), para(note)])
            row_statuses.append((bmp_inst, bmp_maint))
            
            for photo in answer.get("photos", []):
                image = ReportImage(
                    BytesIO(photo["data"]),
                    width=96 * mm,
                    height=54 * mm,
                    kind="bound",
                )
                image.hAlign = "LEFT"
                rows.append(
                    [[image, para(f"Foto/Photo: {photo['name']}")], "", "", ""]
                )
                
        table = Table(rows, colWidths=[88 * mm, 21 * mm, 21 * mm, 43 * mm], repeatRows=1)
        table_style = [
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#173B35")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
            ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D6DEDA")),
            ("VALIGN", (0, 0), (-1, -1), "TOP"),
            ("LEFTPADDING", (0, 0), (-1, -1), 5),
            ("RIGHTPADDING", (0, 0), (-1, -1), 5),
            ("TOPPADDING", (0, 0), (-1, -1), 5),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
        ]
        
        current_row = 1
        for question_index, _ in enumerate(questions):
            key = f"q_{section_index}_{question_index}"
            answer = answers.get(key, {})
            bmp_inst = answer.get("bmp_installed", "Da verificare / TBD")
            bmp_maint = answer.get("bmp_maintenance", "Da verificare / TBD")
            table_style.append(("BACKGROUND", (1, current_row), (1, current_row), STATUS_COLORS[bmp_inst]))
            table_style.append(("BACKGROUND", (2, current_row), (2, current_row), STATUS_COLORS[bmp_maint]))
            current_row += 1
            current_row += len(answer.get("photos", []))

        table.setStyle(TableStyle(table_style))
        story.append(table)

    story.extend(
        [
            Paragraph("Osservazioni generali / General Notes", styles["SectionHeading"]),
            para(metadata["general_notes"] or "Nessuna osservazione aggiuntiva. / No additional notes."),
            Spacer(1, 6 * mm),
            para("Firma ispettore / Inspector Signature: ____________________________________"),
        ]
    )

    def add_page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#68756F"))
        canvas.drawString(17 * mm, 10 * mm, "Checklist cantiere LEED - doc. di supporto / LEED site checklist - support doc.")
        canvas.drawRightString(A4[0] - 17 * mm, 10 * mm, f"Pagina / Page {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
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
st.info(
    "Checklist generale di supporto: non sostituisce i requisiti ufficiali LEED, il piano di progetto o le indicazioni del LEED AP. / "
    "General support checklist: it does not replace the official LEED requirements, the project plan or the LEED AP indications."
)

with st.expander("Dati del progetto e dell'ispezione / Project and Inspection Data", expanded=True):
    first, second, third = st.columns(3)
    with first:
        project = st.text_input("Nome progetto / Project Name *", key="project")
        site = st.text_input("Cantiere-sito / Site", key="site")
        phase = st.text_input("Fase costruttiva / Construction Phase", key="phase")
        address = st.text_input("Indirizzo / Address", key="address")
    with second:
        inspector = st.text_input("Ispettore / Inspector *", key="inspector")
        inspector_email = st.text_input("Email ispettore / Inspector Email", key="inspector_email")
        contact = st.text_input("Referente cantiere / Site Contact", key="contact")
        leed_version = st.text_input("Versione-sistema LEED / LEED Version", placeholder="Es. BD+C v4.1", key="leed_version")
    with third:
        inspection_date = st.date_input("Data ispezione / Inspection Date", value=date.today(), key="inspection_date")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            start_time = st.time_input("Ora inizio / Start time", value=time(8, 0), key="start_time")
        with col_t2:
            end_time = st.time_input("Ora fine / End time", value=time(17, 0), key="end_time")
        inspection_type = st.selectbox("Tipo di ispezione / Inspection type", INSPECTION_TYPES, key="inspection_type")
        
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
with col2:
    cdwm_active = st.checkbox("CDWM Inspection Checklist", value=True)
with col3:
    iaq_active = st.checkbox("IAQ Inspection Checklist", value=True)

active_checklists = {}
if esc_active:
    active_checklists["ESC Inspection Checklist"] = CHECKLIST_DATA["ESC Inspection Checklist"]
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
                        
                        if photo_name.lower().endswith(('.heic', '.heif')):
                            try:
                                img = Image.open(io.BytesIO(photo_data))
                                img = img.convert("RGB")
                                temp_io = io.BytesIO()
                                img.save(temp_io, format="JPEG")
                                photo_data = temp_io.getvalue()
                                photo_name = photo_name.rsplit('.', 1)[0] + ".jpg"
                            except Exception as e:
                                st.warning(f"Impossibile convertire {photo_name}. Potrebbe mancare la libreria 'pillow-heif'.")
                                
                        if len(photo_data) > 10 * 1024 * 1024:
                            st.error(
                                f"{photo_name}: supera il limite di 10 MB / exceeds 10 MB limit."
                            )
                            continue
                        
                        photos.append({"name": photo_name, "data": photo_data})
                        try:
                            st.image(photo_data, caption=photo_name, width=180)
                        except Exception:
                            st.error(f"Errore nella visualizzazione dell'immagine {photo_name}")
                            
                with status_col1:
                    bmp_installed = st.selectbox(
                        "BMP installata? / BMP installed?",
                        STATUSES,
                        key=f"{key}_bmp_inst"
                    )
                with status_col2:
                    bmp_maintenance = st.selectbox(
                        "Necessaria manutenzione alla BMP? / BMP maintenance required?",
                        STATUSES,
                        key=f"{key}_bmp_maint"
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

    if not st.session_state.get("project", "").strip():
        st.caption("Inserisci il nome del progetto per abilitare il download del PDF. / Enter the project name to enable PDF download.")

    metadata = {
        "project": st.session_state.get("project", "").strip() or "—",
        "site": st.session_state.get("site", "").strip() or "—",
        "address": st.session_state.get("address", "").strip() or "—",
        "phase": st.session_state.get("phase", "").strip() or "—",
        "inspection_date": st.session_state.get("inspection_date", date.today()).strftime("%d/%m/%Y"),
        "time_range": f"{st.session_state.get('start_time', '—')} - {st.session_state.get('end_time', '—')}",
        "inspection_type": st.session_state.get("inspection_type", "—"),
        "inspector": st.session_state.get("inspector", "").strip() or "—",
        "inspector_email": st.session_state.get("inspector_email", "").strip() or "—",
        "leed_version": st.session_state.get("leed_version", "").strip() or "—",
        "contact": st.session_state.get("contact", "").strip() or "—",
        "weather": f"{weather}\nData: {weather_source or 'N/A'}\nSource: Open-Meteo (CC BY 4.0)",
        "storm_event": f"Sì / Yes: {st.session_state.get('storm_details', '')}" if st.session_state.get('storm_event') == "Sì / Yes" else "No",
        "spill_past": f"Sì / Yes: {st.session_state.get('spill_past_details', '')}" if st.session_state.get('spill_past') == "Sì / Yes" else "No",
        "spill_current": f"Sì / Yes: {st.session_state.get('spill_current_details', '')}" if st.session_state.get('spill_current') == "Sì / Yes" else "No",
        "general_notes": general_notes.strip(),
    }
    
    answers = {
        f"q_{list(CHECKLIST_DATA.keys()).index(section)}_{question_index}": st.session_state.get(
            f"q_{list(CHECKLIST_DATA.keys()).index(section)}_{question_index}",
            {"bmp_installed": "Da verificare / TBD", "bmp_maintenance": "Da verificare / TBD", "note": "", "photos": []},
        )
        for section, questions in active_checklists.items()
        for question_index, _ in enumerate(questions)
    }

    if project.strip():
        pdf_bytes = make_pdf(metadata, answers, active_checklists)
        safe_name = "".join(
            char.lower() if char.isalnum() else "_" for char in project.strip()
        ).strip("_")
        st.download_button(
            "Scarica checklist in PDF / Download PDF checklist",
            data=pdf_bytes,
            file_name=f"checklist_leed_{safe_name or 'cantiere'}_{inspection_date:%Y%m%d}.pdf",
            mime="application/pdf",
            type="primary",
        )
    else:
        st.button("Scarica checklist in PDF / Download PDF checklist", disabled=True, type="primary")