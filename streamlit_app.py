import io
from datetime import datetime

import pandas as pd
import plotly.express as px
import requests
import streamlit as st

st.set_page_config(page_title="Eurostat Asylum Insights", page_icon="🌍", layout="wide")

EU_BLUE = "#003399"
UNHCR_BLUE = "#0072BC"
NAVY = "#003B5C"
GRID = "#DCE5F2"
COLORS = [EU_BLUE, UNHCR_BLUE, "#4E79A7", "#59C3E6", "#6F4EBA", "#2A9D8F", "#F4A261", "#E76F51"]

st.markdown("""
<style>
.stApp {background:linear-gradient(180deg,#F8FAFF 0%,#EDF3FA 100%);}
.block-container {padding-top:1.3rem;padding-bottom:2rem;max-width:1480px;}
h1,h2,h3 {color:#003B5C;}
.hero {padding:24px 28px;border-radius:18px;color:white;margin-bottom:18px;background:linear-gradient(110deg,#003B5C,#003399 55%,#0072BC);box-shadow:0 10px 30px rgba(0,51,153,.18);}
.hero h1 {color:white;margin:0;font-size:2rem;}.hero p {color:#EAF0FF;margin:8px 0 0;}
.section-title {font-size:1.15rem;font-weight:750;color:#003B5C;margin:16px 0 8px;}
div[data-testid="stMetric"] {background:white;border:1px solid #D4E1F1;padding:17px 19px;border-radius:15px;box-shadow:0 5px 16px rgba(0,59,92,.07);}
div[data-testid="stMetricLabel"] {color:#516979;font-weight:600;} div[data-testid="stMetricValue"] {color:#003399;font-weight:800;}
div[data-testid="stPlotlyChart"] {background:white;border:1px solid #D4E1F1;border-radius:15px;padding:8px;overflow:hidden;box-shadow:0 5px 16px rgba(0,59,92,.06);}
section[data-testid="stSidebar"] {background:#003B5C;}
section[data-testid="stSidebar"] h1,section[data-testid="stSidebar"] h2,section[data-testid="stSidebar"] h3,section[data-testid="stSidebar"] label,section[data-testid="stSidebar"] p {color:white !important;}
section[data-testid="stSidebar"] button {border-radius:10px;} section[data-testid="stSidebar"] button p {color:#111 !important;}
.note {background:#FFF;border-left:5px solid #FFCC00;padding:11px 14px;border-radius:0 10px 10px 0;color:#365B6D;margin:8px 0 14px;}
</style>
""", unsafe_allow_html=True)

COUNTRIES = {
    "Austria":"AT","Belgium":"BE","Bulgaria":"BG","Croatia":"HR","Cyprus":"CY","Czechia":"CZ","Denmark":"DK",
    "Estonia":"EE","Finland":"FI","France":"FR","Germany":"DE","Greece":"EL","Hungary":"HU","Iceland":"IS",
    "Ireland":"IE","Italy":"IT","Latvia":"LV","Liechtenstein":"LI","Lithuania":"LT","Luxembourg":"LU","Malta":"MT",
    "Netherlands":"NL","Norway":"NO","Poland":"PL","Portugal":"PT","Romania":"RO","Slovakia":"SK","Slovenia":"SI",
    "Spain":"ES","Sweden":"SE","Switzerland":"CH","United Kingdom":"UK","Montenegro":"ME"
}

NATIONALITIES = {
    "Afghanistan":"AF","Albania":"AL","Algeria":"DZ","Bangladesh":"BD","Belarus":"BY","Cameroon":"CM","China":"CN",
    "Colombia":"CO","DR Congo":"CD","Côte d’Ivoire":"CI","Egypt":"EG","Eritrea":"ER","Ethiopia":"ET","Georgia":"GE",
    "Guinea":"GN","India":"IN","Iran":"IR","Iraq":"IQ","Lebanon":"LB","Mali":"ML","Morocco":"MA","Nigeria":"NG",
    "North Macedonia":"MK","Pakistan":"PK","Palestine":"PS","Russia":"RU","Senegal":"SN","Serbia":"RS","Somalia":"SO",
    "Sudan":"SD","Syria":"SY","Tunisia":"TN","Türkiye":"TR","Ukraine":"UA","Venezuela":"VE"
}

