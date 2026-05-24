const SEHIRLER = [
    "Adana", "Adıyaman", "Afyonkarahisar", "Ağrı", "Amasya", "Ankara", "Antalya", "Artvin", "Aydın", "Balıkesir",
    "Bilecik", "Bingöl", "Bitlis", "Bolu", "Burdur", "Bursa", "Çanakkale", "Çankırı", "Çorum", "Denizli",
    "Diyarbakır", "Edirne", "Elazığ", "Erzincan", "Erzurum", "Eskişehir", "Gaziantep", "Giresun", "Gümüşhane", "Hakkari",
    "Hatay", "Isparta", "Mersin", "İstanbul", "İzmir", "Kars", "Kastamonu", "Kayseri", "Kırklareli", "Kırşehir",
    "Kocaeli", "Konya", "Kütahya", "Malatya", "Manisa", "Kahramanmaraş", "Mardin", "Muğla", "Muş", "Nevşehir",
    "Niğde", "Ordu", "Rize", "Sakarya", "Samsun", "Siirt", "Sinop", "Sivas", "Tekirdağ", "Tokat",
    "Trabzon", "Tunceli", "Şanlıurfa", "Uşak", "Van", "Yozgat", "Zonguldak", "Aksaray", "Bayburt", "Karaman",
    "Kırıkkale", "Batman", "Şırnak", "Ardahan", "Iğdır", "Yalova", "Karabük", "Kilis", "Osmaniye", "Düzce"
];

let globalIllerData = [];

document.addEventListener("DOMContentLoaded", function() {
    setupIlDropdown();
    loadDashboardData();
});

function setupIlDropdown() {
    const select = document.getElementById("form-il");
    if(select) {
        select.innerHTML = SEHIRLER.sort((a,b) => a.localeCompare(b, 'tr')).map(il => `<option value="${il}">${il}</option>`).join("");
    }
}

function switchTab(tabId) {
    document.querySelectorAll('.tab-content').forEach(el => el.classList.remove('active-tab'));
    document.querySelectorAll('.nav-btn').forEach(el => el.classList.remove('active'));
    document.getElementById(tabId).classList.add('active-tab');
    loadDashboardData();
}

function loadDashboardData() {
    fetch('/api/istatistikler')
        .then(res => res.json())
        .then(data => {
            globalIllerData = data.iller;
            
            document.getElementById("txt-toplam-degerlendirme").innerText = data.toplam_degerlendirme;
            document.getElementById("txt-kritik-vaka").innerText = data.kritik_vaka;
            document.getElementById("txt-en-etkili").innerText = data.en_cok_etkilenen_bolge;
            if(document.getElementById("lbl-toplam")) document.getElementById("lbl-toplam").innerText = data.toplam_degerlendirme;

            renderMapGrid(data.iller);

            const top10 = data.iller.slice(0, 10);
            document.getElementById("donut-top-10").innerHTML = top10.map(il => `
                <div style="margin-bottom: 8px;">
                    ● <strong>${il.il_adi}</strong>: ${il.vaka_sayisi} Vaka 
                    <span style="color:var(--warning-orange)">(${il.risk_seviyesi})</span>
                </div>
            `).join("");

            filterMap('Tümü');
        });
}

function renderMapGrid(iller) {
    const haritaAlani = document.getElementById("svg-turkiye-haritasi");
    if(!haritaAlani) return;

    haritaAlani.innerHTML = iller.map(il => {
        let color = "#38a169"; 
        if(il.risk_seviyesi === "Kritik" || il.risk_seviyesi === "Critical") color = "var(--danger-red)";
        else if(il.risk_seviyesi === "Yüksek" || il.risk_seviyesi === "High") color = "var(--warning-orange)";
        else if(il.risk_seviyesi === "Orta" || il.risk_seviyesi === "Medium") color = "yellow";

        return `
            <div class="map-province-node" style="border-bottom: 3px solid ${color};" title="${il.il_adi}: ${il.vaka_sayisi} Vaka">
                <strong>${il.il_adi.substring(0, 6)}</strong><br>${il.vaka_sayisi}
            </div>
        `;
    }).join("");
}

function filterMap(riskSeviyesi) {
    const kartAlani = document.getElementById("iller-kart-alani");
    if(!kartAlani) return;

    document.querySelectorAll('.filter-btn').forEach(btn => {
        if(btn.innerText.includes(riskSeviyesi)) btn.classList.add('active');
        else btn.classList.remove('active');
    });

    const filtrelenmis = globalIllerData.filter(il => riskSeviyesi === 'Tümü' || il.risk_seviyesi === riskSeviyesi);

    kartAlani.innerHTML = filtrelenmis.map(il => `
        <div class="il-card risk-${il.risk_seviyesi}">
            <h4>${il.il_adi}</h4>
            <p>Mevcut Vaka: ${il.vaka_sayisi}</p>
            <small>Durum: ${il.risk_seviyesi}</small>
        </div>
    `).join("");
}

function nextStep(stepNum) {
    document.querySelectorAll('.form-step').forEach(el => el.classList.remove('active-step'));
    document.getElementById(`step-${stepNum}`).classList.add('active-step');
    document.querySelectorAll('.wiz-step').forEach(el => el.classList.remove('active'));
    document.getElementById(`step-btn-${stepNum}`).classList.add('active');
}

function prevStep(stepNum) { nextStep(stepNum); }

function hesaplaRisk() {
    const ad = document.getElementById("form-ad").value;
    const il = document.getElementById("form-il").value;

    const maruziyetler = [];
    document.querySelectorAll('input[name="maruziyet"]:checked').forEach(el => maruziyetler.push(el.value));

    const belirtiler = [];
    document.querySelectorAll('input[name="belirti"]:checked').forEach(el => belirtiler.push(el.value));

    fetch('/api/risk-analizi', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ ad: ad, il: il, maruziyet: maruziyetler, belirtiler: belirtiler })
    })
    .then(res => res.json())
    .then(resData => {
        document.getElementById("lbl-result-user").innerText = `${ad} — İnceleme Bölgesi: ${il}`;
        document.getElementById("lbl-result-score").innerText = resData.skor;
        document.getElementById("badge-risk-seviye").innerText = `HESAPLANAN DURUM: ${resData.risk_seviyesi}`;
        nextStep(4);
    });
}

function resetForm() {
    document.getElementById("risk-form").reset();
    nextStep(1);
}
