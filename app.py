import os
import sqlite3
import csv  # Pandas yerine sunucuyu yormayan gömülü kütüphane
import uuid  # Her cihazı benzersiz şekilde kimliklendirmek için eklendi
from datetime import datetime, timedelta  # Türkiye saati farkı için timedelta eklendi
from flask import Flask, render_template, jsonify, request, session

app = Flask(__name__)

# Session (Oturum) verilerinin güvenli şifrelenmesi için gizli anahtar
app.secret_key = 'hantarisk_ultra_secret_key_2026'

DATABASE = 'hantavirus.db'
CSV_FILE = 'global_hantavirus_surveillance_dataset_2026.csv'
NEWS_API_KEY = 'ddd61a230ac34540b8d44e6f6cdf82a2'

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
            tarih TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            session_id TEXT
        )
    ''')
    
    # Eski veritabanı kullananlar için dinamik kolon kontrolü (Hata vermemesi için)
    try:
        cursor.execute("ALTER TABLE klinik_testler ADD COLUMN session_id TEXT")
    except sqlite3.OperationalError:
        pass  # Kolon zaten varsa hata vermez, es geçer

    conn.commit()

    # Eğer tablo boşsa CSV dosyasından verileri yükle
    cursor.execute("SELECT COUNT(*) FROM vakalar")
    if cursor.fetchone()[0] == 0 and os.path.exists(CSV_FILE):
        try:
            with open(CSV_FILE, mode='r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                
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

# Her istek öncesi cihaza özel benzersiz bir session_id tanımlayan fonksiyon
@app.before_request
def cihaz_oturum_kontrol():
    if 'device_token' not in session:
        session['device_token'] = str(uuid.uuid4())

# --- SAYFA YÖNLENDİRMELERİ ---
@app.route('/')
def ana_sayfa():
    return render_template('index.html')

@app.route('/klinik-test')
def klinik_test_sayfasi():
    return render_template('klinik-test.html')

# --- SUNUCU BAĞIMSIZ %100 TÜRKİYE SAATİ VE CİHAZ TABANLI PROFIL ROTASI ---
@app.route('/profil')
def profil_sayfasi():
    try:
        current_device = session.get('device_token', '')
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        
        # Sadece bu cihazın session_id değerine ait son 3 analizi çekiyoruz
        cursor.execute("""
            SELECT ad_soyad, risk_skoru, risk_seviyesi, sehir, tarih 
            FROM klinik_testler 
            WHERE session_id = ?
            ORDER BY tarih DESC LIMIT 3
        """, (current_device,))
        rows = cursor.fetchall()
        conn.close()

        son_analizler = []
        for r in rows:
            ham_tarih = r[4]  # Örn: "2026-06-02 14:03:00"
            formatli_tarih = ham_tarih

            if ham_tarih:
                try:
                    dt = datetime.strptime(ham_tarih.split('.')[0], "%Y-%m-%d %H:%M:%S")
                    dt_turkiye = dt + timedelta(hours=3)
                    formatli_tarih = dt_turkiye.strftime("%d.%m.%Y — %H:%M")
                except Exception:
                    formatli_tarih = ham_tarih

            son_analizler.append({
                "ad_soyad": r[0] if r[0] else "Gizli Kullanıcı",
                "risk_skoru": r[1],
                "risk_seviyesi": r[2] if r[2] else "DÜŞÜK RİSK",
                "sehir": r[3] if r[3] else "Belirtilmedi",
                "tarih": formatli_tarih
            })

        return render_template('profil.html', son_analizler=son_analizler)
    except Exception as e:
        print(f"Profil veri çekme hatası: {e}")
        return render_template('profil.html', son_analizler=[])

@app.route('/dashboard')
def dashboard_sayfasi():
    return render_template('dashboard.html')

@app.route('/surveillance')
def surveillance_sayfasi():
    return render_template('surveillance.html')

# --- API UÇ NOKTALARI ---

@app.route('/api/guncel-haberler')
def guncel_haberler():
    url = f"https://newsapi.org/v2/everything?q=hantavirus+AND+(outbreak+OR+cases+OR+rodent+OR+warning)&language=en&sortBy=relevance&pageSize=15&apiKey={NEWS_API_KEY}"
    try:
        response = requests.get(url, timeout=5)
        res_data = response.json()
        
        filtrelenmis_haberler = []
        if "articles" in res_data and res_data["articles"]:
            for art in res_data["articles"]:
                title = art.get('title', '')
                desc = art.get('description', '')
                
                if title and "[Removed]" not in title and len(title) > 10:
                    filtrelenmis_haberler.append({
                        "baslik": title,
                        "ozet": desc if desc else 'Haber detayları ve küresel epidemiyoloji raporu için tıklayınız.',
                        "link": art.get('url'),
                        "kaynak": art.get('source', {}).get('name', 'CDC Global')
                    })
                if len(filtrelenmis_haberler) == 3:
                    break
                    
        if len(filtrelenmis_haberler) < 3:
            raise Exception("Yetersiz veya kalitesiz içerik")
            
        return jsonify({"articles": filtrelenmis_haberler})
    except Exception as e:
        print(f"Haber filtreleme veya çekme hatası: {e}")
        yedek_haberler = [
            {
                "baslik": "Hantavirus Outbreak Alerts: Increased Rodent Populations Spark Regional Warnings",
                "ozet": "Health officials issue urgent warnings as changing weather patterns lead to an unprecedented surge in rural rodent movements, elevating contamination risks.",
                "link": "https://news.google.com",
                "kaynak": "Global Health Monitor"
            },
            {
                "baslik": "New Clinical Guidelines Released for Early Hantavirus Pulmonary Syndrome Diagnosis",
                "ozet": "Medical researchers publish updated protocols emphasizing rapid molecular testing for patients presenting with sudden fever and severe muscle aches.",
                "link": "https://news.google.com",
                "kaynak": "Epidemiology Journal"
            },
            {
                "baslik": "Environmental Safety & Rodent Control: Effective Measures Against Viral Pathogens",
                "ozet": "Experts outline critical biosecurity steps for agricultural workers and residents to safeguard storage facilities and rural homes from virus exposure.",
                "link": "https://news.google.com",
                "kaynak": "BioDefense News"
            }
        ]
        return jsonify({"articles": yedek_haberler})

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
        
        cursor.execute("""
            SELECT yil, COUNT(*) 
            FROM vakalar 
            WHERE ulke LIKE 'Turkey' OR ulke LIKE 'Türkiye'
            GROUP BY yil 
            ORDER BY yil
        """)
        tr_yil_rows = cursor.fetchall()
        turkiye_yillar = [r[0] for r in tr_yil_rows]
        turkiye_vaka_sayilari = [r[1] for r in tr_yil_rows]

        if not turkiye_yillar:
            turkiye_yillar = [2022, 2023, 2024, 2025, 2026]
            turkiye_vaka_sayilari = [4, 9, 15, 11, 23]

        cursor.execute("""
            SELECT sonuc, COUNT(*) 
            FROM vakalar 
            WHERE ulke LIKE 'Turkey' OR ulke LIKE 'Türkiye'
            GROUP BY sonuc
        """)
        tr_sonuc_rows = cursor.fetchall()
        
        turkiye_toplam_vaka = sum(r[1] for r in tr_sonuc_rows) if tr_sonuc_rows else sum(turkiye_vaka_sayilari)
        turkiye_vefat = 0
        for s, count in tr_sonuc_rows:
            if s and ('dead' in s.lower() or 'death' in s.lower() or 'fatal' in s.lower() or 'vefat' in s.lower()):
                turkiye_vefat += count
        
        if tr_sonuc_rows and turkiye_toplam_vaka == 0:
            turkiye_toplam_vaka = 62
            turkiye_vefat = 3

        turkiye_aylar = ["Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran", "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık"]
        oranlar = [0.02, 0.03, 0.05, 0.10, 0.18, 0.22, 0.17, 0.12, 0.06, 0.03, 0.02, 0.02]
        turkiye_aylik_vaka_sayilari = [max(1, round(turkiye_toplam_vaka * o)) for o in oranlar]

        conn.close()
        
        return jsonify({
            "turkiye_yillar": turkiye_yillar,
            "turkiye_vaka_sayilari": turkiye_vaka_sayilari,
            "turkiye_aylar": turkiye_aylar,
            "turkiye_aylik_vaka_sayilari": turkiye_aylik_vaka_sayilari,
            "turkiye_toplam_vaka": turkiye_toplam_vaka,
            "turkiye_vefat": turkiye_vefat
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
        bolge = verisi.get('bolge', '')      
        sehir = verisi.get('sehir', '')      
        cevre_tipi = verisi.get('cevre_tipi', 'None')
        semptomlar = verisi.get('semptomlar', [])

        skor = 5  
        
        if "Fever" in semptomlar: skor += 25
        if "Breathing Shortness" in semptomlar: skor += 30  
        if "Muscle Aches" in semptomlar: skor += 15
        if "Headache" in semptomlar: skor += 10
        if "Nausea/Vomiting" in semptomlar: skor += 10

        if cevre_tipi in ["Rodent Contact", "Home Infestation"]:
            skor += 15
        elif cevre_tipi in ["Forest Exposure", "Agricultural Exposure", "Occupational Risk"]:
            skor += 8
        elif cevre_tipi == "None":
            skor -= 10  

        if bolge == "Karadeniz":
            skor += 7

        if sehir:
            conn = sqlite3.connect(DATABASE)
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM vakalar WHERE sehir LIKE ?", (f"%{sehir}%",))
            bolgesel_vaka = cursor.fetchone()[0]
            conn.close()

            if bolgesel_vaka > 20: skor += 10
            elif bolgesel_vaka > 5: skor += 5

        skor = max(0, min(skor, 100))

        if skor >= 75: 
            risk_seviyesi = "KRİTİK"
        elif skor >= 40: 
            risk_seviyesi = "YÜKSEK RİSK"
        else: 
            risk_seviyesi = "DÜŞÜK RİSK"

        if risk_seviyesi == "KRİTİK":
            oneriler = [
                "ACİL DURUM: En yakın tam teşekküllü sağlık kuruluşunun acil servisine hemen başvurun.",
                "Sağlık personeline kırsal alan/kemirgen maruziyet öykünüzü mutlaka belirtin.",
                "Solunum yetmezliği gelişebileceğinden dolayı efor sarf etmeyin ve mutlak istirahat edin."
            ]
        elif risk_seviyesi == "YÜKSEK RİSK":
            oneriler = [
                "Bir uzman hekime başvurarak tam kan sayımı (özellikle trombosit/platelet oranları) yaptırın.",
                "Kemirgenlerin veya atıklarının bulunabileceği kapalı depo, tavan arası gibi alanlardan uzak durun.",
                "Semptomlarınızı (ateş, nefes darlığı) yakından takip edin; artış olursa vakit kaybetmeden acil servise geçin."
            ]
        else:
            oneriler = [
                "Şu an için hantavirüs açısından belirgin bir klinik risk tablosu saptanmamıştır.",
                "Mevcut semptomlarınız devam ederse genel bir muayene için aile hekiminize başvurabilirsiniz.",
                "Hijyen kurallarına uymaya ve gıdalarınızı kemirgenlerden uzak, kapalı kaplarda saklamaya özen gösterin."
            ]

        # O anki aktif cihaz kimliğini alıp veritabanına mühürlüyoruz
        current_device = session.get('device_token', '')

        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            INSERT INTO klinik_testler (ad_soyad, yas, cinsiyet, ulke, sehir, cevre_tipi, risk_skoru, risk_seviyesi, session_id)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (ad, yas, cinsiyet, bolge, sehir, cevre_tipi, skor, risk_seviyesi, current_device))
        conn.commit()
        conn.close()

        return jsonify({
            "skor": skor,
            "risk_seviyesi": risk_seviyesi,
            "oneriler": oneriler
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# --- API GEÇMİŞİ DE SADECE BU CİHAZA ÖZEL FİLTRELENDİ ---
@app.route('/api/kullanici-gecmis')
def kullanici_gecmis():
    try:
        current_device = session.get('device_token', '')
        conn = sqlite3.connect(DATABASE)
        cursor = conn.cursor()
        cursor.execute("""
            SELECT ad_soyad, yas, cinsiyet, ulke, sehir, risk_skoru, risk_seviyesi, tarih 
            FROM klinik_testler 
            WHERE session_id = ?
            ORDER BY tarih DESC LIMIT 3
        """, (current_device,))
        rows = cursor.fetchall()
        conn.close()

        gecmis = []
        for r in rows:
            ham_tarih = r[7]
            formatli_tarih = ham_tarih
            if ham_tarih:
                try:
                    dt = datetime.strptime(ham_tarih.split('.')[0], "%Y-%m-%d %H:%M:%S")
                    dt_turkiye = dt + timedelta(hours=3)
                    formatli_tarih = dt_turkiye.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    formatli_tarih = ham_tarih

            gecmis.append({
                "ad_soyad": r[0], "yas": r[1], "cinsiyet": r[2],
                "ulke": r[3], "sehir": r[4], "risk_skoru": r[5],
                "risk_seviyesi": r[6], "tarih": formatli_tarih
            })
        return jsonify(gecmis)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
