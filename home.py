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

CHECKLIST = [
    (
        "Eventi meteorici e fuoriuscite / Storm events and discharges",
        [
            "C’è stato un evento meteorico dall’ultima ispezione? / Has there been a storm event since last inspection? (Se sì, fornire in Note: Data e ora inizio evento, Durata in ore, Quantità precipitazione in mm)",
            "C’è stata fuoriuscita dall’ultima ispezione? / Have any discharges occurred since the last inspection? (Se sì, descrivere in Note)",
            "C’è fuoriuscita al momento dell’ispezione? / Are there any discharges at the time of inspection? (Se sì, descrivere in Note)",
        ],
    ),
    (
        "Pianificazione e gestione del cantiere",
        [
            "Il piano di gestione del cantiere e le procedure ambientali sono disponibili e aggiornati?",
            "Le responsabilità per i requisiti LEED e la raccolta delle evidenze sono assegnate?",
            "Il personale e le imprese coinvolte sono stati informati sulle procedure applicabili?",
            "Le aree e le attività oggetto di verifica sono identificabili e coerenti con i documenti di progetto?",
        ],
    ),
    (
        "Suolo, erosione e controllo delle acque",
        [
            "Sono attive misure per limitare erosione, sedimentazione e trasporto di polveri fuori dal cantiere?",
            "Gli scarichi e il deflusso delle acque meteoriche sono protetti e gestiti secondo il piano di cantiere?",
            "Materiali e prodotti sono stoccati in modo da prevenire contaminazione del suolo o delle acque?",
            "Le misure di protezione vengono controllate dopo piogge o modifiche alle lavorazioni?",
        ],
    ),
    (
        "Rifiuti e materiali",
        [
            "Le aree per raccolta differenziata sono segnalate, accessibili e mantenute in ordine?",
            "I rifiuti sono separati per flusso e conferiti a trasportatori o impianti autorizzati?",
            "Sono conservati formulari, pesate, ricevute o altri documenti di tracciabilità dei rifiuti?",
            "Le schede tecniche, le dichiarazioni ambientali e le evidenze richieste per i materiali sono reperibili?",
        ],
    ),
    (
        "Qualità dell'aria interna durante i lavori",
        [
            "I materiali assorbenti e i condotti HVAC sono protetti da polvere e umidità?",
            "Le prese d'aria e gli impianti sono protetti durante le attività che generano polveri o contaminanti?",
            "Le aree di lavoro sono pulite e i materiali a emissione sono gestiti secondo il piano previsto?",
            "È previsto un controllo finale e, se applicabile, il flush-out o il test della qualità dell'aria?",
        ],
    ),
    (
        "Acqua, energia e protezione delle risorse",
        [
            "Le perdite d'acqua sono individuate e corrette tempestivamente?",
            "Le attrezzature e gli impianti installati corrispondono ai requisiti e alle specifiche approvate?",
            "Sono disponibili registrazioni di consumi, prove o controlli richiesti dal piano di progetto?",
            "Le misure temporanee di risparmio e protezione delle risorse sono applicate nelle aree verificate?",
        ],
    ),
    (
        "Commissioning, documenti e azioni correttive",
        [
            "Le ispezioni, le prove e le verifiche previste per gli impianti sono pianificate o registrate?",
            "Disegni, schede tecniche, approvazioni e verbali sono aggiornati e rintracciabili?",
            "Le non conformità precedenti sono state chiuse con evidenza documentale?",
            "Le azioni correttive emerse in questa ispezione hanno un responsabile e una scadenza?",
        ],
    ),
]

STATUSES = ("Da verificare", "Sì", "No", "N/A")
STATUS_COLORS = {
    "Da verificare": colors.HexColor("#FFF0C2"),
    "Sì": colors.HexColor("#DDF3E5"),
    "No": colors.HexColor("#FCE1DF"),
    "N/A": colors.HexColor("#E9EDF2"),
}

WEATHER_CODES = {
    0: "Sereno",
    1: "Prevalentemente sereno",
    2: "Parzialmente nuvoloso",
    3: "Coperto",
    45: "Nebbia",
    48: "Nebbia con brina",
    51: "Pioviggine leggera",
    53: "Pioviggine moderata",
    55: "Pioviggine intensa",
    56: "Pioviggine gelata leggera",
    57: "Pioviggine gelata intensa",
    61: "Pioggia debole",
    63: "Pioggia moderata",
    65: "Pioggia intensa",
    66: "Pioggia gelata debole",
    67: "Pioggia gelata intensa",
    71: "Neve debole",
    73: "Neve moderata",
    75: "Neve intensa",
    77: "Granuli di neve",
    80: "Rovesci deboli",
    81: "Rovesci moderati",
    82: "Rovesci violenti",
    85: "Rovesci di neve deboli",
    86: "Rovesci di neve intensi",
    95: "Temporale",
    96: "Temporale con grandine debole",
    99: "Temporale con grandine intensa",
}
RECENT_HISTORY_DAYS = 92


