import os
import sqlite3
import csv
import requests  # Canlı haberleri çekmek için ekledik
from flask import Flask, render_template, request, jsonify

app = Flask(
    __name__,
    template_folder='templates',
    static_folder='static'
)

DATABASE = 'hantavirus_surveillance.db'
CSV_FILE = 'global_hantavirus_surveillance_dataset_2026.csv'

# --- NEWS API GÜVENLİ ENTEGRASYONU ---
NEWS_API_KEY = "ddd61a230ac34540b8d44e6f6cdf82a2" 

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Veritabanı tablolarını premium ve esnek mimariye uygun şekilde sıfırdan kurar."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('DROP TABLE IF EXISTS vaka_verileri')
    cursor.execute('''
        CREATE TABLE vaka_verileri (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country TEXT,
            region TEXT,
            report_date TEXT,
            virus_strain TEXT,
            transmission_type TEXT,
            exposure_source TEXT,
            patient_age INTEGER,
            gender TEXT,
            symptoms TEXT,
            hospitalization TEXT,
            fatality TEXT
        )
    ''')
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS test_gecmisi (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT,
            yas INTEGER,
            cinsiyet TEXT,
            ulke TEXT,
            sehir TEXT,
            cevre_tipi TEXT,
            risk_skoru REAL,
            risk_seviyesi TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    if os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, mode='r', encoding='utf-8', errors='ignore') as f:
                reader = csv.DictReader(f)
                vakalar = []
                for row in reader:
                    vakalar.append((
                        row.get('country', '').strip(),
                        row.get('region', '').strip(),
                        row.get('report_date', '').strip(),
                        row.get('virus_strain', '').strip(),
                        row.get('transmission_type', '').strip(),
                        row.get('exposure_source', '').strip(),
                        int(row.get('patient_age', 0)) if row.get('patient_age') else 0,
                        row.get('gender', '').strip(),
                        row.get('symptoms', '').strip(),
                        row.get('hospitalization', '').strip(),
                        row.get('fatality', '').strip()
                    ))
                
                if vakalar:
                    cursor.executemany('''
                        INSERT INTO vaka_verileri 
                        (country, region, report_date, virus_strain, transmission_type, exposure_source, patient_age, gender, symptoms, hospitalization, fatality)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', vakalar)
        except Exception as e:
            print("Veri seti yüklenirken hata oluştu:", e)
            
    conn.commit()
    conn.close()

init_db()

# ================= PAGES (SAYFALAR) =================

@app.route('/')
def ana_sayfa():
    return render_template('index.html')

@app.route('/dashboard')
def pano_sayfasi():
    return render_template('dashboard.html')

@app.route('/surveillance')
def harita_sayfasi():
    return render_template('harita.html')

@app.route('/klinik-test')
def klinik_test_sayfasi():
    return render_template('klinik_test.html')

@app.route('/profil')
def profil_sayfasi():
    return render_template('profil.html')

# ================= API ENDPOINTS =================

@app.route('/api/guncel-haberler')
def get_guncel_haberler():
    """News API üzerinden dünya genelindeki Hantavirüs ve salgın haberlerini canlı çeker."""
    if not NEWS_API_KEY or NEWS_API_KEY == "BURAYA_NEWS_API_ANAHTARINI_YAZ":
        return jsonify({
            "articles": [
                {
                    "title": "Küresel Hantavirüs Sürveyans Raporu Yayınlandı",
                    "description": "2026 yılı küresel verilerine göre kemirgen kaynaklı maruziyetlerde tarım alanları başı çekiyor.",
                    "source": {"name": "CDC Gözetim"},
                    "url": "#"
                }
            ]
        })
    
    url = f"https://newsapi.org/v2/everything?q=hantavirus+OR+hanta+OR+virus&sortBy=publishedAt&language=en&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        return jsonify(response.json())
    except Exception as e:
        return jsonify({"articles": [], "error": str(e)})

@app.route('/api/lokasyonlar')
def get_lokasyonlar():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT DISTINCT country, region FROM vaka_verileri WHERE country != "" ORDER BY country, region')
    rows = cursor.fetchall()
    conn.close()
    
    data = {}
    for row in rows:
        ulke = row['country']
        sehir = row['region']
        if ulke not in data:
            data[ulke] = []
        if sehir and sehir not in data[ulke]:
            data[ulke].append(sehir)
            
    return jsonify(data)

@app.route('/api/klinik-analiz', methods=['POST'])
def klinik_analiz_yap():
    data = request.json or {}
    ad = data.get('ad', 'Anonim')
    yas = int(data.get('yas', 30))
    cinsiyet = data.get('cinsiyet', 'Belirtilmedi')
    ulke = data.get('ulke', '')
    sehir = data.get('sehir', '')
    cevre_tipi = data.get('cevre_tipi', '')
    secilen_semptomlar = data.get('semptomlar', [])
    
    semptom_skoru = 0
    for s in secilen_semptomlar:
        s_low = s.lower()
        if 'fever' in s_low or 'ateş' in s_low: semptom_skoru += 30
        elif 'breathing' in s_low or 'nefes' in s_low or 'cough' in s_low: semptom_skoru += 35
        elif 'muscle' in s_low or 'kas' in s_low: semptom_skoru += 15
        elif 'headache' in s_low or 'baş' in s_low: semptom_skoru += 10
        elif 'nausea' in s_low or 'vomiting' in s_low or 'bulantı' in s_low: semptom_skoru += 10
        
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) as vaka_sayisi FROM vaka_verileri WHERE country = ?', (ulke,))
    ulke_vaka_sayisi = cursor.fetchone()['vaka_sayisi']
    
    cursor.execute('SELECT COUNT(*) as bolge_vaka FROM vaka_verileri WHERE country = ? AND region = ?', (ulke, sehir))
    sehir_vaka_sayisi = cursor.fetchone()['bolge_vaka']
    
    cursor.execute('SELECT COUNT(*) as cevre_vaka FROM vaka_verileri WHERE country = ? AND exposure_source = ?', (ulke, cevre_tipi))
    cevre_vaka_sayisi = cursor.fetchone()['cevre_vaka']
    
    bolge_efekti = min(sehir_vaka_sayisi * 5, 20) if sehir_vaka_sayisi > 0 else (min(ulke_vaka_sayisi * 0.5, 10))
    cevre_efekti = min(cevre_vaka_sayisi * 4, 15)
    
    toplam_skor = min((semptom_skoru * 0.65) + bolge_efekti + cevre_efekti, 100)
    
    if toplam_skor >= 75: 
        seviye = "KRİTİK"
        oneriler = [
            "En yakın tam teşekküllü sağlık kuruluşuna acilen başvurun.",
            "Solunum sıkıntısı ihtimaline karşı yoğun bakım desteği olan bir hastane tercih edilmelidir.",
            "Bulunduğunuz ortamı derhal havalandırın ve maskesiz girmeyin."
        ]
    elif toplam_skor >= 50: 
        seviye = "YÜKSEK RİSK"
        oneriler = [
            "Klinik semptomlarınız ciddileşebilir, bir enfeksiyon hastalıkları uzmanına görünün.",
            "Ateş ve kas ağrılarınızı yakından takip edin.",
            "Kemirgen dışkısı barındırabilecek kapalı alanlardan uzak durun."
        ]
    elif toplam_skor >= 25: 
        seviye = "ORTA RİSK"
        oneriler = [
            "Belirtileriniz genel enfeksiyon bulguları içermektedir, dinlenin ve bol sıvı tüketin.",
            "Son 2-4 hafta içinde açık alan veya ambar maruziyetiniz olduysa aile hekiminizi bilgilendirin."
        ]
    else: 
        seviye = "DÜŞÜK RİSK"
        oneriler = [
            "Hantavirüs uyumlu spesifik bir bulguya rastlanmadı.",
            "Genel hijyen kurallarına dikkat etmeniz ve açık alanlarda eldiven/maske kullanmanız önerilir."
        ]
        
    cursor.execute('''
        INSERT INTO test_gecmisi (ad_soyad, yas, cinsiyet, ulke, sehir, cevre_tipi, risk_skoru, risk_seviyesi)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (ad, yas, cinsiyet, ulke, sehir, cevre_tipi, round(toplam_skor, 1), seviye))
    
    conn.commit()
    conn.close()
    
    return jsonify({
        "skor": round(toplam_skor, 1),
        "risk_seviyesi": seviye,
        "oneriler": oneriler
    })

