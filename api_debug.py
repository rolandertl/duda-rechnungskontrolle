"""
Isolierter API Debug für Duda API Probleme
Führe diese Datei separat aus um API-Probleme zu debuggen
"""

import streamlit as st
from api_verifier import DudaAPIVerifier

st.title("🔍 Duda API Debug Tool")
st.markdown("---")

# API Verifier initialisieren
verifier = DudaAPIVerifier()

# Schritt 1: Basis-Informationen
st.header("1️⃣ API Konfiguration")

if verifier.api_available:
    st.success("✅ API Credentials gefunden")
    
    col1, col2 = st.columns(2)
    with col1:
        st.write(f"**Username:** `{verifier.api_username}`")
        st.write(f"**Endpoint:** `{verifier.api_endpoint}`")
    with col2:
        st.write(f"**Password:** `{'*' * len(verifier.api_password) if verifier.api_password else 'FEHLT'}`")
        st.write(f"**Debug Mode:** {verifier.debug_mode}")
else:
    st.error("❌ API Credentials fehlen")
    st.info("Bitte konfiguriere die Streamlit Secrets:")
    st.code("""
[duda]
api_username = "06d7b49e90"
api_password = "DEIN_ECHTES_PASSWORD"
api_endpoint = "https://api.duda.co"
debug_mode = true
""")
    st.stop()

# Schritt 2: API Verbindungstest
st.header("2️⃣ API Verbindungstest")

if st.button("🔍 API-Verbindung testen", type="primary"):
    with st.spinner("Teste API-Verbindung..."):
        result = verifier.test_api_connection()
    
    if result['success']:
        st.success("✅ API-Verbindung erfolgreich!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Account Name:** {result.get('account_name', 'Unknown')}")
        with col2:
            st.write(f"**Account Type:** {result.get('account_type', 'Unknown')}")
            
    else:
        st.error(f"❌ API-Verbindung fehlgeschlagen: {result['error']}")
        
        if 'details' in result:
            st.warning(f"**Details:** {result['details']}")
        
        if 'status_code' in result:
            st.info(f"**HTTP Status:** {result['status_code']}")
            
        if 'response_text' in result:
            with st.expander("Raw Response"):
                st.text(result['response_text'])

# Schritt 3: Einzelne Site testen
st.header("3️⃣ Site-spezifischer Test")

test_site_id = st.text_input(
    "Site ID für Test eingeben:",
    placeholder="z.B. abc123def456",
    help="Gib eine Site ID ein, von der du sicher weißt, dass sie dir gehört"
)

if test_site_id and st.button("🔍 Site Status testen"):
    with st.spinner(f"Teste Site {test_site_id}..."):
        # Debug-Modus temporär aktivieren
        verifier.debug_mode = True
        result = verifier.get_site_status(test_site_id)
    
    st.subheader("📋 Ergebnis:")
    
    if result and 'error' not in result:
        st.success("✅ Site-Daten erfolgreich abgerufen!")
        
        col1, col2 = st.columns(2)
        with col1:
            st.write(f"**Published:** {result.get('is_published', 'Unknown')}")
            st.write(f"**Site Domain:** {result.get('site_domain', 'Unknown')}")
        with col2:
            st.write(f"**Last Published:** {result.get('last_published', 'Unknown')}")
            st.write(f"**Unpublication Date:** {result.get('unpublication_date', 'Unknown')}")
            
        # Publishing History falls vorhanden
        if result.get('publish_history'):
            st.subheader("📊 Publishing History:")
            history_df = pd.DataFrame(result['publish_history'])
            st.dataframe(history_df, use_container_width=True)
    
    elif result:
        st.error(f"❌ Fehler: {result.get('error', 'Unbekannt')}")
        
        if 'details' in result:
            st.warning(f"**Details:** {result['details']}")
            
        if 'api_response_code' in result:
            st.info(f"**HTTP Status:** {result['api_response_code']}")
            
        if 'response_text' in result:
            with st.expander("Raw Response"):
                st.text(result['response_text'])
    else:
        st.error("❌ Keine Antwort von der API erhalten")

# Schritt 4: Tipps und Hilfe
st.header("4️⃣ Häufige Probleme & Lösungen")