class WeatherLookupError(Exception):
    """Errore recuperabile nella ricerca della località o dei dati meteo."""


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_weather(address: str, inspection_day: str) -> dict:
    selected_date = date.fromisoformat(inspection_day)
    today = date.today()
    if selected_date > today + timedelta(days=15):
        raise WeatherLookupError(
            "Le previsioni sono disponibili in una finestra di 16 giorni, incluso oggi."
        )
    if selected_date < today - timedelta(days=RECENT_HISTORY_DAYS):
        weather_endpoint = "https://archive-api.open-meteo.com/v1/archive"
        weather_dates = {
            "start_date": inspection_day,
            "end_date": inspection_day,
        }
        data_source = "archivio climatico"
    elif selected_date < today:
        weather_endpoint = "https://api.open-meteo.com/v1/forecast"
        weather_dates = {
            "past_days": (today - selected_date).days,
            "forecast_days": 1,
        }
        data_source = "dati meteo recenti"
    else:
        weather_endpoint = "https://api.open-meteo.com/v1/forecast"
        weather_dates = {
            "start_date": inspection_day,
            "end_date": inspection_day,
        }
        data_source = "previsioni meteo"

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
                "Località non trovata. Prova a inserire città e provincia."
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
            "Non è stato possibile recuperare i dati meteo. Controlla la connessione "
            "e riprova."
        ) from error

    try:
        day_index = daily.get("time", []).index(inspection_day)
    except ValueError as error:
        raise WeatherLookupError(
            "Il servizio meteo non ha dati disponibili per la data selezionata."
        ) from error

    def daily_value(field: str):
        values = daily.get(field, [])
        return values[day_index] if day_index < len(values) else None

    code = daily_value("weather_code")
    description = WEATHER_CODES.get(code, f"Condizioni variabili (codice {code})")
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
        f"precipitazioni {formatted(precipitation, ' mm')}; "
        f"vento max {formatted(max_wind, ' km/h')}."
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


