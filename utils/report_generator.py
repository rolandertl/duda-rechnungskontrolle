import pandas as pd
from io import StringIO

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
    
    def generate_excel_report(self, issues_df, summary, duda_df, crm_df):
        """Generiert einen Excel-Bericht mit mehreren Sheets"""
        output = StringIO()
        
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            # Sheet 1: Zusammenfassung
            summary_data = []
            summary_data.append(['Metrik', 'Wert'])
            summary_data.append(['Gesamt verrechnet', summary['total_charged']])
            summary_data.append(['OK (Website online)', summary['ok_count']])
            summary_data.append(['Manuelle Kontrolle', summary['issues_count']])
            
            if summary['issues_count'] > 0:
                percentage = round((summary['issues_count'] / summary['total_charged']) * 100, 1)
                summary_data.append(['Problemrate %', f"{percentage}%"])
            
            summary_df = pd.DataFrame(summary_data[1:], columns=summary_data[0])
            summary_df.to_excel(writer, sheet_name='Zusammenfassung', index=False)
            
            # Sheet 2: Produkttyp-Breakdown
            if summary['product_breakdown']:
                breakdown_data = []
                for product, data in summary['product_breakdown'].items():
                    breakdown_data.append([product, data['total'], data['ok'], data['issues']])
                
                breakdown_df = pd.DataFrame(
                    breakdown_data, 
                    columns=['Produkttyp', 'Gesamt', 'OK', 'Probleme']
                )
                breakdown_df.to_excel(writer, sheet_name='Produkttyp-Breakdown', index=False)
            
            # Sheet 3: Problematische Einträge
            if not issues_df.empty:
                issues_df.to_excel(writer, sheet_name='Problematische Einträge', index=False)
            
            # Sheet 4: Alle Duda-Einträge (für Referenz)
            duda_df.to_excel(writer, sheet_name='Alle Duda-Einträge', index=False)
        
        return output.getvalue()
