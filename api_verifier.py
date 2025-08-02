"""
Duda API Verifier Klasse mit erweiterten Debug-Features
"""

import streamlit as st
import requests
import base64
import time
import pandas as pd
from datetime import datetime
from utils import days_since_date, format_api_credentials_debug


class DudaAPIVerifier:
    """Klasse für die Duda API Integration zur finalen Verifikation"""
    
    def __init__(self):
        self.api_available = False
        self.api_username = None
        self.api_password = None
        self.api_endpoint = None
        self.debug_mode = False
        
        # Prüfe ob API Credentials verfügbar sind
        if "duda" in st.secrets:
            self.api_username = st.secrets["duda"].get("api_username")
            self.api_password = st.secrets["duda"].get("api_password")
            self.api_endpoint = st.secrets["duda"].get("api_endpoint", "https://api.duda.co")
            self.api_available = bool(self.api_username and self.api_password)
            
            # Debug-Modus aus Secrets laden (optional)
            self.debug_mode = st.secrets["duda"].get("debug_mode", False)
    
    def test_api_connection(self, test_site_id="63609f38"):
        """Testet die API-Verbindung mit einem Site-spezifischen Call"""
        if not self.api_available:
            return {
                'success': False,
                'error': 'API Credentials nicht verfügbar',
                'details': 'Bitte API Username und Password in Streamlit Secrets konfigurieren'
            }
        
        try:
            # Test mit bekannter Site-ID (funktioniert bei Enterprise Accounts)
            url = f"{self.api_endpoint}/api/sites/multiscreen/{test_site_id}"
            
            # Basic Auth Header
            auth_string = f"{self.api_username}:{self.api_password}"
            auth_bytes = auth_string.encode('ascii')
            auth_header = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/json',
                'User-Agent': 'Duda-Billing-Control/1.0'
            }
            
            if self.debug_mode:
                st.write("🔍 **Debug - API Test:**")
                st.write(f"URL: {url}")
                st.write(f"Credentials: {format_api_credentials_debug(self.api_username)}")
                st.write(f"Test Site ID: {test_site_id}")
            
            # API Call mit kurzem Timeout
            response = requests.get(url, headers=headers, timeout=10)
            
            if self.debug_mode:
                st.write(f"Response Status: {response.status_code}")
                if response.status_code != 200:
                    st.write(f"Response Body: {response.text[:500]}")
            
            if response.status_code == 200:
                data = response.json()
                return {
                    'success': True,
                    'test_site_id': test_site_id,
                    'site_published': data.get('published', False),
                    'site_domain': data.get('site_domain', 'Unknown'),
                    'status_code': response.status_code
                }
            elif response.status_code == 404:
                return {
                    'success': False,
                    'error': f'Test-Site {test_site_id} nicht gefunden',
                    'status_code': response.status_code,
                    'details': 'Site existiert nicht oder gehört nicht zu diesem Account'
                }
            else:
                return {
                    'success': False,
                    'error': f'HTTP {response.status_code}',
                    'status_code': response.status_code,
                    'response_text': response.text[:200],
                    'details': self._interpret_error_code(response.status_code)
                }
                
        except requests.exceptions.Timeout:
            return {
                'success': False,
                'error': 'API Timeout',
                'details': 'Die API-Anfrage hat zu lange gedauert (>10s)'
            }
        except requests.exceptions.ConnectionError:
            return {
                'success': False,
                'error': 'Verbindungsfehler',
                'details': 'Kann keine Verbindung zur Duda API herstellen'
            }
        except Exception as e:
            return {
                'success': False,
                'error': f'Unerwarteter Fehler: {str(e)}',
                'details': 'Unbekannter Fehler bei der API-Verbindung'
            }
    
    def _interpret_error_code(self, status_code):
        """Interpretiert HTTP-Status-Codes und gibt hilfreiche Erklärungen"""
        error_explanations = {
            400: "Bad Request - Die Anfrage ist fehlerhaft formatiert",
            401: "Unauthorized - API Credentials sind ungültig oder fehlen",
            403: "Forbidden - Keine Berechtigung für diese Aktion. Mögliche Ursachen:\n" +
                 "• API Username/Password ist falsch\n" +
                 "• Account hat keine API-Berechtigung\n" +
                 "• Kein Zugriff auf die abgefragten Sites",
            404: "Not Found - Die angeforderte Ressource existiert nicht",
            429: "Too Many Requests - Rate Limit erreicht, bitte warten",
            500: "Internal Server Error - Duda Server Problem",
            502: "Bad Gateway - Duda Service temporär nicht verfügbar",
            503: "Service Unavailable - Duda API ist temporär offline"
        }
        
        return error_explanations.get(status_code, f"HTTP {status_code} - Unbekannter Fehler")
    
    def get_site_status(self, site_id):
        """Holt den aktuellen Status einer Site von der Duda API"""
        if not self.api_available:
            return None
            
        try:
            # Duda API Endpoint für Site Details
            url = f"{self.api_endpoint}/api/sites/multiscreen/{site_id}"
            
            # Basic Auth Header
            auth_string = f"{self.api_username}:{self.api_password}"
            auth_bytes = auth_string.encode('ascii')
            auth_header = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/json',
                'User-Agent': 'Duda-Billing-Control/1.0'
            }
            
            if self.debug_mode:
                st.write(f"🔍 **Debug - Site Status für {site_id}:**")
                st.write(f"URL: {url}")
            
            # API Call
            response = requests.get(url, headers=headers, timeout=15)
            
            if self.debug_mode:
                st.write(f"Response: {response.status_code}")
                if response.status_code != 200:
                    st.write(f"Error: {response.text[:200]}")
            
            if response.status_code == 200:
                data = response.json()
                
                # Zusätzlich Publishing-Historie abrufen
                publish_history = self.get_publish_history(site_id)
                
                return {
                    'is_published': data.get('publish_status') == 'PUBLISHED',  # KORREKTUR!
                    'publish_status': data.get('publish_status', 'unknown'),     # Original-Wert beibehalten
                    'last_published': data.get('last_published_date'),           # KORREKTUR!
                    'first_published': data.get('first_published_date'),         # NEU!
                    'unpublication_date': data.get('unpublication_date'),        # Falls verfügbar
                    'site_status': data.get('site_status', 'unknown'),
                    'publish_history': publish_history,
                    'site_domain': data.get('site_domain', ''),
                    'fqdn': data.get('fqdn', ''),
                    'preview_url': data.get('preview_site_url', ''),             # KORREKTUR!
                    'api_response_code': response.status_code,
                    'creation_date': data.get('creation_date'),                  # NEU!
                    'modification_date': data.get('modification_date')           # NEU!
                }
            elif response.status_code == 404:
                return {
                    'error': 'Site nicht gefunden',
                    'api_response_code': 404,
                    'is_published': False
                }
            elif response.status_code == 403:
                return {
                    'error': 'Zugriff verweigert - keine Berechtigung für diese Site',
                    'api_response_code': 403,
                    'is_published': False,
                    'details': 'Site gehört möglicherweise einem anderen Account'
                }
            else:
                return {
                    'error': f'API Error: {response.status_code}',
                    'api_response_code': response.status_code,
                    'is_published': False,
                    'details': self._interpret_error_code(response.status_code),
                    'response_text': response.text[:200]
                }
                
        except requests.exceptions.Timeout:
            return {'error': 'Timeout', 'api_response_code': 408}
        except Exception as e:
            return {'error': str(e), 'api_response_code': 500}
    
    def get_publish_history(self, site_id):
        """Holt die Publishing-Historie einer Site"""
        if not self.api_available:
            return None
            
        try:
            # API Endpoint für Site Activities (Publishing-Historie)
            url = f"{self.api_endpoint}/api/sites/multiscreen/{site_id}/activities"
            
            auth_string = f"{self.api_username}:{self.api_password}"
            auth_bytes = auth_string.encode('ascii')
            auth_header = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/json',
                'User-Agent': 'Duda-Billing-Control/1.0'
            }
            
            # Nur die letzten 50 Aktivitäten abrufen
            params = {
                'limit': 50,
                'offset': 0
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=10)
            
            if response.status_code == 200:
                activities = response.json()
                
                # Nach Publish/Unpublish Aktivitäten filtern
                publish_activities = []
                for activity in activities:
                    activity_type = activity.get('activity_type', '').lower()
                    if any(term in activity_type for term in ['publish', 'unpublish']):
                        publish_activities.append({
                            'type': activity_type,
                            'date': activity.get('date'),
                            'user': activity.get('user', 'System'),
                            'description': activity.get('description', '')
                        })
                
                return publish_activities[:10]  # Nur die letzten 10 Publish-Aktivitäten
            else:
                return None
                
        except Exception:
            return None
    
    def analyze_api_result(self, site_id, api_result, original_issue):
        """Analysiert das API-Ergebnis und klassifiziert als OK oder Problem"""
        if api_result is None or 'error' in api_result:
            return {
                'classification': 'api_error',
                'reason': api_result.get('error', 'Unbekannter API-Fehler') if api_result else 'API nicht verfügbar',
                'recommendation': 'Manuelle Kontrolle erforderlich',
                'details': api_result.get('details', '') if api_result else ''
            }
        
        is_published = api_result.get('is_published', False)
        
        # Fall 1: Site ist online → False Positive
        if is_published:
            return {
                'classification': 'false_positive',
                'reason': 'Site ist tatsächlich online und erreichbar',
                'recommendation': 'Verrechnung berechtigt - CRM Status prüfen und aktualisieren'
            }
        
        # Fall 2: Site ist offline → weitere Analyse
        unpublish_date = api_result.get('unpublication_date')
        publish_history = api_result.get('publish_history', [])
        
        # Prüfe wann die Site zuletzt unpublished wurde
        days_offline = days_since_date(unpublish_date)
        
        # Wenn kein Unpublish-Datum in API, versuche es aus der History zu extrahieren
        if days_offline is None and publish_history:
            for activity in publish_history:
                if 'unpublish' in activity.get('type', '').lower():
                    activity_date = activity.get('date')
                    if activity_date:
                        days_offline = days_since_date(activity_date)
                        if days_offline is not None:
                            break
        
        # Kalendermonat-Regel anwenden (≤31 Tage)
        if days_offline is not None and days_offline <= 31:
            return {
                'classification': 'false_positive',
                'reason': f'Site offline seit {days_offline} Tagen (≤31 Tage = Kalendermonat-Regel)',
                'recommendation': 'Verrechnung berechtigt - im aktuellen Abrechnungsmonat offline gegangen'
            }
        
        # Fall 3: Echtes Problem - Site ist länger offline oder unbekanntes Offline-Datum
        offline_info = f"seit {days_offline} Tagen" if days_offline is not None else "Offline-Datum unbekannt"
        
        return {
            'classification': 'confirmed_issue',
            'reason': f'Site ist offline {offline_info}',
            'recommendation': 'Manuelle Kontrolle - möglicherweise nicht berechtigt verrechnet'
        }
    
    def verify_issues(self, issues_df):
        """Finale Verifikation der problematischen Sites über Duda API"""
        if not self.api_available or issues_df.empty:
            return issues_df, [], []
        
        verified_issues = []
        false_positives = []
        api_errors = []
        api_calls_made = 0
        
        st.info(f"🔍 Finale Verifikation von {len(issues_df)} problematischen Sites über Duda API...")
        
        # Progress Bar
        progress_bar = st.progress(0)
        status_text = st.empty()
        
        for idx, (_, issue) in enumerate(issues_df.iterrows()):
            site_id = issue['Site_Alias']
            
            # Progress Update
            progress = (idx + 1) / len(issues_df)
            progress_bar.progress(progress)
            status_text.text(f"Prüfe Site {idx + 1}/{len(issues_df)}: {site_id}")
            
            # API Call
            api_result = self.get_site_status(site_id)
            api_calls_made += 1
            
            # Ergebnis analysieren
            analysis = self.analyze_api_result(site_id, api_result, issue)
            
            # Angereicherte Issue-Daten erstellen
            enriched_issue = issue.copy()
            if api_result and 'error' not in api_result:
                enriched_issue['API_Published'] = api_result.get('is_published', False)
                enriched_issue['API_Last_Published'] = api_result.get('last_published', '')
                enriched_issue['API_Unpublish_Date'] = api_result.get('unpublication_date', '')
                enriched_issue['API_Site_Domain'] = api_result.get('site_domain', '')
            else:
                enriched_issue['API_Published'] = 'ERROR'
                enriched_issue['API_Last_Published'] = ''
                enriched_issue['API_Unpublish_Date'] = ''
                enriched_issue['API_Site_Domain'] = ''
                enriched_issue['API_Error_Details'] = api_result.get('details', '') if api_result else ''
            
            enriched_issue['API_Analysis'] = analysis['reason']
            enriched_issue['API_Recommendation'] = analysis['recommendation']
            
            # Klassifikation
            if analysis['classification'] == 'false_positive':
                false_positives.append(enriched_issue)
            elif analysis['classification'] == 'api_error':
                api_errors.append(enriched_issue)
                verified_issues.append(enriched_issue)  # Bei API-Fehlern: Issue beibehalten
            else:  # confirmed_issue
                verified_issues.append(enriched_issue)
            
            # Kleine Pause um API nicht zu überlasten
            if idx < len(issues_df) - 1:  # Nicht bei letztem Aufruf
                time.sleep(0.1)
        
        progress_bar.empty()
        status_text.empty()
        
        # Zusammenfassung
        st.success(f"✅ API Verifikation abgeschlossen:")
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("API Calls", api_calls_made)
        with col2:
            st.metric("False Positives", len(false_positives))
        with col3:
            st.metric("Echte Probleme", len(verified_issues) - len(api_errors))
        with col4:
            st.metric("API Fehler", len(api_errors))
        
        return pd.DataFrame(verified_issues), false_positives, api_errors