CAPITALS = {
    "AT":(48.2082,16.3738,"Vienna"),"BE":(50.8503,4.3517,"Brussels"),"BG":(42.6977,23.3219,"Sofia"),"HR":(45.8150,15.9819,"Zagreb"),
    "CY":(35.1856,33.3823,"Nicosia"),"CZ":(50.0755,14.4378,"Prague"),"DK":(55.6761,12.5683,"Copenhagen"),"EE":(59.4370,24.7536,"Tallinn"),
    "FI":(60.1699,24.9384,"Helsinki"),"FR":(48.8566,2.3522,"Paris"),"DE":(52.5200,13.4050,"Berlin"),"EL":(37.9838,23.7275,"Athens"),
    "HU":(47.4979,19.0402,"Budapest"),"IS":(64.1466,-21.9426,"Reykjavik"),"IE":(53.3498,-6.2603,"Dublin"),"IT":(41.9028,12.4964,"Rome"),
    "LV":(56.9496,24.1052,"Riga"),"LI":(47.1410,9.5209,"Vaduz"),"LT":(54.6872,25.2797,"Vilnius"),"LU":(49.6116,6.1319,"Luxembourg"),
    "MT":(35.8989,14.5146,"Valletta"),"NL":(52.3676,4.9041,"Amsterdam"),"NO":(59.9139,10.7522,"Oslo"),"PL":(52.2297,21.0122,"Warsaw"),
    "PT":(38.7223,-9.1393,"Lisbon"),"RO":(44.4268,26.1025,"Bucharest"),"SK":(48.1486,17.1077,"Bratislava"),"SI":(46.0569,14.5058,"Ljubljana"),
    "ES":(40.4168,-3.7038,"Madrid"),"SE":(59.3293,18.0686,"Stockholm"),"CH":(46.9480,7.4474,"Bern"),"UK":(51.5074,-0.1278,"London"),
    "ME":(42.4304,19.2594,"Podgorica")
}

DATASET = "migr_asyappctzm"
BASE_URL = f"https://ec.europa.eu/eurostat/api/dissemination/sdmx/3.0/data/dataflow/ESTAT/{DATASET}/1.0/*.*.*.*.*.*.*"
SEX_CODES = ["M", "F", "UNK"]
AGE_CODES = ["Y_LT14", "Y14-17", "Y18-34", "Y35-64", "Y_GE65", "UNK"]


def csv_vals(values):
    return ",".join(values)


def parse_cell(cell):
    if pd.isna(cell):
        return None, ""
    text = str(cell).strip()
    if not text or text.startswith(":"):
        return None, text[1:].strip() if len(text) > 1 else ""
    parts = text.split()
    try:
        value = float(parts[0].replace(",", ""))
    except ValueError:
        return None, ""
    return value, " ".join(parts[1:])


def parse_tsv(text, nationality_name):
    """
    Convert the wide Eurostat TSV response into tidy monthly observations.

    This version parses the Eurostat time-series rows directly instead
    of using pandas.melt(), which avoids duplicate-column problems.
    """

    raw = pd.read_csv(
        io.StringIO(text),
        sep="\t",
        dtype=str
    )

    if raw.empty:
        return pd.DataFrame()

    # First column contains the SDMX series dimensions.
    #
    # Example:
    # freq,unit,citizen,sex,applicant,age,geo\\TIME_PERIOD
    series_col = raw.columns[0]

    dimension_names = (
        series_col
        .replace("\\TIME_PERIOD", "")
        .split(",")
    )

    dimension_names = [
        name.strip()
        for name in dimension_names
    ]

    # Every column after the first one represents a month.
    #
    # Example:
    # 2021-01
    # 2021-02
    # 2021-03
    period_columns = [
        column
        for column in raw.columns[1:]
        if str(column).strip()
    ]

    records = []

    # Process each Eurostat time series.
    for _, source_row in raw.iterrows():

        series_key = str(
            source_row.iloc[0]
        )

        dimension_values = [
            value.strip()
            for value in series_key.split(",")
        ]

        # Pair dimension names with their values.
        dimensions = dict(
            zip(
                dimension_names,
                dimension_values
            )
        )

        # Process every monthly observation.
        for period_column in period_columns:

            value, status = parse_cell(
                source_row[period_column]
            )

            # ":" and other unavailable observations
            # are returned as None by parse_cell().
            if value is None:
                continue

            period = str(
                period_column
            ).strip()

            date = pd.to_datetime(
                period,
                format="%Y-%m",
                errors="coerce"
            )

            if pd.isna(date):
                continue

            record = dimensions.copy()

            record.update(
                {
                    "Period": period,
                    "Date": date,
                    "First-time applications": value,
                    "Status": status,
                    "Nationality": nationality_name,
                }
            )

            records.append(record)

    if not records:
        return pd.DataFrame()

    return pd.DataFrame(records)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_one_nationality(nationality_name, citizen_code, geo_codes, start_period, end_period):
    # IMPORTANT: commas mean OR for ordinary component filters.
    # TIME_PERIOD is the range filter and therefore combines ge/le with + (AND).
    params = {
        "c[freq]": "M",
        "c[unit]": "PER",
        "c[citizen]": citizen_code,
        "c[sex]": csv_vals(SEX_CODES),
        "c[applicant]": "FRST",
        "c[age]": csv_vals(AGE_CODES),
        "c[geo]": csv_vals(geo_codes),
        "c[TIME_PERIOD]": f"ge:{start_period}+le:{end_period}",
        "compress": "true",
        "format": "tsv",
    }
    headers = {"Accept": "text/tab-separated-values", "User-Agent": "Eurostat-Asylum-Streamlit-App/1.0"}

    try:
        response = requests.get(BASE_URL, params=params, headers=headers, timeout=90)
        response.raise_for_status()
    except requests.exceptions.Timeout as exc:
        raise RuntimeError("Eurostat took too long to respond. Try fewer countries, nationalities, or years.") from exc
    except requests.exceptions.RequestException as exc:
        detail = ""
        if getattr(exc, "response", None) is not None:
            detail = f" Eurostat response: {exc.response.text[:500]}"
        raise RuntimeError(f"Eurostat SDMX request failed: {exc}.{detail}") from exc

    return parse_tsv(response.text, nationality_name)