def make_pdf(metadata: dict, answers: dict) -> bytes:
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=17 * mm,
        leftMargin=17 * mm,
        topMargin=20 * mm,
        bottomMargin=18 * mm,
        title="Checklist ispezione di cantiere LEED",
        author="Dashboard checklist LEED",
    )
    styles = getSampleStyleSheet()
    styles.add(
        ParagraphStyle(
            name="ChecklistTitle",
            parent=styles["Title"],
            fontName="Helvetica-Bold",
            fontSize=18,
            leading=22,
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

    def para(value: object) -> Paragraph:
        return Paragraph(escape(str(value)).replace("\n", "<br/>"), styles["SmallCell"])

    story = [
        Paragraph("Checklist ispezione di cantiere LEED", styles["ChecklistTitle"]),
        Paragraph(
            "Strumento operativo di supporto. Verificare sempre i requisiti applicabili "
            "nella versione LEED, nei crediti perseguiti e nei documenti approvati del progetto.",
            styles["BodyText"],
        ),
        Spacer(1, 4 * mm),
    ]

    metadata_rows = [
        [para("Progetto"), para(metadata["project"]), para("Cantiere / sito"), para(metadata["site"])],
        [para("Fase costruttiva"), para(metadata["phase"]), para("Indirizzo"), para(metadata["address"])],
        [para("Data ispezione"), para(metadata["inspection_date"]), para("Ora inizio / fine"), para(metadata["time_range"])],
        [para("Ispettore"), para(metadata["inspector"]), para("Email ispettore"), para(metadata["inspector_email"])],
        [para("Referente cantiere"), para(metadata["contact"]), para("Versione LEED"), para(metadata["leed_version"])],
        [para("Meteo"), para(metadata["weather"]), "", ""],
    ]
    metadata_table = Table(metadata_rows, colWidths=[31 * mm, 54 * mm, 31 * mm, 54 * mm])
    metadata_table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), colors.HexColor("#EDF3F1")),
                ("BACKGROUND", (2, 0), (2, -2), colors.HexColor("#EDF3F1")),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#D6DEDA")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ("SPAN", (1, 5), (3, 5)), # Merge weather cells
            ]
        )
    )
    story.extend([metadata_table, Spacer(1, 3 * mm)])

    for section_index, (section, questions) in enumerate(CHECKLIST):
        story.append(Paragraph(escape(section), styles["SectionHeading"]))
        rows = [[para("Verifica"), para("Esito"), para("Note / evidenze")]]
        row_statuses = []
        for question_index, question in enumerate(questions):
            key = f"q_{section_index}_{question_index}"
            answer = answers.get(key, {})
            status = answer.get("status", "Da verificare")
            note = answer.get("note", "").strip() or "—"
            rows.append([para(question), para(status), para(note)])
            row_statuses.append(status)
            for photo in answer.get("photos", []):
                image = ReportImage(
                    BytesIO(photo["data"]),
                    width=96 * mm,
                    height=54 * mm,
                    kind="bound",
                )
                image.hAlign = "LEFT"
                rows.append(
                    [[image, para(f"Foto: {photo['name']}")], "", ""]
                )
        table = Table(rows, colWidths=[104 * mm, 25 * mm, 44 * mm], repeatRows=1)
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
        for row_index, status in enumerate(row_statuses, start=1):
            table_style.append(("BACKGROUND", (1, row_index), (1, row_index), STATUS_COLORS[status]))
        table.setStyle(TableStyle(table_style))
        story.append(table)

    story.extend(
        [
            Paragraph("Osservazioni generali", styles["SectionHeading"]),
            para(metadata["general_notes"] or "Nessuna osservazione aggiuntiva."),
            Spacer(1, 6 * mm),
            para("Firma ispettore: ____________________________________"),
        ]
    )

    def add_page_number(canvas, document):
        canvas.saveState()
        canvas.setFont("Helvetica", 8)
        canvas.setFillColor(colors.HexColor("#68756F"))
        canvas.drawString(17 * mm, 10 * mm, "Checklist cantiere LEED - documento di supporto")
        canvas.drawRightString(A4[0] - 17 * mm, 10 * mm, f"Pagina {document.page}")
        canvas.restoreState()

    doc.build(story, onFirstPage=add_page_number, onLaterPages=add_page_number)
    return buffer.getvalue()


st.set_page_config(page_title="Checklist cantiere LEED", page_icon="✅", layout="wide")
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
    unsafe_allow_html=True,
)

st.title("Ispezione di cantiere · Checklist LEED")
st.markdown(
    '<p class="intro">Compila le verifiche, registra evidenze e azioni correttive, '
    "poi scarica il verbale in PDF.</p>",
    unsafe_allow_html=True,
)
st.info(
    "Checklist generale di supporto: non sostituisce i requisiti ufficiali LEED, "
    "il piano di progetto o le indicazioni del LEED AP. Adattare le verifiche alla "
    "versione e ai crediti effettivamente perseguiti."
)

with st.expander("Dati del progetto e dell'ispezione", expanded=True):
    first, second, third = st.columns(3)
    with first:
        project = st.text_input("Nome progetto *", key="project")
        site = st.text_input("Cantiere / sito", key="site")
        address = st.text_input("Indirizzo", key="address")
        phase = st.text_input("Fase costruttiva", key="phase")
    with second:
        inspector = st.text_input("Ispettore *", key="inspector")
        inspector_email = st.text_input("Email ispettore", key="inspector_email")
        inspection_date = st.date_input("Data ispezione", value=date.today(), key="inspection_date")
        col_t1, col_t2 = st.columns(2)
        with col_t1:
            start_time = st.time_input("Ora inizio", value=time(8, 0), key="start_time")
        with col_t2:
            end_time = st.time_input("Ora fine", value=time(17, 0), key="end_time")
    with third:
        contact = st.text_input("Referente cantiere", key="contact")
        leed_version = st.text_input("Versione / sistema LEED", placeholder="Es. BD+C v4.1", key="leed_version")
        
    weather = "Non disponibile"
    weather_source = ""
    if address.strip():
        try:
            with st.spinner("Recupero automatico del meteo..."):
                weather_data = fetch_weather(address.strip(), inspection_date.isoformat())
            weather = weather_data["summary"]
            weather_source = weather_data["data_source"]
            weather_label = (
                "Meteo storico stimato"
                if inspection_date < date.today()
                else "Meteo previsto"
            )
            st.success(f"**{weather_label}:** {weather}")
            st.caption(
                f"Fonte: Open-Meteo, {weather_source}. I dati passati sono stime "
                "retrospettive del modello, non misure ufficiali della stazione locale."
            )
        except WeatherLookupError as error:
            st.warning(str(error))
    else:
        st.caption("Inserisci l'indirizzo per recuperare automaticamente il meteo della data selezionata.")

