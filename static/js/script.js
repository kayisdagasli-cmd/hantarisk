// Render sunucusunun hata vermemesi için en güvenli ve yalın yapı
(function() {
    "use strict";
    
    // Sayfa yüklendiğinde çalışacak güvenli fonksiyon
    window.onload = function() {
        // Form animasyonu kontrolü
        var analizFormu = document.querySelector('form[action="/analiz"]');
        if (analizFormu) {
            analizFormu.onsubmit = function() {
                var buton = analizFormu.querySelector('button[type="submit"]');
                if (buton) {
                    buton.innerHTML = 'Analiz Ediliyor...';
                    buton.disabled = true;
                }
            };
        }
    };
})();
