import pandas as pd
from .file_processor import FileProcessor

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
    
    def is_status_ok(self, status):
        """Prüft ob ein Workflow-Status als OK gilt"""
        if pd.isna(status):
            return False
        
        status_str = str(status).lower()
        return "website online" in status_str
    
    def find_issues(self):
        """Findet alle problematischen Einträge"""
        issues = []
        
        for _, duda_row in self.duda_df.iterrows():
            site_alias = str(duda_row['Site Alias']).strip()
            
            # CRM-Eintrag suchen
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
                    'Problem_Typ': 'Site nicht im CRM'
                })
            
            else:
                # CRM-Eintrag gefunden, Status prüfen
                crm_row = crm_match.iloc[0]
                workflow_status = crm_row['Workflow-Status']
                
                if not self.is_status_ok(workflow_status):
                    # Für Apps: Prüfen ob es eine zugehörige "Website online" Site gibt
                    if duda_row['Produkttyp'] in ['CCB', 'Apps']:
                        # Prüfen ob es eine Lizenz-Site mit gleichem Alias und OK-Status gibt
                        license_match = self.duda_df[
                            (self.duda_df['Site Alias'] == site_alias) & 
                            (self.duda_df['Produkttyp'] == 'Lizenz')
                        ]
                        
                        if not license_match.empty:
                            # Es gibt eine Lizenz-Site, diese sollte OK sein
                            continue
                        
                        # Sonst ist es ein Problem
                        issues.append({
                            'Site_Alias': site_alias,
                            'Site_URL': duda_row.get('Site URL', ''),
                            'Produkttyp': duda_row['Produkttyp'],
                            'Charge_Frequency': duda_row['Charge Frequency'],
                            'CRM_Status': workflow_status,
                            'Projektname': crm_row['Projektname'],
                            'Problem_Typ': f'{duda_row["Produkttyp"]} ohne Website online'
                        })
                    
                    else:
                        # Für Lizenzen und Shops: Status muss OK sein
                        issues.append({
                            'Site_Alias': site_alias,
                            'Site_URL': duda_row.get('Site URL', ''),
                            'Produkttyp': duda_row['Produkttyp'],
                            'Charge_Frequency': duda_row['Charge Frequency'],
                            'CRM_Status': workflow_status,
                            'Projektname': crm_row['Projektname'],
                            'Problem_Typ': 'Abweichender Workflow-Status'
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
