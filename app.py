import streamlit as st
import pandas as pd
import chardet
from io import StringIO
from urllib.parse import urlparse
from datetime import datetime, timedelta

class FileProcessor:
    """Klasse für die Verarbeitung von CSV-Dateien"""
    
    def __init__(self):
        pass
    
    def detect_encoding(self, file_content):
        """Erkennt das Encoding einer Datei"""
        result = chardet.detect(file_content)
        return result['encoding']
    
    def extract_domain(self, url):
        """Extrahiert die Domain aus einer URL"""
        if not url or url == 'nan':
            return ''
            
        # URL normalisieren
        url = str(url).strip()
        if not url.startswith('http'):
            url = 'https://' + url
            
        try:
            parsed = urlparse(url)
            domain = parsed.netloc.lower()
            
            # www. entfernen für bessere Übereinstimmung
            if domain.startswith('www.'):
                domain = domain[4:]
                
            return domain
        except:
            # Fallback: einfache String-Manipulation
            url = url.replace('https://', '').replace('http://', '')
            domain = url.split('/')[0].lower()
            if domain.startswith('www.'):
                domain = domain[4:]
            return domain
    
    def fix_scientific_notation_ids(self, duda_df, crm_df):
        """Repariert Site IDs die als wissenschaftliche Notation fehlinterpretiert wurden"""
        
        # Finde Einträge mit wissenschaftlicher Notation
        scientific_mask = duda_df['Site Alias'].astype(str).str.contains(r'[eE][+-]', na=False, regex=True)
        problematic_rows = duda_df[scientific_mask].copy()
        
        if len(problematic_rows) == 0:
            return duda_df
        
        st.info(f"🔧 Repariere {len(problematic_rows)} Site IDs mit wissenschaftlicher Notation...")
        
        repairs_made = []
        repaired_scientific_ids = set()  # Track welche IDs bereits repariert wurden
        
        # Für jeden problematischen Eintrag
        for idx, row in problematic_rows.iterrows():
            site_alias_scientific = str(row['Site Alias']).strip()
            
            # Skip wenn diese ID bereits repariert wurde
            if site_alias_scientific in repaired_scientific_ids:
                continue
                
            site_url = str(row.get('Site URL', '')).strip()
            product_type = self.categorize_charge_frequency(row.get('Charge Frequency', ''))
            
            repaired = False
            
            # Strategie 1: Für CCB/Apps - suche nach URL bei anderen Einträgen mit derselben wissenschaftlichen Notation
            if product_type in ['CCB', 'Apps'] and (not site_url or site_url == 'nan'):
                # Finde andere Einträge mit derselben wissenschaftlichen Notation aber mit URL
                same_scientific_id = duda_df[
                    (duda_df['Site Alias'] == site_alias_scientific) & 
                    (duda_df['Site URL'].notna()) & 
                    (duda_df['Site URL'] != '') & 
                    (duda_df['Site URL'] != 'nan')
                ]
                
                if not same_scientific_id.empty:
                    # Nehme die URL vom ersten verfügbaren Eintrag (meist Lizenz)
                    site_url = str(same_scientific_id.iloc[0]['Site URL']).strip()
                    repairs_made.append(f"📋 {product_type} {site_alias_scientific}: URL von Lizenz-Eintrag übernommen ({site_url})")
            
            # Strategie 2: Domain-basierte Reparatur (für alle Produkttypen mit gültiger URL)
            if site_url and site_url != 'nan':
                # Domain aus URL extrahieren
                domain = self.extract_domain(site_url)
                
                # Im CRM nach dieser Domain suchen
                if 'Domain' in crm_df.columns:
                    crm_matches = crm_df[
                        crm_df['Domain'].astype(str).str.contains(
                            domain.replace('.', r'\.'), 
                            case=False, 
                            na=False, 
                            regex=True
                        )
                    ]
                    
                    if len(crm_matches) == 1:
                        # Eindeutige Übereinstimmung gefunden
                        correct_id = str(crm_matches.iloc[0]['Site-ID-Duda']).strip()
                        
                        # Alle Einträge mit dieser wissenschaftlichen Notation korrigieren
                        all_same_scientific = duda_df['Site Alias'] == site_alias_scientific
                        count_repaired = all_same_scientific.sum()
                        duda_df.loc[all_same_scientific, 'Site Alias'] = correct_id
                        
                        # Auch die Site URL für alle korrigieren falls leer
                        empty_url_mask = (
                            (duda_df['Site Alias'] == correct_id) & 
                            ((duda_df['Site URL'].isna()) | (duda_df['Site URL'] == '') | (duda_df['Site URL'] == 'nan'))
                        )
                        duda_df.loc[empty_url_mask, 'Site URL'] = site_url
                        
                        repairs_made.append(f"✅ {site_alias_scientific} → {correct_id} (via Domain: {domain}) - {count_repaired} Einträge")
                        repaired_scientific_ids.add(site_alias_scientific)
                        repaired = True
                        
                    elif len(crm_matches) > 1:
                        repairs_made.append(f"⚠️ Mehrere CRM-Einträge für Domain {domain}")
                    else:
                        repairs_made.append(f"❌ Keine CRM-Übereinstimmung für Domain {domain}")
                else:
                    repairs_made.append(f"❌ Keine Domain-Spalte im CRM gefunden")
            
            if not repaired and site_alias_scientific not in repaired_scientific_ids:
                repairs_made.append(f"❌ Konnte {site_alias_scientific} ({product_type}) nicht reparieren")
        
        # Reparatur-Log anzeigen
        if repairs_made:
            with st.expander("🔧 Details der Site ID Reparaturen"):
                for repair in repairs_made:
                    st.text(repair)
        
        return duda_df
    
    def load_duda_file(self, uploaded_file):
        """Lädt und verarbeitet eine Duda-Rechnungsdatei"""
        try:
            # Encoding erkennen
            file_content = uploaded_file.read()
            encoding = self.detect_encoding(file_content)
            
            # Als String dekodieren
            content_str = file_content.decode(encoding)
            
            # CSV parsen - Site Alias als String erzwingen um wissenschaftliche Notation zu vermeiden
            df = pd.read_csv(StringIO(content_str), dtype={'Site Alias': str})
            
            # Relevante Spalten prüfen
            required_columns = ['Site Alias', 'Site URL', 'Charge Frequency', 'Should Charge']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Fehlende Spalten in Duda-Datei: {missing_columns}")
            
            # Optional: Unpublication Date (für Kalendermonat-Regel)
            if 'Unpublication Date' not in df.columns:
                st.info("ℹ️ Keine 'Unpublication Date' Spalte gefunden - Kalendermonat-Regel wird nicht angewendet")
            
            # Site Alias als String erzwingen und problematische IDs reparieren
            df['Site Alias'] = df['Site Alias'].astype(str)
            
            # Datentypen korrigieren
            df['Should Charge'] = pd.to_numeric(df['Should Charge'], errors='coerce').fillna(0).astype(int)
            
            # Nur verrechenbare Einträge filtern
            df = df[df['Should Charge'] == 1].copy()
            
            return df
            
        except Exception as e:
            raise Exception(f"Fehler beim Laden der Duda-Datei: {str(e)}")
    
    def load_crm_file(self, uploaded_file):
        """Lädt und verarbeitet eine CRM-Exportdatei"""
        try:
            # Encoding erkennen
            file_content = uploaded_file.read()
            encoding = self.detect_encoding(file_content)
            
            # Als String dekodieren
            content_str = file_content.decode(encoding)
            
            # CSV parsen (Semikolon als Delimiter für deutsche CSV)
            df = pd.read_csv(StringIO(content_str), delimiter=';')
            
            # Verfügbare Spalten finden und Domain-Spalte identifizieren
            available_columns = df.columns.tolist()
            
            # Domain-Spalte finden
            domain_column = None
            for col in available_columns:
                if 'domain' in col.lower():
                    domain_column = col
                    break
            
            # Site-ID Spalten finden (Standard + Landingpage)
            site_id_column = None
            landingpage_id_column = None
            
            for col in available_columns:
                col_lower = col.lower()
                if 'duda' in col_lower and 'site' in col_lower and 'id' in col_lower:
                    # Exakte Übereinstimmung für Landingpage-Spalte
                    if col_lower in ['site-id-duda', 'site_id_duda']:
                        landingpage_id_column = col
                    # Standard-Spalte (Duda-Site-ID)
                    elif col_lower in ['duda-site-id', 'duda_site_id']:
                        site_id_column = col
            
            if site_id_column is None:
                raise ValueError("Keine Standard Duda-Site-ID Spalte gefunden")
            
            # Workflow-Status Spalte finden
            status_column = None
            for col in available_columns:
                if 'workflow' in col.lower() and 'status' in col.lower():
                    status_column = col
                    break
            
            if status_column is None:
                raise ValueError("Keine Workflow-Status Spalte gefunden")
            
            # Projektname Spalte finden
            project_column = None
            for col in available_columns:
                if 'projekt' in col.lower():
                    project_column = col
                    break
            
            # DataFrame mit standardisierten Spaltennamen erstellen
            result_df = pd.DataFrame()
            result_df['Site-ID-Duda'] = df[site_id_column]
            result_df['Workflow-Status'] = df[status_column]
            result_df['Domain'] = df[domain_column] if domain_column else ''
            result_df['Projektname'] = df[project_column] if project_column else 'Unbekannt'
            
            # Landingpage-IDs hinzufügen falls vorhanden
            if landingpage_id_column is not None:
                result_df['Landingpage-ID'] = df[landingpage_id_column]
            else:
                result_df['Landingpage-ID'] = ''
            
            # Leere Site-IDs entfernen und Datentyp korrigieren
            result_df = result_df[result_df['Site-ID-Duda'].notna()].copy()
            result_df['Site-ID-Duda'] = result_df['Site-ID-Duda'].astype(str).str.strip()
            
            # Landingpage-IDs bereinigen
            if landingpage_id_column is not None:
                result_df['Landingpage-ID'] = result_df['Landingpage-ID'].astype(str).str.strip()
                result_df.loc[result_df['Landingpage-ID'] == 'nan', 'Landingpage-ID'] = ''
            
            # WICHTIG: Zusätzliche Zeilen für Landingpages erstellen
            landingpage_rows = []
            if landingpage_id_column is not None:
                for idx, row in df.iterrows():
                    landingpage_id = row[landingpage_id_column]
                    if pd.notna(landingpage_id) and str(landingpage_id).strip() not in ['', 'nan']:
                        landingpage_id_clean = str(landingpage_id).strip()
                        
                        # Prüfe ob bereits in Standard-Spalte vorhanden
                        standard_ids = df[site_id_column].dropna().astype(str).str.strip().tolist()
                        
                        if landingpage_id_clean not in standard_ids:
                            # Neue Landingpage-Zeile erstellen
                            new_row = {
                                'Site-ID-Duda': landingpage_id_clean,
                                'Workflow-Status': str(row[status_column]).strip(),
                                'Domain': str(row[domain_column]).strip() if domain_column else '',
                                'Projektname': f"{str(row[project_column]).strip()} (Landingpage)" if project_column else 'Landingpage',
                                'Landingpage-ID': landingpage_id_clean
                            }
                            landingpage_rows.append(new_row)
                
                # Landingpage-Zeilen hinzufügen
                if landingpage_rows:
                    landingpage_df = pd.DataFrame(landingpage_rows)
                    result_df = pd.concat([result_df, landingpage_df], ignore_index=True)
            
            # Workflow-Status bereinigen
            result_df['Workflow-Status'] = result_df['Workflow-Status'].astype(str).str.strip()
            
            return result_df
            
        except Exception as e:
            raise Exception(f"Fehler beim Laden der CRM-Datei: {str(e)}")
    
    def categorize_charge_frequency(self, charge_frequency):
        """Kategorisiert Charge Frequency in Produkttypen"""
        if pd.isna(charge_frequency):
            return "Unbekannt"
        
        freq_lower = str(charge_frequency).lower()
        
        if "dudaone monthly" in freq_lower:
            return "Lizenz"
        elif any(term in freq_lower for term in ["ecom", "store"]):
            return "Shop"
        elif "cookiebot" in freq_lower:
            return "CCB"
        else:
            return "Apps"


