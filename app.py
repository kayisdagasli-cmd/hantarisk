from flask import Flask, render_template, request, jsonify, redirect, url_for
import sqlite3
import os
from datetime import datetime

app = Flask(__name__)
DATABASE = 'database.db'

def get_db():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.executescript('''
            CREATE TABLE IF NOT EXISTS vakalar (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                il TEXT NOT NULL,
                ilce TEXT NOT NULL,
                tani_tarihi TEXT NOT NULL,
                semptom_siddeti TEXT NOT NULL,
                temas_tipi TEXT NOT NULL,
                yas INTEGER,
                cinsiyet TEXT,
                risk_skoru INTEGER DEFAULT 0,
                durum TEXT DEFAULT 'Yeni',
                notlar TEXT,
                olusturma_tarihi TEXT DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS risk_bolgeleri (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                bolge_adi TEXT NOT NULL,
                il TEXT NOT NULL,
                risk_seviyesi TEXT NOT NULL,
                risk_skoru INTEGER NOT NULL,
                vaka_sayisi INTEGER DEFAULT 0,
                son_guncelleme TEXT DEFAULT CURRENT_TIMESTAMP
            );

            INSERT OR IGNORE INTO risk_bolgeleri (id, bolge_adi, il, risk_seviyesi, risk_skoru, vaka_sayisi)
            VALUES
                (1, 'Karadeniz Bölgesi', 'Kastamonu', 'Yüksek', 85, 47),
                (2, 'Karadeniz Bölgesi', 'Artvin', 'Yüksek', 82, 38),
                (3, 'Ege Bölgesi', 'İzmir', 'Orta', 68, 21),
                (4, 'İç Anadolu', 'Ankara', 'Düşük', 45, 12),
                (5, 'Marmara', 'Bursa', 'Çok Düşük', 22, 5);
        ''')

def hesapla_risk_skoru(semptom_siddeti, temas_tipi, yas):
    skor = 0
    if semptom_siddeti == 'Şiddetli':
        skor += 50
    elif semptom_siddeti == 'Orta':
        skor += 30
    else:
        skor += 10

    if temas_tipi == 'Kırsal Alan':
        skor += 30
    elif temas_tipi == 'Tarım':
        skor += 25
    elif temas_tipi == 'Mesken':
        skor += 15
    else:
        skor += 5

    if yas and yas > 60:
        skor += 20
    elif yas and yas < 12:
        skor += 15
    else:
        skor += 5

    return min(skor, 100)

@app.route('/')
def index():
    db = get_db()
    vakalar = db.execute(
        'SELECT * FROM vakalar ORDER BY olusturma_tarihi DESC LIMIT 10'
    ).fetchall()
    bolgeler = db.execute(
        'SELECT * FROM risk_bolgeleri ORDER BY risk_skoru DESC'
    ).fetchall()

    toplam_vaka = db.execute('SELECT COUNT(*) as c FROM vakalar').fetchone()['c']
    aktif_bolge = db.execute(
        "SELECT COUNT(*) as c FROM risk_bolgeleri WHERE risk_seviyesi IN ('Yüksek','Orta')"
    ).fetchone()['c']
    ort_risk = db.execute('SELECT AVG(risk_skoru) as a FROM vakalar').fetchone()['a']
    ort_risk = round(ort_risk) if ort_risk else 0

    db.close()
    return render_template(
        'index.html',
        vakalar=vakalar,
        bolgeler=bolgeler,
        toplam_vaka=toplam_vaka,
        aktif_bolge=aktif_bolge,
        ort_risk=ort_risk
    )

@app.route('/vaka-ekle', methods=['GET', 'POST'])
def vaka_ekle():
    if request.method == 'POST':
        il = request.form.get('il', '').strip()
        ilce = request.form.get('ilce', '').strip()
        tani_tarihi = request.form.get('tani_tarihi', '')
        semptom_siddeti = request.form.get('semptom_siddeti', '')
        temas_tipi = request.form.get('temas_tipi', '')
        yas = request.form.get('yas', None)
        cinsiyet = request.form.get('cinsiyet', '')
        notlar = request.form.get('notlar', '')

        try:
            yas_int = int(yas) if yas else None
        except ValueError:
            yas_int = None

        risk_skoru = hesapla_risk_skoru(semptom_siddeti, temas_tipi, yas_int)

        if risk_skoru >= 70:
            risk_seviyesi = 'Yüksek'
        elif risk_skoru >= 40:
            risk_seviyesi = 'Orta'
        else:
            risk_seviyesi = 'Düşük'

        db = get_db()
        db.execute(
            '''INSERT INTO vakalar
               (il, ilce, tani_tarihi, semptom_siddeti, temas_tipi, yas, cinsiyet, risk_skoru, durum, notlar)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)''',
            (il, ilce, tani_tarihi, semptom_siddeti, temas_tipi, yas_int, cinsiyet, risk_skoru, 'Yeni', notlar)
        )
        db.commit()
        db.close()
        return redirect(url_for('index'))

    return render_template('vaka_ekle.html')

@app.route('/api/vakalar')
def api_vakalar():
    db = get_db()
    vakalar = db.execute('SELECT * FROM vakalar ORDER BY olusturma_tarihi DESC').fetchall()
    db.close()
    return jsonify([dict(v) for v in vakalar])

@app.route('/api/risk-dagilim')
def api_risk_dagilim():
    db = get_db()
    rows = db.execute(
        '''SELECT risk_skoru,
           CASE
               WHEN risk_skoru >= 70 THEN "Yüksek"
               WHEN risk_skoru >= 40 THEN "Orta"
               ELSE "Düşük"
           END as seviye,
           COUNT(*) as sayi
           FROM vakalar GROUP BY seviye'''
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

@app.route('/api/aylik-vaka')
def api_aylik_vaka():
    db = get_db()
    rows = db.execute(
        '''SELECT substr(tani_tarihi, 1, 7) as ay, COUNT(*) as sayi
           FROM vakalar GROUP BY ay ORDER BY ay DESC LIMIT 12'''
    ).fetchall()
    db.close()
    return jsonify([dict(r) for r in rows])

if __name__ == '__main__':
    init_db()
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=False)
