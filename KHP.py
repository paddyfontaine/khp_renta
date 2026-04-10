import streamlit as st
import pandas as pd
import plotly.express as px

# =========================================
# App-Setup
# =========================================
st.set_page_config(page_title="Online-Rentabilität Analyse", layout="wide")
st.title("📊 Online-Rentabilität Analyse Tool")

st.markdown("""
Lade deine Minubo-CSV-Datei hoch.  
Das Tool berechnet automatisch die wichtigsten Rentabilitätskennzahlen und zeigt dir Tabellen & Diagramme.
""")

# =========================================
# Spalten-Mapping (Exportnamen → Standard)
# =========================================
SPALTEN_MAPPING = {
    "Standort": ["Standort", "Lager > Gruppe > Ebene 1"],
    "Category": ["Category", "Produkt > Linie > Name"],
    "Zeitraum": ["Zeitraum", "Datenreihe"],
    "Bestellungen": ["Bestellungen", "Verkäufe (FD)"],
    "Verkaufsmenge": ["Verkaufsmenge", "Verkaufsmenge (FD)"],
    "Bestellwert": ["Bestellwert", "Warenwert in Verkäufen (FD)"],
    "Umsatz nach Retoure": ["Umsatz nach Retoure", "Warenwert in Netto-Verkäufen (FD,RD)"],
    "Anzahl Retouren": ["Anzahl Retouren", "Retouren (RD)"],
    "erzielte Spanne": ["erzielte Spanne"],
    "Produktkategorie": ["Produktkategorie", "Produkt > SKU > Attribut 4"],
}

NUMERIC_COLS = [
    "Bestellungen", "Verkaufsmenge", "Bestellwert",
    "Umsatz nach Retoure", "Anzahl Retouren", "erzielte Spanne"
]

GROUPABLE = ["Zeitraum", "Category", "Standort", "Produktkategorie"]

RAW_METRICS = [
    "Bestellungen",
    "Verkaufsmenge",
    "Bestellwert",
    "Umsatz nach Retoure",
    "Anzahl Retouren",
    "erzielte Spanne",
]

CALC_METRICS = [
    "Deckungsbeitrag",
    "DB2",
    "DB2 %",
    "Retourenquote %",
    "ø Warenwert pro Bon",
    "ø Warenwert pro Artikel",
    "ø Teile pro Warenkorb",
]

COST_METRICS = [
    "Verpackungskosten",
    "Versandkosten",
    "Versandnebenkosten",
    "Retourenkosten",
    "Provision",
    "Personalkosten Versand",
    "Personalkosten Retoure",
    "Gesamtkosten",
]

def finde_spalte(df: pd.DataFrame, suchliste: list) -> str:
    for name in suchliste:
        if name in df.columns:
            return name
    return None

def convert_column_to_float(df: pd.DataFrame, col: str) -> pd.DataFrame:
    df[col] = (
        df[col].astype(str)
        .str.replace('€', '', regex=False)
        .str.replace(' ', '', regex=False)
        .str.replace('.', '', regex=False)
        .str.replace(',', '.', regex=False)
    )
    df[col] = pd.to_numeric(df[col], errors='coerce')
    return df

# =========================================
# Kostenparameter (Sidebar)
# =========================================
st.sidebar.header("⚙️ Variable Kostenparameter")
KOSTEN = {
    "Versandkosten": st.sidebar.number_input("Versandkosten pro Bestellung (€)", value=3.79, step=0.1),
    "Versandnebenkosten": st.sidebar.number_input("Versandnebenkosten pro Bestellung (€)", value=0.44, step=0.1),
    "Retourenkosten": st.sidebar.number_input("Retourenkosten pro Retoure (€)", value=4.19, step=0.1),
    "Personalkosten_Stunde": st.sidebar.number_input("Personalkosten pro Stunde (€)", value=18.0, step=0.5),
    "Versandzeit_Min": st.sidebar.number_input("Bearbeitungszeit Versand (Min.)", value=7.0, step=0.5),
    "Retourenzeit_Min": st.sidebar.number_input("Bearbeitungszeit Retoure (Min.)", value=3.5, step=0.5),
    "Provision_%": st.sidebar.number_input("Provision (%)", value=15.47, step=0.1),
    "Verpackungskosten": st.sidebar.number_input("Verpackungskosten pro Bestellung (€)", value=0.70, step=0.1),
}

# =========================================
# Datei-Upload
# =========================================
uploaded_file = st.file_uploader("CSV-Datei hochladen", type=["csv"])