class DataAnalyzer:
    """Klasse für die Datenanalyse und Identifikation von Problemen"""
    
    def __init__(self, duda_df, crm_df):
        self.duda_df = duda_df.copy()
        self.crm_df = crm_df.copy()
        self.processor = FileProcessor()
        
        # WICHTIG: Problematische Site IDs über Domain-Abgleich reparieren
        self.duda_df = self.processor.fix_scientific_notation_ids(self.duda_df, self.crm_df)
        
        # Produkttypen hinzufügen
        self.duda_df['Produkttyp'] = self.duda_df['Charge Frequency'].apply(
            self.processor.categorize_charge_frequency
        )
    
    def is_status_ok(self, status, unpublication_date=None):
        """Prüft ob ein Workflow-Status als OK gilt"""
        if pd.isna(status):
            return False
        
        status_str = str(status).lower()
        
        # Primär-Check: "Website online" ist immer OK
        if "website online" in status_str:
            return True
        
        # Sekundär-Check: Offline/gekündigt ist OK wenn kürzlich unpublished (≤31 Tage)
        if any(term in status_str for term in ["offline", "gekündigt"]):
            if unpublication_date and not pd.isna(unpublication_date):
                days_since_unpublish = self.days_since_unpublication(unpublication_date)
                if days_since_unpublish is not None and days_since_unpublish <= 31:
                    return True  # Kürzlich offline → noch berechtigt verrechnet
        
        return False
    
    def days_since_unpublication(self, unpublication_date):
        """Berechnet Tage seit Unpublication Date"""
        if pd.isna(unpublication_date) or str(unpublication_date).strip() in ['', 'nan']:
            return None
            
        try:
            # Verschiedene Datumsformate versuchen
            date_str = str(unpublication_date).strip()
            
            # Common formats: YYYY-MM-DD, MM/DD/YYYY, DD.MM.YYYY, etc.
            formats_to_try = [
                '%Y-%m-%d',
                '%m/%d/%Y', 
                '%d.%m.%Y',
                '%Y-%m-%d %H:%M:%S',
                '%m/%d/%Y %H:%M:%S',
                '%d.%m.%Y %H:%M:%S'
            ]
            
            unpublish_date = None
            for fmt in formats_to_try:
                try:
                    unpublish_date = datetime.strptime(date_str, fmt)
                    break
                except ValueError:
                    continue
            
            if unpublish_date is None:
                return None
                
            # Tage zwischen unpublish_date und heute
            today = datetime.now()
            delta = today - unpublish_date
            return delta.days
            
        except Exception:
            return None
    
    def find_issues(self):
        """Findet alle problematischen Einträge"""
        issues = []
        
        for _, duda_row in self.duda_df.iterrows():
            site_alias = str(duda_row['Site Alias']).strip()
            unpublication_date = duda_row.get('Unpublication Date', None)
            
            # CRM-Eintrag suchen - direkte Suche in der kombinierten Site-ID-Duda Spalte
            crm_match = self.crm_df[self.crm_df['Site-ID-Duda'] == site_alias]
            
            if crm_match.empty:
                # Site nicht im CRM gefunden
                issues.append({
                    'Site_Alias': site_alias,
                    'Site_URL': duda_row.get('Site URL', ''),
                    'Produkttyp': duda_row['Produkttyp'],
                    'Charge_Frequency': duda_row['Charge Frequency'],
                    'CRM_Status': 'Nicht gefunden',
                    'Projektname': 'Nicht gefunden',
                    'Problem_Typ': 'Site nicht im CRM',
                    'Unpublish_Tage': self.days_since_unpublication(unpublication_date) if unpublication_date else None
                })
            
            else:
                # CRM-Eintrag gefunden, Status prüfen
                crm_row = crm_match.iloc[0]
                workflow_status = crm_row['Workflow-Status']
                
                if not self.is_status_ok(workflow_status, unpublication_date):
                    # Für Apps: Prüfen ob es eine zugehörige "Website online" Site gibt
                    if duda_row['Produkttyp'] in ['CCB', 'Apps']:
                        # Prüfen ob es eine Lizenz-Site mit gleichem Alias und OK-Status gibt
                        license_match = self.duda_df[
                            (self.duda_df['Site Alias'] == site_alias) & 
                            (self.duda_df['Produkttyp'] == 'Lizenz')
                        ]
                        
                        if not license_match.empty:
                            # Es gibt eine Lizenz-Site, prüfe deren Status auch mit unpublication_date
                            license_unpublish = license_match.iloc[0].get('Unpublication Date', None)
                            if self.is_status_ok(workflow_status, license_unpublish):
                                continue
                        
                        # Sonst ist es ein Problem
                        issues.append({
                            'Site_Alias': site_alias,
                            'Site_URL': duda_row.get('Site URL', ''),
                            'Produkttyp': duda_row['Produkttyp'],
                            'Charge_Frequency': duda_row['Charge Frequency'],
                            'CRM_Status': workflow_status,
                            'Projektname': crm_row['Projektname'],
                            'Problem_Typ': f'{duda_row["Produkttyp"]} ohne Website online',
                            'Unpublish_Tage': self.days_since_unpublication(unpublication_date) if unpublication_date else None
                        })
                    
                    else:
                        # Für Lizenzen und Shops: Status muss OK sein (inkl. unpublication_date check)
                        days_unpublished = self.days_since_unpublication(unpublication_date) if unpublication_date else None
                        
                        issues.append({
                            'Site_Alias': site_alias,
                            'Site_URL': duda_row.get('Site URL', ''),
                            'Produkttyp': duda_row['Produkttyp'],
                            'Charge_Frequency': duda_row['Charge Frequency'],
                            'CRM_Status': workflow_status,
                            'Projektname': crm_row['Projektname'],
                            'Problem_Typ': 'Abweichender Workflow-Status',
                            'Unpublish_Tage': days_unpublished
                        })
        
        return pd.DataFrame(issues)
    
    def get_summary(self):
        """Erstellt eine Zusammenfassung der Analyse"""
        total_charged = len(self.duda_df)
        issues_df = self.find_issues()
        issues_count = len(issues_df)
        ok_count = total_charged - issues_count
        
        # Breakdown nach Produkttyp
        product_breakdown = {}
        for product_type in self.duda_df['Produkttyp'].unique():
            product_total = len(self.duda_df[self.duda_df['Produkttyp'] == product_type])
            product_issues = len(issues_df[issues_df['Produkttyp'] == product_type]) if not issues_df.empty else 0
            product_ok = product_total - product_issues
            
            product_breakdown[product_type] = {
                'total': product_total,
                'ok': product_ok,
                'issues': product_issues
            }
        
        return {
            'total_charged': total_charged,
            'ok_count': ok_count,
            'issues_count': issues_count,
            'product_breakdown': product_breakdown
        }


