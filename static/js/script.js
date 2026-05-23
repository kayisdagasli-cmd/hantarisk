document.addEventListener('DOMContentLoaded', function () {
    console.log('HantaRisk Sistem Arayüzü Aktif!');

    // 1. Analiz Formu Gönderilirken Yükleniyor Animasyonu Çıkarma
    const analizFormu = document.querySelector('form[action="/analiz"]');
    if (analizFormu) {
        analizFormu.addEventListener('submit', function () {
            const buton = analizFormu.querySelector('button[type="submit"]');
            buton.innerHTML = '<i class="fa-solid fa-spinner animate-spin mr-2"></i> Yapay Zeka Analiz Ediyor...';
            buton.disabled = true;
            buton.classList.remove('bg-red-600', 'hover:bg-red-700');
            buton.classList.add('bg-slate-600', 'cursor-not-allowed');
        });
    }

    // 2. Tablo Satırlarına Giriş Animasyonu Tanımlama
    const tabloSatirlari = document.querySelectorAll('tbody tr');
    tabloSatirlari.forEach((satir, index) => {
        satir.classList.add('animate__animated', 'animate__fadeInUp');
        satir.style.animationDelay = `${index * 0.05}s`;
    });
});