@st.cache_data(ttl=3600, show_spinner=False)
def fetch_eurostat(nationality_items, geo_codes, start_period, end_period):
    frames = []
    for nationality_name, citizen_code in nationality_items:
        frame = fetch_one_nationality(nationality_name, citizen_code, geo_codes, start_period, end_period)
        if not frame.empty:
            frames.append(frame)
    if not frames:
        return pd.DataFrame()

    detail = pd.concat(frames, ignore_index=True)
    country_by_code = {code: name for name, code in COUNTRIES.items()}
    detail["Country code"] = detail["geo"]
    detail["Country of asylum"] = detail["Country code"].map(country_by_code).fillna(detail["Country code"])
    detail["Year"] = detail["Date"].dt.year
    detail["Month"] = detail["Date"].dt.strftime("%b")
    return detail


def style_chart(fig, title, height=420, legend=False):
    fig.update_layout(
        title=dict(text=title, x=.02, y=.96, xanchor="left", yanchor="top", font=dict(size=18, color=NAVY)),
        height=height, margin=dict(l=18, r=18, t=108 if legend else 80, b=25),
        plot_bgcolor="white", paper_bgcolor="rgba(0,0,0,0)", font=dict(color="#365B6D"),
        hoverlabel=dict(bgcolor="white", font_size=13),
    )
    if legend:
        fig.update_layout(legend=dict(orientation="h", x=.02, xanchor="left", y=1.02, yanchor="bottom", title_text=""))


st.markdown('<div class="hero"><h1>🌍 Eurostat Asylum Insights</h1><p>First-time asylum applications by month, year, country of asylum and nationality</p></div>', unsafe_allow_html=True)

now = datetime.now()
current_year = now.year
DEFAULT_COUNTRIES = ["Greece", "Germany", "France", "Italy", "Spain"]
DEFAULT_NATIONALITIES = ["Syria", "Afghanistan", "Türkiye", "Venezuela", "Colombia"]


def clear_filters():
    st.session_state["countries"] = DEFAULT_COUNTRIES
    st.session_state["nationalities"] = DEFAULT_NATIONALITIES
    st.session_state["years"] = (max(2015, current_year - 5), current_year)


with st.sidebar:
    st.header("Dashboard filters")
    st.button("↻ Clear all filters", use_container_width=True, on_click=clear_filters)
    selected_countries = st.multiselect("Country of asylum", list(COUNTRIES), default=DEFAULT_COUNTRIES, key="countries")
    selected_nationalities = st.multiselect("Nationality", list(NATIONALITIES), default=DEFAULT_NATIONALITIES, key="nationalities")
    selected_years = st.slider("Year range", 2008, current_year, (max(2015, current_year - 5), current_year), key="years")
    st.divider()
    st.caption("Source: Eurostat SDMX 3.0 API · migr_asyappctzm · applicant FRST")