class ReportGenerator:
    """Klasse für die Generierung von Berichten"""
    
    def __init__(self):
        pass
    
    def generate_csv_report(self, issues_df, summary):
        """Generiert einen CSV-Bericht der Kontrollergebnisse"""
        output = StringIO()
        
        # Header mit Zusammenfassung
        output.write("# Duda Rechnungskontrolle - Bericht\n")
        output.write(f"# Datum: {pd.Timestamp.now().strftime('%d.%m.%Y %H:%M')}\n")
        output.write("#\n")
        output.write(f"# Zusammenfassung:\n")
        output.write(f"# - Gesamt verrechnet: {summary['total_charged']}\n")
        output.write(f"# - OK (Website online): {summary['ok_count']}\n")
        output.write(f"# - Manuelle Kontrolle: {summary['issues_count']}\n")
        output.write("#\n")
        
        # Produkttyp-Breakdown
        if summary['product_breakdown']:
            output.write("# Breakdown nach Produkttyp:\n")
            for product, data in summary['product_breakdown'].items():
                output.write(f"# - {product}: {data['total']} gesamt, {data['ok']} OK, {data['issues']} Probleme\n")
            output.write("#\n")
        
        output.write("# Problematische Einträge:\n")
        output.write("#\n")
        
        # Problematische Einträge als CSV
        if not issues_df.empty:
            # DataFrame zu CSV konvertieren
            csv_string = issues_df.to_csv(index=False, sep=';', encoding='utf-8')
            output.write(csv_string)
        else:
            output.write("Site_Alias;Site_URL;Produkttyp;Charge_Frequency;CRM_Status;Projektname;Problem_Typ\n")
            output.write("# Keine problematischen Einträge gefunden!\n")
        
        return output.getvalue()


