"""
Hilfsfunktionen für die Duda Rechnungskontrolle
Zentrale Utilities die von mehreren Modulen verwendet werden
"""

from datetime import datetime
from urllib.parse import urlparse
import pandas as pd


def extract_domain(url):
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


def days_since_date(date_value):
    """Berechnet Tage seit einem gegebenen Datum - unterstützt alle Formate"""
    if pd.isna(date_value) or str(date_value).strip() in ['', 'nan']:
        return None
        
    try:
        # Verschiedene Datumsformate versuchen
        date_str = str(date_value).strip()
        
        # Common formats: YYYY-MM-DD, MM/DD/YYYY, DD.MM.YYYY, ISO, etc.
        formats_to_try = [
            '%Y-%m-%d',
            '%m/%d/%Y', 
            '%d.%m.%Y',
            '%Y-%m-%d %H:%M:%S',
            '%m/%d/%Y %H:%M:%S',
            '%d.%m.%Y %H:%M:%S',
            '%Y-%m-%dT%H:%M:%S.%fZ',  # ISO mit Millisekunden
            '%Y-%m-%dT%H:%M:%SZ',     # ISO ohne Millisekunden
            '%Y-%m-%dT%H:%M:%S'       # ISO ohne Z
        ]
        
        parsed_date = None
        for fmt in formats_to_try:
            try:
                # Z am Ende entfernen für ISO-Format
                clean_date_str = date_str.replace('Z', '') if 'Z' in fmt else date_str
                parsed_date = datetime.strptime(clean_date_str, fmt.replace('Z', ''))
                break
            except ValueError:
                continue
        
        if parsed_date is None:
            return None
            
        # Tage zwischen parsed_date und heute
        today = datetime.now()
        delta = today - parsed_date
        return delta.days
        
    except Exception:
        return None


def is_app_product(product_type):
    """Prüft ob ein Produkttyp eine App/Zusatzservice ist (abhängig von Lizenz)"""
    app_types = [
        'CCB', 'AudioEye', 'Paperform', 'RSS/Social', 
        'SiteSearch', 'BookingTool', 'IVR', 'Apps'
    ]
    return product_type in app_types


def categorize_charge_frequency(charge_frequency):
    """Kategorisiert Charge Frequency in Produkttypen"""
    if pd.isna(charge_frequency):
        return "Unbekannt"
    
    freq_lower = str(charge_frequency).lower()
    
    # Haupt-Website-Lizenzen
    if "dudaone monthly" in freq_lower:
        return "Lizenz"
    
    # E-Commerce / Online-Shops
    elif any(term in freq_lower for term in ["ecom", "store"]):
        return "Shop"
    
    # Alle anderen sind Apps/Zusatzservices (abhängig von der Haupt-Website)
    else:
        # Spezielle App-Kategorien für bessere Übersicht
        if "cookiebot" in freq_lower:
            return "CCB"
        elif "audioeye" in freq_lower:
            return "AudioEye"
        elif "paperform" in freq_lower:
            return "Paperform"
        elif "rss" in freq_lower or "social" in freq_lower:
            return "RSS/Social"
        elif "sitesearch" in freq_lower:
            return "SiteSearch"
        elif "book like a boss" in freq_lower:
            return "BookingTool"
        elif "ivr" in freq_lower:
            return "IVR"
        else:
            return "Apps" # Fallback für unbekannte Apps


def format_api_credentials_debug(username, password_masked=True):
    """Formatiert API-Credentials für Debug-Ausgabe (sicher)"""
    if password_masked:
        return f"Username: {username[:8]}... | Password: ***"
    return f"Username: {username} | Password: [HIDDEN]"


def validate_site_id(site_id):
    """Validiert eine Duda Site ID"""
    if not site_id or pd.isna(site_id):
        return False
    
    site_id_str = str(site_id).strip()
    
    # Grundlegende Validierung: mindestens 8 Zeichen, alphanumerisch
    if len(site_id_str) < 8:
        return False
    
    # Keine wissenschaftliche Notation
    if any(char in site_id_str for char in ['e+', 'e-', 'E+', 'E-']):
        return False
    
    return True


def format_currency(amount, currency="EUR"):
    """Formatiert Geldbeträge für bessere Lesbarkeit"""
    try:
        amount_float = float(amount)
        return f"{amount_float:,.2f} {currency}"
    except (ValueError, TypeError):
        return str(amount)


def safe_string_convert(value, default=""):
    """Sichere String-Konvertierung mit Fallback"""
    if pd.isna(value) or value is None:
        return default
    return str(value).strip()
