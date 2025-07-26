import pandas as pd
import chardet
from io import StringIO

class FileProcessor:
    """Klasse für die Verarbeitung von CSV-Dateien"""
    
    def __init__(self):
        pass
    
    def fix_scientific_notation_ids(self, duda_df, crm_df):
        """Repariert Site IDs die als wissenschaftliche Notation fehlinterpretiert wurden"""
        
        # Finde Einträge mit wissenschaftlicher Notation
        scientific_mask = duda_df['Site Alias'].astype(str).str.contains(r'[eE][+-]', na=False, regex=True)
        problematic_rows = duda_df[scientific_mask].copy()
        
        if len(problematic_rows) == 0:
            return duda_df
        
        print(f"🔧 Repariere {len(problematic_rows)} Site IDs mit wissenschaftlicher Notation...")
        
        # Für jeden problematischen Eintrag
        for idx, row in problematic_rows.iterrows():
            site_url = str(row.get('Site URL', '')).strip()
            
            if site_url and site_url != 'nan':
                # Domain aus URL extrahieren
                domain = self.extract_domain(site_url)
                
                # Im CRM nach dieser Domain suchen
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
                    correct_id = crm_matches.iloc[0]['Site-ID-Duda']
                    old_id = row['Site Alias']
                    duda_df.at[idx, 'Site Alias'] = str(correct_id)
                    print(f"  ✅ {old_id} → {correct_id} (via Domain: {domain})")
                elif len(crm_matches) > 1:
                    print(f"  ⚠️ Mehrere CRM-Einträge für Domain {domain} gefunden")
                else:
                    print(f"  ❌ Keine CRM-Übereinstimmung für Domain {domain}")
            else:
                print(f"  ❌ Keine gültige URL für Site ID {row['Site Alias']}")
        
        return duda_df
    
    def extract_domain(self, url):
        """Extrahiert die Domain aus einer URL"""
        if not url or url == 'nan':
            return ''
            
        # URL normalisieren
        url = str(url).strip()
        if not url.startswith('http'):
            url = 'https://' + url
            
        try:
            from urllib.parse import urlparse
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
    
    def convert_scientific_to_hex(self, value)::
        """Konvertiert wissenschaftliche Notation zurück zu Hex-String für Site IDs"""
        if pd.isna(value):
            return value
            
        value_str = str(value).strip()
        
        # Prüfen ob es wissenschaftliche Notation ist (enthält E+ oder e+)
        if ('e+' in value_str.lower() or 'e-' in value_str.lower()):
            try:
                # Als Float parsen und zu Integer konvertieren
                float_val = float(value_str)
                
                # Nur wenn es eine sehr große Zahl ist (typisch für falsch interpretierte Hex-IDs)
                if float_val > 1e10:
                    # Zurück zu Hex konvertieren (ohne 0x Prefix)
                    hex_val = hex(int(float_val))[2:]
                    return hex_val
                else:
                    # Kleine wissenschaftliche Zahlen beibehalten
                    return value_str
            except (ValueError, OverflowError):
                # Wenn Konvertierung fehlschlägt, ursprünglichen Wert zurückgeben
                return value_str
        
        return value_str
    
    def detect_encoding(self, file_content):
        """Erkennt das Encoding einer Datei"""
        result = chardet.detect(file_content)
        return result['encoding']
    
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
            
            # Spalten-Mapping für verschiedene Namenskonventionen
            column_mapping = {
                'Duda-Site-ID': 'Site-ID-Duda',  # Fallback
                'Site-ID-Duda': 'Site-ID-Duda',
                'Workflow-Status': 'Workflow-Status',
                'Projektname': 'Projektname'
            }
            
            # Verfügbare Spalten finden und Domain-Spalte identifizieren
            available_columns = df.columns.tolist()
            
            # Domain-Spalte finden
            domain_column = None
            for col in available_columns:
                if 'domain' in col.lower():
                    domain_column = col
                    break
            
            # Site-ID Spalte finden
            site_id_column = None
            for col in available_columns:
                if 'duda' in col.lower() and 'site' in col.lower() and 'id' in col.lower():
                    site_id_column = col
                    break
            
            if site_id_column is None:
                raise ValueError("Keine Duda-Site-ID Spalte gefunden")
            
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
            
            # DataFrame mit standardisierten Spaltennamen
            result_df = pd.DataFrame()
            result_df['Site-ID-Duda'] = df[site_id_column]
            result_df['Workflow-Status'] = df[status_column]
            result_df['Domain'] = df[domain_column] if domain_column else ''
            if project_column:
                result_df['Projektname'] = df[project_column]
            else:
                result_df['Projektname'] = 'Unbekannt'
            
            # Leere Site-IDs entfernen und Datentyp korrigieren
            result_df = result_df[result_df['Site-ID-Duda'].notna()].copy()
            result_df['Site-ID-Duda'] = result_df['Site-ID-Duda'].astype(str).str.strip()
            
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
