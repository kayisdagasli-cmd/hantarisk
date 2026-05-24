import os
import sqlite3
import csv
from flask import Flask, render_template, request, jsonify

app = Flask(
    __name__,
    template_folder='şablonlar',
    static_folder='statik'
)

DATABASE = 'veritabani.db'
CSV_FILE = 'global_hantavirus_surveillance_dataset_2026.csv'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db_from_kaggle_csv():
    """Kaggle veri setinden 81 ili ve vaka verilerini veritabanına yükler."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS iller (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            il_adi TEXT UNIQUE,
            vaka_sayisi INTEGER DEFAULT 0,
            risk_seviyesi TEXT DEFAULT 'Düşük'
        )
    ''')
    
    # 81 İl Listesi (CSV'de eksik il olma ihtimaline karşı ana şablon)
    turkiye_iller = [
        "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir",
        "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli",
        "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari",
        "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir",
        "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir",
        "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat",
        "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman",
        "Kırıkkale", "Batman", "Şırnak", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"
    ]
    
    # Önce tüm illeri varsayılan 0 vaka ile oluştur
    for il in turkiye_iller:
        cursor.execute('INSERT OR IGNORE INTO iller (il_adi, vaka_sayisi, risk_seviyesi) VALUES (?, 0, "Düşük")', (il,))
    
    # Eğer Kaggle CSV dosyası mevcutsa verileri oku ve veritabanını güncelle
    if os.path.exists(CSV_FILE):
        with open(CSV_FILE, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            # CSV kolon başlıklarına göre burayı esnetebilirsiniz (Örn: 'il_adi', 'vaka', 'risk')
            for row in reader:
                il_adi = row.get('il_adi') or row.get('Province') or row.get('City')
                vaka = row.get('vaka_sayisi') or row.get('Cases') or 0
                risk = row.get('risk_seviyesi') or row.get('Risk') or 'Düşük'
                
                if il_adi in turkiye_iller:
                    cursor.execute('''
                        UPDATE iller 
                        SET vaka_sayisi = ?, risk_seviyesi = ? 
                        WHERE il_adi = ?
                    ''', (int(vaka), risk, il_adi))
                    
    conn.commit()
    conn.close()

# Veritabanını Kaggle verisiyle senkronize eterek başlat
init_db_from_kaggle_csv()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/istatistikler')
def istatistikler():
    conn = get_db()
    cursor = conn.cursor()
    cursor.execute('SELECT il_adi, vaka_sayisi, risk_seviyesi FROM iller ORDER BY vaka_sayisi DESC')
    iller_data = [dict(row) for row in cursor.fetchall()]
    
    toplam_degerlendirme = sum(item['vaka_sayisi'] for item in iller_data)
    kritik_vaka = sum(item['vaka_sayisi'] for item in iller_data if item['risk_seviyesi'] in ['Kritik', 'Critical'])
    en_cok_etkilenen = iller_data[0]['il_adi'] if iller_data and iller_data[0]['vaka_sayisi'] > 0 else "İzmir"
    
    conn.close()
    return jsonify({
        "iller": iller_data,
        "toplam_degerlendirme": toplam_degerlendirme,
        "kritik_vaka": kritik_vaka,
        "en_cok_etkilenen_bolge": en_cok_etkilenen
    })

@app.route('/api/risk-analizi', methods=['POST'])
def risk_analizi():
    data = request.json
    skor = 0
    
    maruziyet = data.get('maruziyet', [])
    if 'kemirgen' in maruziyet: skor += 30
    if 'acik_alan' in maruziyet: skor += 15
    if 'toz' in maruziyet: skor += 20
    if 'seyahat' in maruziyet: skor += 15
    if 'bagisiklik' in maruziyet: skor += 10
        
    belirtiler = data.get('belirtiler', [])
    if 'ateş' in belirtiler: skor += 25
    if 'bas_agrisi' in belirtiler: skor += 10
    if 'yorgunluk' in belirtiler: skor += 10
    if 'kas_agrisi' in belirtiler: skor += 15
    if 'bulanti' in belirtiler: skor += 10
    if 'nefes' in belirtiler: skor += 30

    skor = min(skor, 100)
    
    if skor >= 75: seviye = "KRİTİK"
    elif skor >= 50: seviye = "YÜKSEK"
    elif skor >= 25: seviye = "ORTA"
    else: seviye = "DÜŞÜK"
        
    il = data.get('il')
    if il:
        conn = get_db()
        cursor = conn.cursor()
        db_risk = "Düşük"
        if seviye in ["KRİTİK", "YÜKSEK"]: db_risk = "Kritik" if seviye == "KRİTİK" else "Yüksek"
        elif seviye == "ORTA": db_risk = "Orta"
        
        cursor.execute('''
            UPDATE iller 
            SET vaka_sayisi = vaka_sayisi + 1, risk_seviyesi = ? 
            WHERE il_adi = ?
        ''', (db_risk, il))
        conn.commit()
        conn.close()

    return jsonify({
        "skor": skor,
        "risk_seviyesi": seviye
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
