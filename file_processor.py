"""
File Processing Klasse für die Duda Rechnungskontrolle
Verarbeitet CSV-Dateien von Duda und CRM mit automatischer Fehlerkorrektur
"""

import streamlit as st
import pandas as pd
import chardet
from io import StringIO
from utils import extract_domain, categorize_charge_frequency, is_app_product


class FileProcessor:
    """Klasse für die Verarbeitung von CSV-Dateien"""
    
    def __init__(self):
        pass
    
    def detect_encoding(self, file_content):
        """Erkennt das Encoding einer Datei"""
        result = chardet.detect(file_content)
        return result['encoding']
    
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
            product_type = categorize_charge_frequency(row.get('Charge Frequency', ''))
            
            repaired = False
            
            # Strategie 1: Für Apps - suche nach URL bei anderen Einträgen mit derselben wissenschaftlichen Notation
            if is_app_product(product_type) and (not site_url or site_url == 'nan'):
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
                domain = extract_domain(site_url)
                
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