def main():
    st.set_page_config(
        page_title="Duda Rechnungskontrolle",
        page_icon="💰",
        layout="wide"
    )
    
    st.title("💰 Duda Rechnungskontrolle")
    st.markdown("---")
    
    # Sidebar für File Upload
    with st.sidebar:
        st.header("📁 Dateien hochladen")
        
        # Duda Rechnung Upload
        st.subheader("Duda Rechnung")
        duda_file = st.file_uploader(
            "CSV-Datei mit Duda-Rechnung",
            type=['csv'],
            help="Format: roland.ertl@edelweiss-digital.at_YYYY_MM_*.csv",
            key="duda_upload"
        )
        
        # CRM Export Upload
        st.subheader("CRM Export")
        crm_file = st.file_uploader(
            "CSV-Datei mit CRM-Daten",
            type=['csv'],
            help="Format: Projekte_*.csv",
            key="crm_upload"
        )
        
        # Info Box
        with st.expander("ℹ️ Hinweise"):
            st.markdown("""
            **Kontrollogik:**
            - ✅ OK: Sites mit 'Website online' Status
            - ✅ OK: Sites mit 'offline/gekündigt' Status, aber unpublished ≤31 Tage (Kalendermonat-Regel)
            - ⚠️ Kontrolle: Abweichender Status oder nicht im CRM gefunden
            
            **Produkttypen:**
            - Lizenz: DudaOne Monthly
            - Shop: ecom*/store*
            - CCB: Cookiebot Pro monthly
            - Apps: AudioEye, Paperform, etc.
            
            **Kalendermonat-Regel:**
            Sites die im aktuellen Abrechnungsmonat offline gingen, werden noch voll verrechnet.
            
            **App Version: v16** 🔄 - Unpublication Date Logik hinzugefügt
            """)
        
        # Version Info auch als kleine Badge
        st.sidebar.markdown("---")
        st.sidebar.markdown("*App Version: v16*", help="Unpublication Date Berücksichtigung")
    
    # Main Content
    if duda_file is not None and crm_file is not None:
        try:
            # Dateien verarbeiten
            with st.spinner("Dateien werden verarbeitet..."):
                processor = FileProcessor()
                
                # Duda Rechnung laden
                duda_df = processor.load_duda_file(duda_file)
                
                # CRM Daten laden
                crm_df = processor.load_crm_file(crm_file)
            
            # Datenanalyse
            with st.spinner("Daten werden analysiert..."):
                analyzer = DataAnalyzer(duda_df, crm_df)
                issues = analyzer.find_issues()
                summary = analyzer.get_summary()
            
            # Ergebnisse anzeigen
            display_results(issues, summary, duda_df, crm_df)
            
        except Exception as e:
            st.error(f"Fehler beim Verarbeiten der Dateien: {str(e)}")
            st.exception(e)
    
    else:
        # Placeholder wenn keine Dateien geladen
        st.info("👆 Bitte lade beide CSV-Dateien in der Sidebar hoch, um die Analyse zu starten.")
        
        # Demo-Info
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("🔍 Was macht diese App?")
            st.markdown("""
            - Automatische Kontrolle von Duda-Rechnungen
            - Abgleich mit CRM-Workflow-Status
            - Identifikation von Unstimmigkeiten
            - Export der Kontrollergebnisse
            """)
        
        with col2:
            st.subheader("📊 Analyse-Features")
            st.markdown("""
            - Zusammenfassung nach Produkttypen
            - Liste aller problematischen Einträge
            - Downloadbare Berichte
            - Übersichtliche Darstellung
            """)


