import os
import sqlite3
import datetime
import pandas as pd
import numpy as np
from flask import Flask, render_template, request, redirect, url_for, flash, send_file
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import matplotlib
matplotlib.use('Agg')  # Sunucu ortamlarında grafik çizimi için
import matplotlib.pyplot as plt
import seaborn as sns

app = Flask(__name__, 
            static_folder='statik', 
            template_folder='şablonlar')

app.config['SECRET_KEY'] = 'hantavirus_gizli_anahtar_1234'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///veritabanı.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)
login_manager = LoginManager(app)
login_manager.login_view = 'giris'

# ------------------------------------------------------------------
# VERİTABANI MODELLERİ (SQLite)
# ------------------------------------------------------------------
class Kullanici(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kullanici_adi = db.Column(db.String(50), unique=True, nullable=False)
    sifre = db.Column(db.String(100), nullable=False)
    rol = db.Column(db.String(20), default='kullanici') # admin veya kullanici

class AnalizGecmisi(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    kullanici_id = db.Column(db.Integer, db.ForeignKey('kullanici.id'), nullable=False)
    yas = db.Column(db.Integer)
    ates = db.Column(db.Float)
    kas_agrisi = db.Column(db.Integer) # 1 veya 0
    kemirgen_temas = db.Column(db.Integer) # 1 veya 0
    risk_skoru = db.Column(db.Float)
    sonuc = db.Column(db.String(50))
    tarih = db.Column(db.DateTime, default=datetime.datetime.utcnow)

@login_manager.user_loader
def load_user(user_id):
    return Kullanici.query.get(int(user_id))

# ------------------------------------------------------------------
# YAPAY ZEKA / MAKİNE ÖĞRENMESİ MODELİ (ML)
# ------------------------------------------------------------------
model = None
features = ['Age', 'Fever', 'MusclePain', 'RodentContact']

def model_egit():
    global model
    veri_yolu = 'global_hantavirus_surveillance_dataset_2026.csv'
    
    if os.path.exists(veri_yolu):
        try:
            # Gerçek Kaggle verisini veya yapısını yükle
            df = pd.read_csv(veri_yolu)
            
            # Eğer veri kümesinde eksik sütun varsa simüle et/temizle (Güvenli çalışma için)
            for col in features:
                if col not in df.columns:
                    if col == 'Fever':
                        df[col] = np.random.uniform(36.5, 40.0, size=len(df))
                    elif col == 'Age':
                        df[col] = np.random.randint(1, 80, size=len(df))
                    else:
                        df[col] = np.random.choice([0, 1], size=len(df))
            
            if 'RiskResult' not in df.columns:
                df['RiskResult'] = ((df['Fever'] > 38.5) & (df['RodentContact'] == 1)).astype(int)
            
            X = df[features]
            y = df['RiskResult']
            
            X_train, X_test, y_train, y_test = train_test_split(X, y, test_test_split=0.2, random_state=42)
            model = RandomForestClassifier(n_estimators=100, random_state=42)
            model.fit(X_train, y_train)
            print("Makine öğrenmesi modeli başarıyla eğitildi.")
        except Exception as e:
            print(f"Model eğitilirken hata oluştu, varsayılan model kuruluyor: {e}")
            varsayilan_model_kur()
    else:
        print("Kaggle veri seti bulunamadı, prototip veriyle eğitiliyor.")
        varsayilan_model_kur()

def varsayilan_model_kur():
    global model
    # Veri seti yoksa veya okunamazsa sistemin çökmemesi için sentetik veri üretimi
    np.random.seed(42)
    data = {
        'Age': np.random.randint(18, 70, 500),
        'Fever': np.random.uniform(36.0, 41.0, 500),
        'MusclePain': np.random.choice([0, 1], 500),
        'RodentContact': np.random.choice([0, 1], 500),
    }
    df = pd.DataFrame(data)
    df['RiskResult'] = ((df['Fever'] > 38.2) & (df['RodentContact'] == 1) | (df['MusclePain'] == 1)).astype(int)
    
    X = df[features]
    y = df['RiskResult']
    model = RandomForestClassifier(n_estimators=50, random_state=42)
    model.fit(X, y)

# ------------------------------------------------------------------
# ROUTER / SAYFA YÖNLENDİRMELERİ
# ------------------------------------------------------------------
@app.route('/')
def ana_sayfa():
    return render_template('index.html')

@app.route('/kayit', methods=['GET', 'POST'])
def kayit():
    if request.method == 'POST':
        kadi = request.form.get('kullanici_adi')
        sifre = request.form.get('sifre')
        
        mevcut = Kullanici.query.filter_by(kullanici_adi=kadi).first()
        if mevcut:
            flash('Bu kullanıcı adı zaten alınmış!', 'danger')
            return redirect(url_for('kayit'))
        
        # İlk kayıt olan kullanıcıyı test kolaylığı için admin yapalım
        rol = 'admin' if Kullanici.query.count() == 0 else 'kullanici'
        
        yeni_kullanici = Kullanici(kullanici_adi=kadi, sifre=sifre, rol=rol)
        db.session.add(yeni_kullanici)
        db.session.commit()
        flash('Kayıt başarılı! Giriş yapabilirsiniz.', 'success')
        return redirect(url_for('giris'))
    return render_template('kayit.html')

@app.route('/giris', methods=['GET', 'POST'])
def giris():
    if request.method == 'POST':
        kadi = request.form.get('kullanici_adi')
        sifre = request.form.get('sifre')
        user = Kullanici.query.filter_by(kullanici_adi=kadi, sifre=sifre).first()
        
        if user:
            login_user(user)
            flash('Başarıyla giriş yapıldı.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Hatalı kullanıcı adı veya şifre!', 'danger')
    return render_template('giris.html')

@app.route('/cikis')
@login_required
def cikis():
    logout_user()
    return redirect(url_for('ana_sayfa'))

@app.route('/dashboard')
@login_required
def dashboard():
    gecmis = AnalizGecmisi.query.filter_by(kullanici_id=current_user.id).all()
    return render_template('dashboard.html', gecmis=gecmis)

@app.route('/analiz', methods=['GET', 'POST'])
@login_required
def analiz():
    if request.method == 'POST':
        yas = int(request.form.get('yas'))
        ates = float(request.form.get('ates'))
        kas_agrisi = int(request.form.get('kas_agrisi'))
        kemirgen_temas = int(request.form.get('kemirgen_temas'))
        
        # Yapay zeka tahmini
        girdi = [[yas, ates, kas_agrisi, kemirgen_temas]]
        olasilik = model.predict_proba(girdi)[0][1] # Pozitif risk olasılığı
        risk_skoru = round(olasilik * 100, 2)
        
        sonuc = "Yüksek Risk" if risk_skoru >= 50 else "Düşük Risk"
        
        # Veritabanına kaydet
        yeni_analiz = AnalizGecmisi(
            kullanici_id=current_user.id,
            yas=yas, ates=ates,
            kas_agrisi=kas_agrisi,
            kemirgen_temas=kemirgen_temas,
            risk_skoru=risk_skoru,
            sonuc=sonuc
        )
        db.session.add(yeni_analiz)
        db.session.commit()
        
        return render_template('analiz_sonuc.html', skor=risk_skoru, sonuc=sonuc)
        
    return render_template('analiz.html')

@app.route('/rapor/<int:id>')
@login_required
def rapor_indir(id):
    kayit = AnalizGecmisi.query.get_or_404(id)
    if kayit.kullanici_id != current_user.id and current_user.rol != 'admin':
        return "Yetkisiz Erişim", 403
        
    pdf_yolu = f"hantavirus_rapor_{id}.pdf"
    c = canvas.Canvas(pdf_yolu, pagesize=letter)
    c.drawString(100, 750, "HANTAVIRUS RISK ANALIZ RAPORU")
    c.drawString(100, 720, f"Rapor Tarihi: {kayit.tarih.strftime('%Y-%m-%d %H:%M')}")
    c.drawString(100, 700, f"Kullanıcı ID: {kayit.kullanici_id}")
    c.drawString(100, 660, "--------------------------------------------------")
    c.drawString(100, 640, f"Hasta Yaşı: {kayit.yas}")
    c.drawString(100, 620, f"Vücut Ateşi: {kayit.ates} °C")
    c.drawString(100, 600, f"Şiddetli Kas Ağrısı: {'Var' if kayit.kas_agrisi==1 else 'Yok'}")
    c.drawString(100, 580, f"Kemirgen/Dışkı Teması: {'Var' if kayit.kemirgen_temas==1 else 'Yok'}")
    c.drawString(100, 540, "--------------------------------------------------")
    c.drawString(100, 510, f"Hesaplanan Risk Skoru: %{kayit.risk_skoru}")
    c.drawString(100, 490, f"Sonuç Değerlendirmesi: {kayit.sonuc}")
    c.save()
    
    return send_file(pdf_yolu, as_attachment=True)

@app.route('/admin')
@login_required
def admin_panel():
    if current_user.rol != 'admin':
        flash('Bu alana erişim yetkiniz yok!', 'danger')
        return redirect(url_for('dashboard'))
    tüm_kayitlar = AnalizGecmisi.query.all()
    kullanicilar = Kullanici.query.all()
    return render_template('admin.html', kayitlar=tüm_kayitlar, kullanicilar=kullanicilar)

# ------------------------------------------------------------------
# UYGULAMA BAŞLANGICI
# ------------------------------------------------------------------
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # SQLite veritabanı tablolarını oluşturur
    model_egit() # ML modelini yükler veya eğiter
    app.run(debug=True)
