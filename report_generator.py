"""
Report Generator Klasse für die Duda Rechnungskontrolle
Erstellt CSV-Berichte mit Zusammenfassungen und API-Ergebnissen
"""

import pandas as pd
from io import StringIO


class ReportGenerator:
    """Klasse für die Generierung von Berichten"""
    
    def __init__(self):
        pass
    
    def generate_csv_report(self, issues_df, summary, api_results=None):
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
        
        # API-Ergebnisse falls vorhanden
        if api_results:
            output.write(f"# - API Verifikation: {api_results.get('api_calls', 0)} Calls\n")
            output.write(f"# - False Positives: {api_results.get('false_positives', 0)}\n")
            output.write(f"# - API Fehler: {api_results.get('api_errors', 0)}\n")
        
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
    
    def generate_false_positives_report(self, false_positives):
        """Generiert einen separaten Bericht für False Positives"""
        if not false_positives:
            return "# Keine False Positives gefunden\n"
        
        output = StringIO()
        
        # Header
        output.write("# False Positives Report - Eliminierte Probleme\n")
        output.write(f"# Datum: {pd.Timestamp.now().strftime('%d.%m.%Y %H:%M')}\n")
        output.write("#\n")
        output.write(f"# Anzahl eliminierte False Positives: {len(false_positives)}\n")
        output.write("#\n")
        
        # False Positives als DataFrame
        fp_df = pd.DataFrame(false_positives)
        
        # Relevante Spalten für Report
        columns_to_include = [
            'Site_Alias', 'Produkttyp', 'Problem_Typ', 
            'API_Analysis', 'API_Recommendation'
        ]
        
        # Nur verfügbare Spalten verwenden
        available_columns = [col for col in columns_to_include if col in fp_df.columns]
        
        if available_columns:
            csv_string = fp_df[available_columns].to_csv(index=False, sep=';', encoding='utf-8')
            output.write(csv_string)
        
        return output.getvalue()
    
    def generate_summary_metrics(self, summary, api_results=None):
        """Generiert eine kompakte Metrik-Übersicht"""
        metrics = {
            'total_charged': summary['total_charged'],
            'ok_count': summary['ok_count'],
            'issues_count': summary['issues_count'],
            'problem_rate_percent': round((summary['issues_count'] / summary['total_charged']) * 100, 1) if summary['total_charged'] > 0 else 0
        }
        
        # API-Metriken hinzufügen falls vorhanden
        if api_results:
            metrics.update({
                'api_calls_made': api_results.get('api_calls', 0),
                'false_positives_eliminated': api_results.get('false_positives', 0),
                'api_errors': api_results.get('api_errors', 0),
                'final_issues_count': metrics['issues_count'] - api_results.get('false_positives', 0)
            })
            
            # Aktualisierte Problemrate nach API-Verifikation
            if metrics['final_issues_count'] >= 0:
                metrics['final_problem_rate_percent'] = round((metrics['final_issues_count'] / summary['total_charged']) * 100, 1)
        
        return metrics
    
    def format_product_breakdown(self, product_breakdown):
        """Formatiert Product-Breakdown für bessere Lesbarkeit"""
        if not product_breakdown:
            return []
        
        breakdown_list = []
        for product, data in product_breakdown.items():
            breakdown_list.append({
                'Produkttyp': product,
                'Gesamt': data['total'],
                'OK': data['ok'],
                'Probleme': data['issues'],
                'Problem_Rate_%': round((data['issues'] / data['total']) * 100, 1) if data['total'] > 0 else 0
            })
        
        # Sortiere nach Anzahl der Probleme (absteigend)
        breakdown_list.sort(key=lambda x: x['Probleme'], reverse=True)
        
        return breakdown_list