answered_count = 0
no_count = 0
applicable_count = 0
for section_index, (section, questions) in enumerate(CHECKLIST):
    with st.expander(section, expanded=False):
        for question_index, question in enumerate(questions):
            key = f"q_{section_index}_{question_index}"
            question_col, status_col = st.columns([4, 1])
            with question_col:
                st.markdown(f"**{question}**")
                uploaded_photos = st.file_uploader(
                    "Foto della verifica",
                    type=["jpg", "jpeg", "png"],
                    accept_multiple_files=True,
                    key=f"{key}_photos",
                    help="Le foto vengono mostrate sotto la domanda e inserite nello stesso punto nel PDF.",
                )
                photos = []
                for uploaded_photo in uploaded_photos or []:
                    photo_data = uploaded_photo.getvalue()
                    if len(photo_data) > 10 * 1024 * 1024:
                        st.error(
                            f"{uploaded_photo.name}: supera il limite di 10 MB e non verrà aggiunta."
                        )
                        continue
                    photos.append({"name": uploaded_photo.name, "data": photo_data})
                    st.image(photo_data, caption=uploaded_photo.name, width=180)
            with status_col:
                status = st.selectbox(
                    "Esito",
                    STATUSES,
                    key=f"{key}_status",
                    label_visibility="collapsed",
                )
            note = st.text_area(
                "Note / evidenze / azione correttiva / dettagli richiesti",
                key=f"{key}_note",
                height=68,
                placeholder="Aggiungi riferimenti, dettagli, responsabile e scadenza se necessario.",
            )
            st.divider()
            st.session_state[key] = {
                "status": status,
                "note": note,
                "photos": photos,
            }
            if status != "Da verificare":
                answered_count += 1
                applicable_count += status != "N/A"
            if status == "No":
                no_count += 1

total_count = sum(len(questions) for _, questions in CHECKLIST)
st.subheader("Riepilogo")
metric1, metric2, metric3 = st.columns(3)
metric1.metric("Verifiche completate", f"{answered_count}/{total_count}")
metric2.metric("Esiti negativi", no_count)
metric3.metric("Verifiche applicabili", applicable_count)
st.progress(answered_count / total_count if total_count else 0.0)

general_notes = st.text_area(
    "Osservazioni generali",
    key="general_notes",
    placeholder="Annotazioni conclusive, priorità o riferimenti agli allegati.",
)

if not st.session_state.get("project", "").strip():
    st.caption("Inserisci il nome del progetto per abilitare il download del PDF.")

metadata = {
    "project": st.session_state.get("project", "").strip() or "—",
    "site": st.session_state.get("site", "").strip() or "—",
    "address": st.session_state.get("address", "").strip() or "—",
    "phase": st.session_state.get("phase", "").strip() or "—",
    "inspection_date": st.session_state.get("inspection_date", date.today()).strftime("%d/%m/%Y"),
    "time_range": f"{st.session_state.get('start_time', '—')} - {st.session_state.get('end_time', '—')}",
    "inspector": st.session_state.get("inspector", "").strip() or "—",
    "inspector_email": st.session_state.get("inspector_email", "").strip() or "—",
    "leed_version": st.session_state.get("leed_version", "").strip() or "—",
    "contact": st.session_state.get("contact", "").strip() or "—",
    "weather": (
        f"{weather}\nTipo dati: {weather_source or 'non disponibile'}\n"
        "Fonte: Open-Meteo (CC BY 4.0)"
    ),
    "general_notes": general_notes.strip(),
}
answers = {
    f"q_{section_index}_{question_index}": st.session_state.get(
        f"q_{section_index}_{question_index}",
        {"status": "Da verificare", "note": "", "photos": []},
    )
    for section_index, (_, questions) in enumerate(CHECKLIST)
    for question_index, _ in enumerate(questions)
}

if project.strip():
    pdf_bytes = make_pdf(metadata, answers)
    safe_name = "".join(
        char.lower() if char.isalnum() else "_" for char in project.strip()
    ).strip("_")
    st.download_button(
        "Scarica checklist in PDF",
        data=pdf_bytes,
        file_name=f"checklist_leed_{safe_name or 'cantiere'}_{inspection_date:%Y%m%d}.pdf",
        mime="application/pdf",
        type="primary",
    )
else:
    st.button("Scarica checklist in PDF", disabled=True, type="primary")