def display_results(issues, summary, duda_df, crm_df):
    """Zeigt die Analyseergebnisse an"""
    
    # Zusammenfassung
    st.header("📊 Zusammenfassung")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        st.metric(
            "Gesamt verrechnet",
            summary['total_charged'],
            help="Anzahl aller verrechenbaren Einträge"
        )
    
    with col2:
        st.metric(
            "OK (Website online)",
            summary['ok_count'],
            help="Sites mit korrektem Status"
        )
    
    with col3:
        st.metric(
            "⚠️ Manuelle Kontrolle",
            summary['issues_count'],
            delta=f"-{summary['issues_count']} Probleme",
            delta_color="inverse"
        )
    
    with col4:
        if summary['issues_count'] > 0:
            percentage = round((summary['issues_count'] / summary['total_charged']) * 100, 1)
            st.metric(
                "Problemrate",
                f"{percentage}%",
                help="Anteil problematischer Einträge"
            )
        else:
            st.metric("Problemrate", "0%")
    
    # Produkttyp-Breakdown
    if summary['product_breakdown']:
        st.subheader("📋 Breakdown nach Produkttyp")
        
        breakdown_df = pd.DataFrame([
            {
                'Produkttyp': product,
                'OK': data['ok'],
                'Probleme': data['issues'],
                'Gesamt': data['total']
            }
            for product, data in summary['product_breakdown'].items()
        ])
        
        st.dataframe(
            breakdown_df,
            use_container_width=True,
            hide_index=True
        )
    
    # Problematische Einträge
    if not issues.empty:
        st.header("⚠️ Manuelle Kontrolle erforderlich")
        
        # Filter für Problemtyp
        problem_types = issues['Problem_Typ'].unique()
        selected_type = st.selectbox(
            "Filter nach Problemtyp:",
            ['Alle'] + list(problem_types),
            key="problem_filter"
        )
        
        filtered_issues = issues if selected_type == 'Alle' else issues[issues['Problem_Typ'] == selected_type]
        
        # Site ID Links für Duda Dashboard hinzufügen
        filtered_issues_display = filtered_issues.copy()
        filtered_issues_display['Duda_Dashboard'] = filtered_issues_display['Site_Alias'].apply(
            lambda x: f"https://my.duda.co/home/dashboard/overview/{x}" if pd.notna(x) and str(x).strip() else ""
        )
        
        # Unpublish-Tage für bessere Verständlichkeit formatieren
        if 'Unpublish_Tage' in filtered_issues_display.columns:
            filtered_issues_display['Offline_seit'] = filtered_issues_display['Unpublish_Tage'].apply(
                lambda x: f"{x} Tage" if pd.notna(x) and x is not None else "Unbekannt"
            )
        
        # Anzeige der Probleme
        st.dataframe(
            filtered_issues_display,
            use_container_width=True,
            hide_index=True,
            column_config={
                'Site_Alias': 'Site ID',
                'Site_URL': st.column_config.LinkColumn('Site URL'),
                'Duda_Dashboard': st.column_config.LinkColumn(
                    'Duda Dashboard',
                    help="Direkt zum Duda-Dashboard"
                ),
                'Produkttyp': 'Produkt',
                'CRM_Status': 'CRM Status',
                'Problem_Typ': 'Problem',
                'Projektname': 'Projekt',
                'Offline_seit': 'Offline seit',
                'Unpublish_Tage': None  # Hide raw number column
            }
        )
        
        # Download-Button
        report_gen = ReportGenerator()
        csv_data = report_gen.generate_csv_report(filtered_issues, summary)
        
        st.download_button(
            label="📥 Bericht als CSV herunterladen",
            data=csv_data,
            file_name=f"duda_kontrolle_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
            mime="text/csv"
        )
    
    else:
        st.success("🎉 Alle Einträge sind in Ordnung! Keine manuelle Kontrolle erforderlich.")
    
    # Debug Info (ausklappbar)
    with st.expander("🔧 Debug-Informationen"):
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Duda-Daten")
            st.text(f"Zeilen: {len(duda_df)}")
            st.text(f"Verrechenbare: {len(duda_df[duda_df['Should Charge'] == 1])}")
            
        with col2:
            st.subheader("CRM-Daten")
            st.text(f"Zeilen: {len(crm_df)}")
            with_duda_id = len(crm_df[crm_df['Site-ID-Duda'].notna()])
            st.text(f"Mit Standard Duda-ID: {with_duda_id}")
            
            # Landingpage-IDs prüfen falls vorhanden
            if 'Landingpage-ID' in crm_df.columns:
                with_landingpage_id = len(crm_df[
                    (crm_df['Landingpage-ID'].notna()) & 
                    (crm_df['Landingpage-ID'] != '') & 
                    (crm_df['Landingpage-ID'] != 'nan')
                ])
                st.text(f"Mit Landingpage-ID: {with_landingpage_id}")
                
                # Gesamtanzahl einzigartiger IDs
                all_ids = set()
                all_ids.update(crm_df['Site-ID-Duda'].dropna().astype(str).str.strip())
                if 'Landingpage-ID' in crm_df.columns:
                    landingpage_ids = crm_df['Landingpage-ID'].dropna().astype(str).str.strip()
                    landingpage_ids = landingpage_ids[landingpage_ids != 'nan']
                    all_ids.update(landingpage_ids)
                st.text(f"Einzigartige IDs gesamt: {len(all_ids)}")
            else:
                st.text("Keine Landingpage-Spalte gefunden")
                
        # Zeige Information über Unpublication Date Feature
        with st.expander("📅 Kalendermonat-Regel"):
            st.markdown("""
            **Neue Logik:** Sites mit Status 'offline' oder 'gekündigt' sind OK, wenn sie vor ≤31 Tagen unpublished wurden.
            
            **Beispiel:**
            - Site unpublished am 15. Juni
            - CRM Status: "gekündigt, Website offline"  
            - Heute: 20. Juni (5 Tage später)
            - **Ergebnis: ✅ OK** (weil ≤31 Tage, noch im Abrechnungsmonat)
            
            **Ohne Unpublication Date:** Nur "Website online" Status gilt als OK.
            """)
            
            # Zeige ob Unpublication Date verfügbar ist
            has_unpublish_col = 'Unpublication Date' in duda_df.columns if 'duda_df' in locals() else False
            if has_unpublish_col:
                st.success("✅ Unpublication Date Spalte gefunden - Kalendermonat-Regel aktiv")
            else:
                st.warning("⚠️ Keine Unpublication Date Spalte - nur Standard-Logik aktiv")


if __name__ == "__main__":
    main()