with st.expander("🔧 403 Forbidden Fehler"):
    st.markdown("""
    **Mögliche Ursachen:**
    - API Username ist falsch (sollte `06d7b49e90` sein)
    - API Password ist falsch oder abgelaufen
    - Account hat keine Berechtigung für die Site
    - Site gehört einem anderen Account/Sub-Account
    - Enterprise Account mit speziellen Berechtigungen
    
    **Lösungsansätze:**
    1. **Password prüfen:** Gehe zu Duda Dashboard → Settings → API und generiere ein neues Password
    2. **Account-Typ prüfen:** Enterprise Accounts haben manchmal andere API-Berechtigungen
    3. **Site-Zugehörigkeit:** Prüfe ob die Sites wirklich in deinem Account sind
    4. **Sub-Accounts:** Bei Enterprise-Accounts können Sites in Sub-Accounts liegen
    """)

with st.expander("🔧 401 Unauthorized Fehler"):
    st.markdown("""
    **Bedeutung:** API Credentials sind komplett ungültig
    
    **Lösungsansätze:**
    1. Username und Password komplett neu eingeben
    2. Neue API Credentials in Duda generieren
    3. Prüfen ob API-Zugang für deinen Plan aktiviert ist
    """)

with st.expander("🔧 404 Not Found Fehler"):
    st.markdown("""
    **Bedeutung:** Site existiert nicht oder ist nicht verfügbar
    
    **Lösungsansätze:**
    1. Site ID doppelt prüfen (Copy/Paste Fehler?)
    2. Site wurde möglicherweise gelöscht
    3. Site ist in einem anderen Account
    """)

with st.expander("💡 Enterprise Account Besonderheiten"):
    st.markdown("""
    **Enterprise Accounts haben oft:**
    - **Sub-Accounts** für verschiedene Teams/Kunden
    - **Spezielle API-Berechtigungen** pro Sub-Account
    - **White-Label Konfigurationen** die API-Zugriff beeinflussen
    
    **Überprüfen:**
    1. Sind die Sites in deinem Haupt-Account oder in Sub-Accounts?
    2. Haben Sub-Accounts eigene API-Credentials?
    3. Ist der API-Zugriff für alle Account-Ebenen aktiviert?
    """)

# Schritt 5: Manuelle Credential-Eingabe zum Testen
st.header("5️⃣ Manuelle Credential-Tests")

st.info("Falls die Streamlit Secrets nicht funktionieren, teste hier manuell:")

with st.form("manual_test"):
    manual_username = st.text_input("API Username:", value="06d7b49e90")
    manual_password = st.text_input("API Password:", type="password")
    manual_endpoint = st.text_input("API Endpoint:", value="https://api.duda.co")
    
    submitted = st.form_submit_button("🧪 Manuell testen")
    
    if submitted and manual_username and manual_password:
        # Temporären Verifier mit manuellen Credentials erstellen
        import requests
        import base64
        
        try:
            url = f"{manual_endpoint}/api/accounts/account"
            auth_string = f"{manual_username}:{manual_password}"
            auth_bytes = auth_string.encode('ascii')
            auth_header = base64.b64encode(auth_bytes).decode('ascii')
            
            headers = {
                'Authorization': f'Basic {auth_header}',
                'Content-Type': 'application/json'
            }
            
            st.write("🔍 **Teste mit manuellen Credentials...**")
            st.write(f"URL: {url}")
            st.write(f"Username: {manual_username}")
            st.write(f"Password: {'*' * len(manual_password)}")
            
            response = requests.get(url, headers=headers, timeout=10)
            
            st.write(f"**Response Status:** {response.status_code}")
            
            if response.status_code == 200:
                st.success("✅ Manuelle Credentials funktionieren!")
                data = response.json()
                st.json(data)
            else:
                st.error(f"❌ Fehler {response.status_code}")
                st.text(f"Response: {response.text[:500]}")
                
        except Exception as e:
            st.error(f"❌ Exception: {str(e)}")

# Debug-Informationen
st.header("6️⃣ System-Informationen")
with st.expander("📊 Debug Info"):
    import sys
    import requests
    
    st.write("**Python Version:**", sys.version)
    st.write("**Requests Version:**", requests.__version__)
    st.write("**Streamlit Version:**", st.__version__)
    
    # Secrets Debug (ohne sensible Daten zu zeigen)
    secrets_available = "duda" in st.secrets
    st.write("**Streamlit Secrets verfügbar:**", secrets_available)
    
    if secrets_available:
        secret_keys = list(st.secrets["duda"].keys())
        st.write("**Verfügbare Secret Keys:**", secret_keys)
