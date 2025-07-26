# Duda Rechnungskontrolle

Eine Streamlit-Anwendung zur automatischen Kontrolle von Duda-Rechnungen gegen CRM-Workflow-Status.

## Funktionsweise

Die App gleicht monatliche Duda-Rechnungen mit dem CRM-Workflow-Status ab und identifiziert Seiten/Apps, die manuell kontrolliert werden sollten.

### Kontrollogik

**✅ OK (werden nicht angezeigt):**
- Sites mit `Should Charge = 1` und CRM-Status "Website online" (auch mit "gekündigt")
- Apps/Cookie Banner nur wenn zugehörige Site im Status "Website online" existiert

**⚠️ Manuelle Kontrolle erforderlich:**
- Sites werden abgerechnet, aber haben abweichenden Workflow-Status
- Sites werden abgerechnet, aber sind nicht im CRM zu finden
- Apps werden abgerechnet, aber zugehörige Site ist nicht "Website online"

### Produktkategorien

- **Lizenz**: `DudaOne Monthly` 
- **Shop**: Alles mit `ecom*` oder `store*`
- **CCB**: `Cookiebot Pro monthly`
- **Apps**: Alle anderen (AudioEye, Paperform, Feeds, etc.)

## Setup

### Lokale Entwicklung

```bash
git clone <repository-url>
cd duda-rechnungskontrolle
pip install -r requirements.txt
streamlit run app.py
```

### Deployment auf Streamlit Cloud

1. Repository auf GitHub veröffentlichen
2. Bei [streamlit.io](https://streamlit.io) anmelden
3. "New app" → Repository auswählen
4. App wird automatisch deployed

## Verwendung

1. **Duda-Rechnung hochladen**: CSV-Datei mit Format `roland.ertl@edelweiss-digital.at_YYYY_MM_*.csv`
2. **CRM-Export hochladen**: CSV-Datei mit Format `Projekte_*.csv`
3. **Analyse ausführen**: Automatische Kontrolle und Anzeige problematischer Einträge
4. **Export**: Download der Kontrollergebnisse als CSV

## Dateistruktur

```
duda-rechnungskontrolle/
├── app.py              # Hauptanwendung
├── requirements.txt    # Python-Abhängigkeiten
├── README.md          # Diese Dokumentation
└── utils/
    ├── __init__.py
    ├── file_processor.py   # CSV-Verarbeitung
    ├── data_analyzer.py    # Datenanalyse-Logik
    └── report_generator.py # Bericht-Generierung
```

## Technische Details

- **Framework**: Streamlit
- **Python**: 3.8+
- **Hauptbibliotheken**: pandas, streamlit, chardet (für Encoding-Erkennung)

## Support

Bei Problemen oder Fragen Repository Issues verwenden.