if not selected_countries or not selected_nationalities:
    st.warning("Select at least one country of asylum and one nationality.")
    st.stop()
if len(selected_countries) > 10 or len(selected_nationalities) > 10:
    st.warning("For API performance, select at most 10 countries and 10 nationalities.")
    st.stop()

start_year, end_year = selected_years
start_period = f"{start_year}-01"
end_period = min(f"{end_year}-12", now.strftime("%Y-%m"))

with st.spinner("Retrieving first-time asylum data from Eurostat SDMX 3.0..."):
    try:
        detail = fetch_eurostat(
            [(name, NATIONALITIES[name]) for name in selected_nationalities],
            [COUNTRIES[name] for name in selected_countries],
            start_period,
            end_period,
        )
    except RuntimeError as error:
        st.error(str(error))
        st.stop()

if detail.empty:
    st.warning("Eurostat returned no data for this selection.")
    st.stop()

# The requested M/F/UNK sex categories and age bands are mutually exclusive;
# aggregate these series to total first-time applicants by country/nationality/month.
df = detail.groupby(
    ["Date", "Year", "Month", "Country code", "Country of asylum", "Nationality"], as_index=False
).agg(
    **{"First-time applications": ("First-time applications", "sum")},
    Status=("Status", lambda values: ", ".join(sorted({v for v in values if v}))),
)

latest_date = df["Date"].max()
latest_total = df.loc[df["Date"] == latest_date, "First-time applications"].sum()
previous_date = latest_date - pd.DateOffset(months=1)
previous_total = df.loc[df["Date"] == previous_date, "First-time applications"].sum()
change = (latest_total - previous_total) / previous_total if previous_total else None
period_total = df["First-time applications"].sum()
latest_year_total = df.loc[df["Year"] == latest_date.year, "First-time applications"].sum()
top_country = df.groupby("Country of asylum")["First-time applications"].sum().idxmax()
top_nationality = df.groupby("Nationality")["First-time applications"].sum().idxmax()

st.markdown('<div class="section-title">Overview</div>', unsafe_allow_html=True)
k1,k2,k3,k4,k5 = st.columns(5)
k1.metric("Selected-period total", f"{period_total:,.0f}")
k2.metric(f"Latest month · {latest_date:%b %Y}", f"{latest_total:,.0f}", f"{change:+.1%}" if change is not None else None)
k3.metric(f"{latest_date.year} total", f"{latest_year_total:,.0f}")
k4.metric("Top asylum country", top_country)
k5.metric("Top nationality", top_nationality)
st.markdown('<div class="note">The latest year may be incomplete. Eurostat observation flags are retained in the downloadable table.</div>', unsafe_allow_html=True)

st.markdown('<div class="section-title">Applications over time</div>', unsafe_allow_html=True)
monthly = df.groupby(["Date", "Country of asylum"], as_index=False)["First-time applications"].sum()
fig_monthly = px.line(monthly, x="Date", y="First-time applications", color="Country of asylum", markers=True, color_discrete_sequence=COLORS)
style_chart(fig_monthly, "Monthly first-time asylum applications", 475, True)
fig_monthly.update_traces(line=dict(width=2.7), marker=dict(size=5), hovertemplate="<b>%{fullData.name}</b><br>%{x|%b %Y}<br>%{y:,.0f}<extra></extra>")
fig_monthly.update_xaxes(title="Month", gridcolor=GRID)
fig_monthly.update_yaxes(title="First-time applications", tickformat=",.0f", gridcolor=GRID)
st.plotly_chart(fig_monthly, use_container_width=True)

yearly = df.groupby(["Year", "Country of asylum"], as_index=False)["First-time applications"].sum()
fig_yearly = px.bar(yearly, x="Year", y="First-time applications", color="Country of asylum", barmode="group", color_discrete_sequence=COLORS)
style_chart(fig_yearly, "Annual first-time asylum applications", 450, True)
fig_yearly.update_xaxes(title="Year", dtick=1, gridcolor=GRID)
fig_yearly.update_yaxes(title="First-time applications", tickformat=",.0f", gridcolor=GRID)
st.plotly_chart(fig_yearly, use_container_width=True)