if uploaded_file:
    # Einlesen
    df_raw = pd.read_csv(uploaded_file, sep=";", encoding="utf-8")
    df_raw.columns = df_raw.columns.str.strip()

    # Mapping anwenden → Standardnamen verwenden
    mapping = {}
    for ziel, varianten in SPALTEN_MAPPING.items():
        gefunden = finde_spalte(df_raw, varianten)
        if gefunden:
            mapping[gefunden] = ziel
    master_df = df_raw.rename(columns=mapping)

    # Numerische Spalten konvertieren (falls vorhanden)
    for col in NUMERIC_COLS:
        if col in master_df.columns:
            master_df = convert_column_to_float(master_df, col)

    # =========================================
    # Berechnungen (Zeilenebene)
    # =========================================
    # Quoten/Ø
    master_df['Retourenquote %'] = 100 - (master_df['Umsatz nach Retoure'] / master_df['Bestellwert']) * 100
    master_df['ø Warenwert pro Bon'] = master_df['Bestellwert'] / master_df['Bestellungen']
    master_df['ø Warenwert pro Artikel'] = master_df['Bestellwert'] / master_df['Verkaufsmenge']
    master_df['ø Teile pro Warenkorb'] = master_df['Verkaufsmenge'] / master_df['Bestellungen']
    # Kosten
    master_df['Verpackungskosten'] = master_df['Bestellungen'] * KOSTEN["Verpackungskosten"]
    master_df['Versandkosten'] = master_df['Bestellungen'] * KOSTEN["Versandkosten"]
    master_df['Versandnebenkosten'] = master_df['Bestellungen'] * KOSTEN["Versandnebenkosten"]
    master_df['Retourenkosten'] = master_df['Anzahl Retouren'] * KOSTEN["Retourenkosten"]
    master_df['Provision'] = master_df['Umsatz nach Retoure'] * (KOSTEN["Provision_%"] / 100)
    master_df['Personalkosten Versand'] = master_df['Bestellungen'] * KOSTEN["Versandzeit_Min"] * (KOSTEN["Personalkosten_Stunde"] / 60)
    master_df['Personalkosten Retoure'] = master_df['Anzahl Retouren'] * KOSTEN["Retourenzeit_Min"] * (KOSTEN["Personalkosten_Stunde"] / 60)
    master_df['Gesamtkosten'] = (
        master_df['Verpackungskosten']
        + master_df['Versandkosten']
        + master_df['Versandnebenkosten']
        + master_df['Retourenkosten']
        + master_df['Provision']
        + master_df['Personalkosten Versand']
        + master_df['Personalkosten Retoure']
    )
    # Deckungsbeitrag/DB2
    master_df['Deckungsbeitrag'] = master_df['Umsatz nach Retoure'] * (master_df['erzielte Spanne'] / 100)
    master_df['DB2'] = master_df['Deckungsbeitrag'] - master_df['Gesamtkosten']
    master_df['DB2 %'] = (master_df['DB2'] / master_df['Umsatz nach Retoure']) * 100

    st.success("✅ Datei erfolgreich verarbeitet! Alle Kennzahlen wurden berechnet.")

    # =========================================
    # Filter
    # =========================================
    st.sidebar.header("📌 Filter")
    standort_filter = st.sidebar.selectbox(
        "Standort wählen",
        ["Alle"] + (sorted(master_df['Standort'].dropna().unique()) if "Standort" in master_df.columns else []),
    ) if "Standort" in master_df.columns else None

    category_filter = st.sidebar.selectbox(
        "Category wählen",
        ["Alle"] + (sorted(master_df['Category'].dropna().unique()) if "Category" in master_df.columns else []),
    ) if "Category" in master_df.columns else None

    zeitraum_options = (
        sorted(master_df['Zeitraum'].dropna().unique())
        if "Zeitraum" in master_df.columns
        else []
    )
    show_ist = show_vergleich = False
    ist_zeitraum = vergleich_zeitraum = None
    if zeitraum_options:
        show_ist = st.sidebar.checkbox("Ist-Zeitraum anzeigen", value=True)
        if len(zeitraum_options) > 1:
            show_vergleich = st.sidebar.checkbox("Vergleichszeitraum anzeigen", value=True)
        ist_zeitraum = zeitraum_options[0]
        vergleich_zeitraum = zeitraum_options[1] if len(zeitraum_options) > 1 else None

    produktkat_filter = st.sidebar.selectbox(
        "Produktkategorie wählen",
        ["Alle"] + (sorted(master_df['Produktkategorie'].dropna().unique()) if "Produktkategorie" in master_df.columns else []),
    ) if "Produktkategorie" in master_df.columns else None

    df_filtered = master_df.copy()
    if standort_filter and standort_filter != "Alle":
        df_filtered = df_filtered[df_filtered['Standort'] == standort_filter]
    if category_filter and category_filter != "Alle":
        df_filtered = df_filtered[df_filtered['Category'] == category_filter]
    periods = []
    if show_ist and ist_zeitraum:
        periods.append(ist_zeitraum)
    if show_vergleich and vergleich_zeitraum:
        periods.append(vergleich_zeitraum)
    if periods:
        df_filtered = df_filtered[df_filtered['Zeitraum'].isin(periods)]
    if produktkat_filter and produktkat_filter != "Alle":
        df_filtered = df_filtered[df_filtered['Produktkategorie'] == produktkat_filter]

    # =========================================
    # Gruppierung
    # =========================================
    gruppenwahl = st.selectbox("Gruppierung wählen:", [g for g in GROUPABLE if g in df_filtered.columns] or ["Zeitraum"])

    if gruppenwahl in df_filtered.columns:
        agg_cols = [
            "Bestellungen",
            "Verkaufsmenge",
            "Bestellwert",
            "Umsatz nach Retoure",
            "Anzahl Retouren",
            "Deckungsbeitrag",
            "Verpackungskosten",
            "Versandkosten",
            "Versandnebenkosten",
            "Retourenkosten",
            "Provision",
            "Personalkosten Versand",
            "Personalkosten Retoure",
        ]
        group_cols = [gruppenwahl]
        if gruppenwahl != "Zeitraum" and "Zeitraum" in df_filtered.columns:
            group_cols.append("Zeitraum")
        summary = df_filtered.groupby(group_cols)[agg_cols].sum().reset_index()
        if "erzielte Spanne" in df_filtered.columns:
            spanne = (
                df_filtered.groupby(group_cols)["erzielte Spanne"].mean().reset_index()
            )
            summary = summary.merge(spanne, on=group_cols, how="left")
        summary["Gesamtkosten"] = (
            summary["Verpackungskosten"]
            + summary["Versandkosten"]
            + summary["Versandnebenkosten"]
            + summary["Retourenkosten"]
            + summary["Provision"]
            + summary["Personalkosten Versand"]
            + summary["Personalkosten Retoure"]
        )
        summary["DB2"] = summary["Deckungsbeitrag"] - summary["Gesamtkosten"]

        # Verhältniskennzahlen nach Aggregation
        summary["Retourenquote %"] = 100 - (
            summary["Umsatz nach Retoure"] / summary["Bestellwert"]
        ) * 100
        summary["ø Warenwert pro Bon"] = summary["Bestellwert"] / summary["Bestellungen"]
        summary["ø Warenwert pro Artikel"] = summary["Bestellwert"] / summary["Verkaufsmenge"]
        summary["ø Teile pro Warenkorb"] = summary["Verkaufsmenge"] / summary["Bestellungen"]
        summary["DB2 %"] = (
            summary["DB2"] / summary["Umsatz nach Retoure"]
        ) * 100

        # =========================================
        # Tabelle mit Formatierung
        # =========================================
        format_dict = {
            "DB2 %": "{:.2f} %",
            "Retourenquote %": "{:.2f} %",
            "erzielte Spanne": "{:.2f} %",
            "ø Warenwert pro Bon": "{:.2f} €",
            "ø Warenwert pro Artikel": "{:.2f} €",
            "Bestellwert": "{:.2f} €",
            "Umsatz nach Retoure": "{:.2f} €",
            "Deckungsbeitrag": "{:.2f} €",
            "Verpackungskosten": "{:.2f} €",
            "Versandkosten": "{:.2f} €",
            "Versandnebenkosten": "{:.2f} €",
            "Retourenkosten": "{:.2f} €",
            "Provision": "{:.2f} €",
            "Personalkosten Versand": "{:.2f} €",
            "Personalkosten Retoure": "{:.2f} €",
            "Gesamtkosten": "{:.2f} €",
            "DB2": "{:.2f} €",
        }

        col_map = {}
        if show_ist and ist_zeitraum:
            col_map[ist_zeitraum] = f"Ist ({ist_zeitraum})"
        if show_vergleich and vergleich_zeitraum:
            col_map[vergleich_zeitraum] = f"Vergleich ({vergleich_zeitraum})"

        if "Zeitraum" in summary.columns:
            summary["Zeitraum"] = summary["Zeitraum"].map(col_map).fillna(summary["Zeitraum"])
            order = []
            if show_ist and ist_zeitraum:
                order.append(col_map.get(ist_zeitraum))
            if show_vergleich and vergleich_zeitraum:
                order.append(col_map.get(vergleich_zeitraum))
            if order:
                summary["Zeitraum"] = pd.Categorical(summary["Zeitraum"], categories=order, ordered=True)
            summary.sort_values(group_cols, inplace=True)

        summary_display = summary

        def match_metrics(names: list[str]) -> list[str]:
            return [
                col
                for col in summary_display.columns
                if col not in group_cols and any(col.startswith(n) for n in names)
            ]

        given_options = match_metrics(RAW_METRICS)
        calc_options = match_metrics(CALC_METRICS)
        cost_options = match_metrics(COST_METRICS)

        selected_given = st.multiselect(
            "Gegebene Werte",
            given_options,
            default=given_options,
        )
        selected_calc = st.multiselect(
            "Berechnete Werte",
            calc_options,
            default=calc_options,
        )
        selected_cost = st.multiselect(
            "Kosten",
            cost_options,
            default=cost_options,
        )
        selected_metrics = selected_given + selected_calc + selected_cost

        st.subheader("📑 Auswertungstabelle")
        st.dataframe(
            summary_display[group_cols + selected_metrics].style.format(
                {
                    k: format_dict.get(k, "{}")
                    for k in selected_metrics
                    if k in format_dict
                }
            )
        )

        # =========================================
        # 2×2-Grid: Charts mit Plotly
        # =========================================
        def plot_bar(data, y_col, title, y_label, suffix=""):
            fig = px.bar(
                data,
                x=gruppenwahl if gruppenwahl != "Zeitraum" else "Zeitraum",
                y=y_col,
                color="Zeitraum" if ("Zeitraum" in data.columns and gruppenwahl != "Zeitraum") else None,
                barmode="group",
                text=data[y_col].map(lambda v: f"{v:.2f}{suffix}"),
            )
            fig.update_traces(textposition="outside")
            fig.update_layout(title=title, yaxis_title=y_label, xaxis_tickangle=-45)
            return fig

        c1, c2 = st.columns(2)
        with c1:
            if "DB2 %" in summary.columns:
                st.plotly_chart(
                    plot_bar(
                        summary,
                        "DB2 %",
                        f"DB2 % nach {gruppenwahl}",
                        "DB2 %",
                        suffix=" %",
                    ),
                    use_container_width=True,
                )
        with c2:
            if "Retourenquote %" in summary.columns:
                st.plotly_chart(
                    plot_bar(
                        summary,
                        "Retourenquote %",
                        f"Retourenquote % nach {gruppenwahl}",
                        "Retourenquote %",
                        suffix=" %",
                    ),
                    use_container_width=True,
                )

        c3, c4 = st.columns(2)
        with c3:
            if "erzielte Spanne" in summary.columns:
                st.plotly_chart(
                    plot_bar(
                        summary,
                        "erzielte Spanne",
                        f"Erzielte Spanne (Ø) nach {gruppenwahl}",
                        "Spanne",
                        suffix=" %",
                    ),
                    use_container_width=True,
                )
        with c4:
            if "ø Warenwert pro Artikel" in summary.columns:
                st.plotly_chart(
                    plot_bar(
                        summary,
                        "ø Warenwert pro Artikel",
                        f"ø Warenwert pro Artikel nach {gruppenwahl}",
                        "ø Warenwert pro Artikel",
                        suffix=" €",
                    ),
                    use_container_width=True,
                )

        c5, c6 = st.columns(2)
        with c5:
            if "Gesamtkosten" in summary.columns:
                st.plotly_chart(
                    plot_bar(
                        summary,
                        "Gesamtkosten",
                        f"Gesamtkosten nach {gruppenwahl}",
                        "Gesamtkosten",
                        suffix=" €",
                    ),
                    use_container_width=True,
                )
        with c6:
            if "DB2" in summary.columns:
                st.plotly_chart(
                    plot_bar(
                        summary,
                        "DB2",
                        f"DB2 nach {gruppenwahl}",
                        "DB2",
                        suffix=" €",
                    ),
                    use_container_width=True,
                )

    # =========================================
    # Download
    # =========================================
    st.download_button(
        label="📥 Ergebnisse als CSV herunterladen",
        data=master_df.to_csv(index=False, sep=";").encode('utf-8'),
        file_name="Rentabilitäts-Auswertung.csv",
        mime="text/csv",
    )

else:
    st.info("Bitte lade eine CSV-Datei hoch, um die Analyse zu starten.")