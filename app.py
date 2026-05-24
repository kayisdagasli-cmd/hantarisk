import os
import sqlite3
import csv  # Pandas yerine sunucuyu yormayan gömülü kütüphane
from flask import Flask, render_template, jsonify, request
import requests

app = Flask(__name__)

DATABASE = 'hantavirus.db'
CSV_FILE = 'global_hantavirus_surveillance_dataset_2026.csv'
NEWS_API_KEY = 'bc24ec87c1264c3986a45480749bd00c'

def veritabanı_hazırla():
    # Veritabanı ve tabloları oluştur
    conn = sqlite3.connect(DATABASE)
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS vakalar (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ulke TEXT,
            sehir TEXT,
            enlem REAL,
            boylam REAL,
            yil INTEGER,
            sonuc TEXT
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS klinik_testler (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            ad_soyad TEXT,
            yas INTEGER,
            cinsiyet TEXT,
            ulke TEXT,
            sehir TEXT,
            cevre_tipi TEXT,
            risk_skoru INTEGER,
            risk_seviyesi TEXT,
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    conn.commit()

    # Eğer tablo boşsa CSV dosyasından verileri yükle (Pandas olmadan hızlı sürüm)
    cursor.execute("SELECT COUNT(*) FROM vakalar")
    if cursor.fetchone()[0] == 0 and os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
                # Sütun isimlerini temizle ve küçük harfe çevir
                headers = [h.strip().lower() for h in reader.fieldnames]
                reader.fieldnames = headers
                
                ulke_col = 'country' if 'country' in headers else headers[0]
                sehir_col = 'city' if 'city' in headers else headers[1]
                enlem_col = 'latitude' if 'latitude' in headers else (headers[2] if 'lat' in ''.join(headers) else headers[2])
                boylam_col = 'longitude' if 'longitude' in headers else (headers[3] if 'long' in ''.join(headers) else headers[3])
                yil_col = 'year' if 'year' in headers else 'yil'
                sonuc_col = 'outcome' if 'outcome' in headers else 'clinical_outcome'
                
                for row in reader:
                    ulke = str(row.get(ulke_col, 'Bilinmiyor'))
                    sehir = str(row.get(sehir_col, 'Bilinmiyor'))
                    
                    try: enlem = float(row.get(enlem_col, 0.0))
                    except: enlem = 0.0
                    
                    try: boylam = float(row.get(boylam_col, 0.0))
                    except: boylam = 0.0
                    
                    try: yil = int(row.get(yil_col, 2026))
                    except: yil = 2026
                    
                    sonuc = str(row.get(sonuc_col, 'Recovered'))
                    
                    cursor.execute(
                        "INSERT INTO vakalar (ulke, sehir, enlem, boylam, yil, sonuc) VALUES (?, ?, ?, ?, ?, ?)",
                        (ulke, sehir, enlem, boylam, yil, sonuc)
                    )
            conn.commit()
            print("Kaggle veri seti başarıyla veritabanına aktarıldı.")
        except Exception as e:
            print(f"CSV yükleme hatası: {e}")
    conn.close()

# Uygulama başlarken veritabanını doldur
veritabanı_hazırla()

# --- SAYFA YÖNLENDİRMELERİ ---
@app.route('/')
def ana_sayfa():
    return render_template('index.html')

@app.route('/klinik-test')
def klinik_test_sayfasi():
    return render_template('klinik-test.html') # Burası düzeltildi!

@app.route('/profil')
def profil_sayfasi():
    return render_template('profil.html')

@app.route('/dashboard')
def dashboard_sayfasi():
    return render_template('dashboard.html')

@app.route('/surveillance')
def surveillance_sayfasi():
    return render_template('surveillance.html')

# --- API UÇ NOKTALARI ---

@app.route('/api/guncel-haberler')
def guncel_haberler():
    url = f"https://newsapi.org/v2/everything?q=hantavirus+OR+epidemic&language=en&sortBy=publishedAt&pageSize=10&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        return jsonify(response.json())
    except:
        return jsonify({"articles": []})

@app.route('/api/lokasyonlar')
def lokasyonlar():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT DISTINCT ulke, sehir FROM vakalar ORDER BY ulke, sehir")
        rows = cursor.fetchall()
        conn.close()

        data = {}
        for ulke, sehir in rows:
            if ulke not in data:
                data[ulke] = []
            if sehir and sehir != 'nan' and sehir not in data[ulke]:
                data[ulke].append(sehir)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/harita-noktalari')
def harita_noktalari():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ulke, sehir, AVG(enlem), AVG(boylam), COUNT(*) 
            FROM vakalar 
            GROUP BY ulke, sehir
        """)
        rows = cursor.fetchall()
        conn.close()

        noktalar = []
        for ulke, sehir, enlem, boylam, vaka_sayisi in rows:
            if enlem and boylam:
                noktalar.append({
                    "ulke": ulke,
                    "sehir": sehir,
                    "enlem": enlem,
                    "boylam": boylam,
                    "vaka_sayisi": vaka_sayisi
                })
        return jsonify(noktalar)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/grafik-verileri')
def grafik_verileri():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        cursor.execute("SELECT yil, COUNT(*) FROM vakalar GROUP BY yil ORDER BY yil")
        yil_rows = cursor.fetchall()
        yillar = [r[0] for r in yil_rows]
        vaka_sayilari = [r[1] for r in yil_rows]

        cursor.execute("SELECT sonuc, COUNT(*) FROM vakalar GROUP BY sonuc")
        sonuc_rows = cursor.fetchall()
        
        iyilesen = 0
        vefat = 0
        for s, count in sonuc_rows:
            if s and ('dead' in s.lower() or 'death' in s.lower() or 'fatal' in s.lower() or 'vefat' in s.lower()):
                vefat += count
            else:
                iyilesen += count

        conn.close()
        return jsonify({
            "yillar": yillar,
            "vaka_sayilari": vaka_sayilari,
            "iyilesen": iyilesen,
            "vefat": vefat
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/klinik-analiz', methods=['POST'])
def klinik_analiz():
    try:
        verisi = request.json
        ad = verisi.get('ad', 'Gizli Kullanıcı')
        yas = int(verisi.get('yas', 30))
        cinsiyet = verisi.get('cinsiyet', 'Belirtilmemiş')
        ulke = verisi.get('ulke', '')
        sehir = verisi.get('sehir', '')
        cevre_tipi = verisi.get('cevre_tipi', '')
        semptomlar = verisi.get('semptomlar', [])

        skor = 10  # Temel başlangıç puanı
        
        # Semptom ağırlık hesaplaması
        if "Fever" in semptomlar: skor += 25
        if "Breathing Shortness" in semptomlar: skor += 30
        if "Muscle Aches" in semptomlar: skor += 15
        if "Headache" in semptomlar: skor += 10
        if "Nausea/Vomiting" in semptomlar: skor += 10

        # Çevresel maruziyet ek puanı
        if cevre_tipi in ["Forest Exposure", "Agricultural Exposure"]:
            skor += 10
        elif cevre_tipi == "Home Infestation":
            skor += 15

        # Veri setindeki o şehre ait tarihsel vaka kontrolü
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM vakalar WHERE ulke=? AND sehir=?", (ulke, sehir))
        bolgesel_vaka = cursor.fetchone()[0]
        conn.close()

        if bolgesel_vaka > 20: skor += 10
        elif bolgesel_vaka > 5: skor += 5

        if skor > 100: skor = 100

        if skor >= 75: risk_seviyesi = "KRİTİK"
        elif skor >= 50: risk_seviyesi = "YÜKSEK RİSK"
        elif skor >= 25: risk_seviyesi = "ORTA RİSK"
        else: risk_seviyesi = "DÜŞÜK RİSK"

        oneriler = ["Kemirgenlerin bulunduğu ortamlardan ve atıklardan uzak durun."]
        if risk_seviyesi in ["KRİTİK", "YÜKSEK RİSK"]:
            oneriler.append("ACİL DURUM: En yakın tam teşekküllü sağlık kuruluşuna başvurun.")
            oneriler.append("Hekiminize hantavirüs olası maruziyet senaryonuzu ve semptomlarınızı aktarın.")
            oneriler.append("Solunum destek üniteleri gerekebileceğinden istirahat edin.")
        elif risk_seviyesi == "ORTA RİSK":
            oneriler.append("Semptomların seyrini (özellikle ateş ve nefes darlığı) sonraki 48 saat yakından izleyin.")
            oneriler.append("Bulunduğunuz kapalı mekanları maske takarak havalandırın.")
        else:
            oneriler.append("Genel hijyen kurallarına uymanız yeterlidir.")

        # Testi veritabanına kaydet
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO klinik_testler (ad_soyad, yas, cinsiyet, ulke, sehir, cevre_tipi, risk_skoru, risk_seviyesi)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (ad, yas, cinsiyet, ulke, sehir, cevre_tipi, skor, risk_seviyesi))
        conn.commit()
        conn.close()

        return jsonify({
            "skor": skor,
            "risk_seviyesi": risk_seviyesi,
            "oneriler": oneriler
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/api/kullanici-gecmis')
def kullanici_gecmis():
    try:
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ad_soyad, yas, cinsiyet, ulke, sehir, risk_skoru, risk_seviyesi, tarih 
            FROM klinik_testler 
            ORDER BY tarih DESC LIMIT 3
        """)
        rows = cursor.fetchall()
        conn.close()

        gecmis = []
        for r in rows:
            gecmis.append({
                "ad_soyad": r[0], "yas": r[1], "cinsiyet": r[2],
                "ulke": r[3], "sehir": r[4], "risk_skoru": r[5],
                "risk_seviyesi": r[6], "tarih": r[7]
            })
        return jsonify(gecmis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