st.markdown('<div class="section-title">Country and nationality analysis</div>', unsafe_allow_html=True)
left,right = st.columns(2)
country_totals = df.groupby("Country of asylum", as_index=False)["First-time applications"].sum().sort_values("First-time applications")
with left:
    fig_country = px.bar(country_totals, x="First-time applications", y="Country of asylum", orientation="h", color="First-time applications", color_continuous_scale=["#D7E7FF", EU_BLUE], text_auto=".3s")
    style_chart(fig_country, "Applications by country of asylum", 470)
    fig_country.update_layout(coloraxis_showscale=False)
    fig_country.update_xaxes(title="First-time applications", tickformat=",.0f", gridcolor=GRID)
    fig_country.update_yaxes(title="")
    st.plotly_chart(fig_country, use_container_width=True)

nationality_totals = df.groupby("Nationality", as_index=False)["First-time applications"].sum().sort_values("First-time applications")
with right:
    fig_nat = px.bar(nationality_totals, x="First-time applications", y="Nationality", orientation="h", color="First-time applications", color_continuous_scale=["#D7F3FA", UNHCR_BLUE], text_auto=".3s")
    style_chart(fig_nat, "Applications by nationality", 470)
    fig_nat.update_layout(coloraxis_showscale=False)
    fig_nat.update_xaxes(title="First-time applications", tickformat=",.0f", gridcolor=GRID)
    fig_nat.update_yaxes(title="")
    st.plotly_chart(fig_nat, use_container_width=True)

matrix = df.pivot_table(index="Nationality", columns="Country of asylum", values="First-time applications", aggfunc="sum", fill_value=0)
fig_heat = px.imshow(matrix, aspect="auto", color_continuous_scale=["#F4F7FF", "#7DA7E8", EU_BLUE], text_auto=".3s", labels=dict(color="Applications"))
style_chart(fig_heat, "Country of asylum × nationality", max(420, 42 * len(matrix) + 120))
fig_heat.update_xaxes(title="Country of asylum")
fig_heat.update_yaxes(title="Nationality")
st.plotly_chart(fig_heat, use_container_width=True)

st.markdown('<div class="section-title">Geographic view</div>', unsafe_allow_html=True)
map_data = country_totals.copy()
code_lookup = {name: code for name,code in COUNTRIES.items()}
map_data["Code"] = map_data["Country of asylum"].map(code_lookup)
map_data["Latitude"] = map_data["Code"].map(lambda x: CAPITALS.get(x,(None,None,None))[0])
map_data["Longitude"] = map_data["Code"].map(lambda x: CAPITALS.get(x,(None,None,None))[1])
map_data["Capital"] = map_data["Code"].map(lambda x: CAPITALS.get(x,(None,None,None))[2])
map_data = map_data.dropna(subset=["Latitude","Longitude"])
max_val = map_data["First-time applications"].max()
map_data["Marker_Size"] = 12 + 28*(map_data["First-time applications"]/max_val).pow(.5) if max_val else 16
fig_map = px.scatter_map(
    map_data, lat="Latitude", lon="Longitude", size="Marker_Size", size_max=34, color="First-time applications",
    hover_name="Country of asylum", hover_data={"Capital":True,"First-time applications":":,.0f","Marker_Size":False,"Latitude":False,"Longitude":False},
    color_continuous_scale=["#80D4EE",UNHCR_BLUE,EU_BLUE], map_style="open-street-map", zoom=2.3, center={"lat":50,"lon":12}
)
fig_map.update_traces(marker=dict(opacity=.86))
fig_map.update_layout(title=dict(text="First-time applications by country of asylum",x=.02,y=.97,xanchor="left",yanchor="top",font=dict(size=18,color=NAVY)),height=560,margin=dict(l=8,r=8,t=65,b=8),paper_bgcolor="rgba(0,0,0,0)",coloraxis_colorbar=dict(title="Applications",thickness=12,len=.65))
st.plotly_chart(fig_map, use_container_width=True)

with st.expander("View and download the Eurostat observations"):
    table = df[["Date","Year","Month","Country of asylum","Nationality","First-time applications","Status"]].sort_values(["Date","Country of asylum","Nationality"],ascending=[False,True,True]).copy()
    table["Date"] = table["Date"].dt.strftime("%Y-%m")
    st.dataframe(table, use_container_width=True, hide_index=True)
    st.download_button("Download selected Eurostat data as CSV", table.to_csv(index=False).encode("utf-8"), "eurostat_first_time_asylum_applications.csv", "text/csv")

st.caption(f"Showing {len(df):,} monthly country-nationality observations. Source: Eurostat SDMX 3.0 API · {DATASET}.")