@app.route('/api/kullanici-gecmis')
def get_kullanici_gecmis():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT ad_soyad, yas, cinsiyet, ulke, sehir, risk_skoru, risk_seviyesi, tarih FROM test_gecmisi ORDER BY id DESC LIMIT 3')
    rows = cursor.fetchall()
    conn.close()
    return jsonify([dict(row) for row in rows])

@app.route('/api/pano-istatistikler')
def get_pano_istatistikler():
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('SELECT country, COUNT(*) as vaka_sayisi FROM vaka_verileri GROUP BY country ORDER BY vaka_sayisi DESC LIMIT 1')
    top_country_row = cursor.fetchone()
    top_country = top_country_row['country'] if top_country_row else "-"
    
    cursor.execute('SELECT exposure_source, COUNT(*) as vaka FROM vaka_verileri GROUP BY exposure_source ORDER BY vaka DESC LIMIT 1')
    top_source_row = cursor.fetchone()
    top_source = top_source_row['exposure_source'] if top_source_row else "-"
    
    aylar_isimler = ["Oca", "Şub", "Mar", "Nis", "May", "Haz", "Tem", "Ağu", "Eyl", "Eki", "Kas", "Ara"]
    trend_data = {isim: 0 for isim in aylar_isimler}
    
    cursor.execute('SELECT report_date FROM vaka_verileri')
    dates = cursor.fetchall()
    for d in dates:
        date_str = d['report_date']
        if len(date_str) >= 10:
            try:
                ay_index = int(date_str.split('-')[1]) - 1
                if 0 <= ay_index < 12:
                    trend_data[aylar_isimler[ay_index]] += 1
            except:
                pass
                
    conn.close()
    return jsonify({
        "en_cok_vaka_ulke": top_country,
        "en_yaygin_maruziyet": top_source,
        "aylik_trend": trend_data
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
