"""
Data Analyzer Klasse für die Duda Rechnungskontrolle
Implementiert die komplette Business-Logic für Problem-Identifikation
"""

import pandas as pd
from file_processor import FileProcessor
from utils import days_since_date, is_app_product, categorize_charge_frequency


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
            categorize_charge_frequency
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
                days_since_unpublish = days_since_date(unpublication_date)
                if days_since_unpublish is not None and days_since_unpublish <= 31:
                    return True  # Kürzlich offline → noch berechtigt verrechnet
        
        return False
    
    def find_issues(self):
        """Findet alle problematischen Einträge"""
        issues = []
        
        for _, duda_row in self.duda_df.iterrows():
            site_alias = str(duda_row['Site Alias']).strip()
            unpublication_date = duda_row.get('Unpublication Date', None)
            product_type = duda_row['Produkttyp']
            
            # Für Apps: Unpublication Date von zugehöriger Lizenz-Site übernehmen falls leer
            if is_app_product(product_type) and (pd.isna(unpublication_date) or str(unpublication_date).strip() in ['', 'nan']):
                # Suche nach Lizenz-Site mit derselben ID
                license_match = self.duda_df[
                    (self.duda_df['Site Alias'] == site_alias) & 
                    (self.duda_df['Produkttyp'] == 'Lizenz')
                ]
                if not license_match.empty:
                    license_unpublish = license_match.iloc[0].get('Unpublication Date', None)
                    if not pd.isna(license_unpublish) and str(license_unpublish).strip() not in ['', 'nan']:
                        unpublication_date = license_unpublish
            
            # CRM-Eintrag suchen - direkte Suche in der kombinierten Site-ID-Duda Spalte
            crm_match = self.crm_df[self.crm_df['Site-ID-Duda'] == site_alias]
            
            if crm_match.empty:
                # Site nicht im CRM gefunden
                issues.append({
                    'Site_Alias': site_alias,
                    'Site_URL': duda_row.get('Site URL', ''),
                    'Produkttyp': product_type,
                    'Charge_Frequency': duda_row['Charge Frequency'],
                    'CRM_Status': 'Nicht gefunden',
                    'Projektname': 'Nicht gefunden',
                    'Problem_Typ': 'Site nicht im CRM',
                    'Unpublish_Tage': days_since_date(unpublication_date) if unpublication_date else None
                })
            
            else:
                # CRM-Eintrag gefunden, Status prüfen
                crm_row = crm_match.iloc[0]
                workflow_status = crm_row['Workflow-Status']
                
                if not self.is_status_ok(workflow_status, unpublication_date):
                    # Für Apps: Prüfen ob es eine zugehörige Lizenz-Site mit OK-Status gibt
                    if is_app_product(product_type):
                        # Prüfen ob es eine Lizenz-Site mit gleichem Alias und OK-Status gibt
                        license_match = self.duda_df[
                            (self.duda_df['Site Alias'] == site_alias) & 
                            (self.duda_df['Produkttyp'] == 'Lizenz')
                        ]
                        
                        if not license_match.empty:
                            # Verwende das Unpublication Date der Lizenz für die Bewertung
                            license_unpublish = license_match.iloc[0].get('Unpublication Date', None)
                            if self.is_status_ok(workflow_status, license_unpublish):
                                continue  # App ist OK weil zugehörige Lizenz OK ist
                        
                        # App ist problematisch: entweder keine Lizenz gefunden oder Lizenz auch nicht OK
                        problem_reason = "ohne Website online" if not license_match.empty else "keine zugehörige Lizenz gefunden"
                        issues.append({
                            'Site_Alias': site_alias,
                            'Site_URL': duda_row.get('Site URL', ''),
                            'Produkttyp': product_type,
                            'Charge_Frequency': duda_row['Charge Frequency'],
                            'CRM_Status': workflow_status,
                            'Projektname': crm_row['Projektname'],
                            'Problem_Typ': f'{product_type} {problem_reason}',
                            'Unpublish_Tage': days_since_date(unpublication_date) if unpublication_date else None
                        })
                    
                    else:
                        # Für Lizenzen und Shops: Status muss OK sein (inkl. unpublication_date check)
                        days_unpublished = days_since_date(unpublication_date) if unpublication_date else None
                        
                        issues.append({
                            'Site_Alias': site_alias,
                            'Site_URL': duda_row.get('Site URL', ''),
                            'Produkttyp': product_type,
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
