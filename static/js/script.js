// ===== ZAMAN GÖSTER =====
function updateTime() {
    const el = document.getElementById('current-time');
    if (!el) return;
    el.textContent = new Date().toLocaleString('tr-TR', {
        day: '2-digit', month: '2-digit', year: 'numeric',
        hour: '2-digit', minute: '2-digit'
    });
}
updateTime();
setInterval(updateTime, 60000);

// ===== AYLIK TREND GRAFİĞİ =====
async function loadTrendChart() {
    const canvas = document.getElementById('trendChart');
    if (!canvas) return;
    try {
        const res = await fetch('/api/aylik-vaka');
        const data = await res.json();
        const labels = data.map(d => d.ay).reverse();
        const values = data.map(d => d.sayi).reverse();

        new Chart(canvas, {
            type: 'line',
            data: {
                labels: labels,
                datasets: [{
                    label: 'Vaka Sayısı',
                    data: values,
                    borderColor: '#c62828',
                    backgroundColor: 'rgba(198,40,40,0.08)',
                    fill: true,
                    tension: 0.4,
                    pointRadius: 5,
                    pointBackgroundColor: '#c62828',
                    borderWidth: 2
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: {
                        beginAtZero: true,
                        ticks: { stepSize: 1, font: { size: 11 } },
                        grid: { color: 'rgba(0,0,0,0.04)' }
                    },
                    x: {
                        ticks: { font: { size: 11 } },
                        grid: { display: false }
                    }
                }
            }
        });
    } catch (e) {
        // Veri yok – demo grafik göster
        new Chart(canvas, {
            type: 'line',
            data: {
                labels: ['Oca', 'Şub', 'Mar', 'Nis', 'May'],
                datasets: [{
                    label: 'Vaka',
                    data: [3, 7, 5, 12, 8],
                    borderColor: '#c62828',
                    backgroundColor: 'rgba(198,40,40,0.08)',
                    fill: true, tension: 0.4, borderWidth: 2,
                    pointRadius: 5, pointBackgroundColor: '#c62828'
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { display: false } },
                scales: {
                    y: { beginAtZero: true, ticks: { font: { size: 11 } }, grid: { color: 'rgba(0,0,0,0.04)' } },
                    x: { ticks: { font: { size: 11 } }, grid: { display: false } }
                }
            }
        });
    }
}

// ===== RİSK DAĞILIM GRAFİĞİ =====
async function loadRiskChart() {
    const canvas = document.getElementById('riskChart');
    if (!canvas) return;
    try {
        const res = await fetch('/api/risk-dagilim');
        const data = await res.json();
        const labelMap = { 'Yüksek': '#c62828', 'Orta': '#e65100', 'Düşük': '#2e7d32' };
        const labels = data.map(d => d.seviye);
        const values = data.map(d => d.sayi);
        const colors = labels.map(l => labelMap[l] || '#90a4ae');

        new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: labels,
                datasets: [{
                    data: values,
                    backgroundColor: colors,
                    borderWidth: 2,
                    borderColor: '#fff'
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'bottom',
                        labels: { font: { size: 12 }, padding: 16 }
                    }
                },
                cutout: '65%'
            }
        });
    } catch (e) {
        new Chart(canvas, {
            type: 'doughnut',
            data: {
                labels: ['Yüksek', 'Orta', 'Düşük'],
                datasets: [{
                    data: [12, 8, 5],
                    backgroundColor: ['#c62828', '#e65100', '#2e7d32'],
                    borderWidth: 2, borderColor: '#fff'
                }]
            },
            options: {
                responsive: true, maintainAspectRatio: false,
                plugins: { legend: { position: 'bottom', labels: { font: { size: 12 }, padding: 16 } } },
                cutout: '65%'
            }
        });
    }
}

// ===== BAŞLAT =====
document.addEventListener('DOMContentLoaded', () => {
    loadTrendChart();
    loadRiskChart();
});
