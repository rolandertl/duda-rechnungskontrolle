"""
Hauptdatei für die Duda Rechnungskontrolle
Modulare Version v22 - Enterprise-kompatible API-Verifikation
"""

import streamlit as st
import pandas as pd
from file_processor import FileProcessor
from data_analyzer import DataAnalyzer
from api_verifier import DudaAPIVerifier
from report_generator import ReportGenerator


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
            
            **API Verifikation:**
            Finale Kontrolle über echte Duda-Site-Status für eliminierte False Positives.
            
            **App Version: v22** 🎉 - Modulare Architektur mit Enterprise-API
            """)
        
        # Version Info
        st.sidebar.markdown("---")
        st.sidebar.markdown("*Modulare Version: v22*", help="Aufgeteilte Architektur mit Enterprise-kompatible API-Verifikation")
    
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
            - **NEU:** Modulare Architektur
            """)
        
        with col2:
            st.subheader("📊 Analyse-Features")
            st.markdown("""
            - Zusammenfassung nach Produkttypen
            - Liste aller problematischen Einträge
            - Downloadbare Berichte
            - Übersichtliche Darstellung
            - **NEU:** Enterprise-API-Verifikation
            """)


def display_results(issues, summary, duda_df, crm_df):
    """Zeigt die Analyseergebnisse an"""
    
    # API Verifikation für finale Kontrolle
    duda_verifier = DudaAPIVerifier()
    
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
    
    # API Status anzeigen
    if duda_verifier.api_available:
        st.success("🔑 Duda API verfügbar - Enterprise-kompatible Verifikation möglich")
        
        # API-Verbindungstest anbieten
        col1, col2 = st.columns([3, 1])
        with col1:
            st.info("💡 Die API-Verifikation nutzt Site-spezifische Calls (funktioniert mit Enterprise-Accounts)")
        with col2:
            if st.button("🔍 API testen", help="Teste API-Verbindung"):
                with st.spinner("Teste API-Verbindung..."):
                    api_test = duda_verifier.test_api_connection()
                
                if api_test['success']:
                    st.success(f"✅ API funktioniert! Test-Site: {api_test.get('site_domain', 'OK')}")
                else:
                    st.error(f"❌ API-Problem: {api_test['error']}")
                    if 'details' in api_test:
                        st.warning(api_test['details'])
    else:
        st.warning("⚠️ Duda API nicht konfiguriert - Manuelle Kontrolle aller Probleme erforderlich")
        with st.expander("🔧 API Konfiguration"):
            st.markdown("""
            Füge folgende Secrets in Streamlit hinzu um die API-Verifikation zu aktivieren:
            
            ```toml
            [duda]
            api_username = "06d7b49e90"
            api_password = "DEIN_ECHTES_PASSWORD"  
            api_endpoint = "https://api.duda.co"
            ```
            
            Die API-Verifikation prüft:
            - ✅ Aktuellen Publish-Status
            - 📅 Letztes Publish/Unpublish-Datum
            - 📊 Publishing-Historie
            - 🔍 Automatische Kalendermonat-Regel
            """)
    
    # Produkttyp-Breakdown
    if summary['product_breakdown']:
        st.subheader("📋 Breakdown nach Produkttyp")
        
        report_gen = ReportGenerator()
        breakdown_list = report_gen.format_product_breakdown(summary['product_breakdown'])
        breakdown_df = pd.DataFrame(breakdown_list)
        
        st.dataframe(
            breakdown_df,
            use_container_width=True,
            hide_index=True
        )
    
    # Problematische Einträge
    if not issues.empty:
        st.header("⚠️ Manuelle Kontrolle erforderlich")
        
        # API Verifikation Button
        if duda_verifier.api_available:
            col1, col2 = st.columns([3, 1])
            with col1:
                st.info(f"📋 {len(issues)} problematische Einträge gefunden - API-Verifikation empfohlen")
            with col2:
                verify_button = st.button("🔍 API-Verifikation starten", type="primary", use_container_width=True)
            
            if verify_button:
                verified_issues, false_positives, api_errors = duda_verifier.verify_issues(issues)
                
                # API-Ergebnisse in Session State speichern
                st.session_state['verified_issues'] = verified_issues
                st.session_state['false_positives'] = false_positives
                st.session_state['api_errors'] = api_errors
                st.session_state['api_verification_done'] = True
                
                # False Positives anzeigen
                if false_positives:
                    st.subheader("✅ Eliminierte False Positives")
                    st.success(f"🎉 {len(false_positives)} False Positives durch API-Verifikation eliminiert!")
                    
                    fp_df = pd.DataFrame(false_positives)
                    display_columns = ['Site_Alias', 'Produkttyp', 'CRM_Status', 'API_Analysis', 'API_Recommendation']
                    available_columns = [col for col in display_columns if col in fp_df.columns]
                    
                    st.dataframe(
                        fp_df[available_columns],
                        use_container_width=True,
                        hide_index=True,
                        column_config={
                            'Site_Alias': 'Site ID',
                            'Produkttyp': 'Produkt',
                            'CRM_Status': 'CRM Status',
                            'API_Analysis': 'API Analyse',
                            'API_Recommendation': 'Empfehlung'
                        }
                    )
                
                # API-Fehler anzeigen
                if api_errors:
                    st.subheader("❌ API-Fehler")
                    st.warning(f"⚠️ {len(api_errors)} Sites konnten nicht über API verifiziert werden")
                    
                    error_df = pd.DataFrame(api_errors)
                    display_columns = ['Site_Alias', 'Produkttyp', 'API_Analysis']
                    available_columns = [col for col in display_columns if col in error_df.columns]
                    
                    st.dataframe(
                        error_df[available_columns],
                        use_container_width=True,
                        hide_index=True
                    )
                
                # Update issues für weitere Anzeige
                issues = verified_issues
                
                if issues.empty:
                    st.success("🎉 Alle Probleme durch API-Verifikation als False Positives identifiziert!")
                    return
        
        # Verwende Session State falls API-Verifikation bereits durchgeführt wurde
        elif 'api_verification_done' in st.session_state and st.session_state['api_verification_done']:
            issues = st.session_state.get('verified_issues', issues)
            false_positives = st.session_state.get('false_positives', [])
            api_errors = st.session_state.get('api_errors', [])
            
            if false_positives:
                st.success(f"✅ {len(false_positives)} False Positives bereits eliminiert")
            if api_errors:
                st.warning(f"⚠️ {len(api_errors)} API-Fehler")
        
        # Filter für Problemtyp
        if not issues.empty:
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
            
            # Spalten für Anzeige auswählen
            base_columns = {
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
                'Offline_seit': 'Offline seit'
            }
            
            # API-spezifische Spalten hinzufügen falls vorhanden
            if 'API_Published' in filtered_issues_display.columns:
                base_columns.update({
                    'API_Published': 'API: Online',
                    'API_Unpublish_Date': 'API: Offline seit',
                    'API_Analysis': 'API Analyse',
                    'API_Recommendation': 'Empfehlung'
                })
            
            # Anzeige der Probleme
            st.dataframe(
                filtered_issues_display,
                use_container_width=True,
                hide_index=True,
                column_config=base_columns
            )
        
        # Download-Buttons
        report_gen = ReportGenerator()
        
        # API-Ergebnisse für Report zusammenfassen
        api_results = None
        if 'api_verification_done' in st.session_state and st.session_state['api_verification_done']:
            api_results = {
                'api_calls': len(st.session_state.get('verified_issues', [])) + len(st.session_state.get('false_positives', [])),
                'false_positives': len(st.session_state.get('false_positives', [])),
                'api_errors': len(st.session_state.get('api_errors', []))
            }
        
        # Download-Buttons
        col1, col2 = st.columns(2)
        
        with col1:
            csv_data = report_gen.generate_csv_report(issues if not issues.empty else pd.DataFrame(), summary, api_results)
            st.download_button(
                label="📥 Haupt-Bericht als CSV",
                data=csv_data,
                file_name=f"duda_kontrolle_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
                mime="text/csv"
            )
        
        with col2:
            if 'false_positives' in st.session_state and st.session_state['false_positives']:
                fp_report = report_gen.generate_false_positives_report(st.session_state['false_positives'])
                st.download_button(
                    label="📥 False Positives Report",
                    data=fp_report,
                    file_name=f"false_positives_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.csv",
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
        
        # Modulare Architektur Info
        st.subheader("🏗️ Modulare Architektur")
        st.markdown("""
        **Erfolgreich geladene Module:**
        - ✅ `utils.py` - Hilfsfunktionen
        - ✅ `file_processor.py` - CSV-Verarbeitung
        - ✅ `data_analyzer.py` - Business-Logic
        - ✅ `api_verifier.py` - Enterprise-API
        - ✅ `report_generator.py` - Berichte
        - ✅ `main.py` - UI-Integration
        
        **Vorteile:**
        - Wartbarer Code
        - Kleinere Dateien
        - Keine Token-Limits
        - Einfache Updates
        """)


if __name__ == "__main__":
    main()
