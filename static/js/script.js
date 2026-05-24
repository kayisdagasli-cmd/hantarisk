document.addEventListener("DOMContentLoaded", function () {
    // 1. MODAL (VİRÜS BİLGİ BUTONU) SİSTEMİ
    const modal = document.getElementById("info-modal");
    const btn = document.getElementById("btn-info-modal");
    if (modal && btn) {
        const closeSpan = modal.querySelector(".close-modal");
        const closeBtn = modal.querySelector(".close-modal-btn");

        btn.onclick = () => modal.style.display = "flex";
        if (closeSpan) closeSpan.onclick = () => modal.style.display = "none";
        if (closeBtn) closeBtn.onclick = () => modal.style.display = "none";
        
        window.onclick = (e) => {
            if (e.target === modal) modal.style.display = "none";
        };
    }

    // 2. NEWS API CANLI HABER AKIŞI
    const newsGrid = document.getElementById("news-grid");
    if (newsGrid) {
        fetch("/api/guncel-haberler")
            .then(res => res.json())
            .then(data => {
                if (data.articles && data.articles.length > 0) {
                    newsGrid.innerHTML = data.articles.slice(0, 6).map(article => `
                        <div class="news-card">
                            <div class="news-source"><i class="fa-solid fa-newspaper"></i> ${article.source.name || 'Global Sağlık'}</div>
                            <h3>${article.title}</h3>
                            <p>${article.description || 'Haber içeriği yüklenemedi.'}</p>
                            <a href="${article.url}" target="_blank" class="news-link">Detayları Oku <i class="fa-solid fa-arrow-up-right-from-square"></i></a>
                        </div>
                    `).join("");
                } else {
                    newsGrid.innerHTML = `<div class="no-news">Şu anda güncel hantavirüs haberi bulunamadı.</div>`;
                }
            })
            .catch(err => {
                console.error("Haber çekme hatası:", err);
                newsGrid.innerHTML = `<div class="no-news">Haber servisine bağlanırken bir hata oluştu.</div>`;
            });
    }

    // 3. FAREYİ TAKİP EDEN İNTERAKTİF VİRÜS ANİMASYONU (CANVAS)
    const canvas = document.getElementById("animation-canvas");
    if (canvas) {
        const ctx = canvas.getContext("2d");
        
        function resize() {
            canvas.width = window.innerWidth;
            canvas.height = window.innerHeight;
        }
        window.addEventListener("resize", resize);
        resize();

        // Fare koordinatları
        let mouse = { x: canvas.width / 2, y: canvas.height / 2, targetX: canvas.width / 2, targetY: canvas.height / 2 };

        window.addEventListener("mousemove", function (e) {
            mouse.targetX = e.clientX;
            mouse.targetY = e.clientY;
        });

        // Virüs Hücresi Sınıfı
        class VirusCell {
            constructor() {
                this.x = mouse.x;
                this.y = mouse.y;
                this.radius = 23;
                this.angle = 0;
            }

            update() {
                this.x += (mouse.targetX - this.x) * 0.08;
                this.y += (mouse.targetY - this.y) * 0.08;
                this.angle += 0.015;
            }

            draw() {
                ctx.save();
                ctx.translate(this.x, this.y);
                ctx.rotate(this.angle);

                // Parlama (Neon) Efekti
                ctx.shadowBlur = 25;
                ctx.shadowColor = "rgba(239, 68, 68, 0.7)";

                // Hücre Gövdesi
                ctx.beginPath();
                ctx.arc(0, 0, this.radius, 0, Math.PI * 2);
                ctx.fillStyle = "rgba(239, 68, 68, 0.2)";
                ctx.strokeStyle = "#ef4444";
                ctx.lineWidth = 3;
                ctx.fill();
                ctx.stroke();

                // Virüs Reseptör Uzantıları (Spikes)
                const spikes = 10;
                for (let i = 0; i < spikes; i++) {
                    const spikeAngle = (i * Math.PI * 2) / spikes;
                    const x1 = Math.cos(spikeAngle) * this.radius;
                    const y1 = Math.sin(spikeAngle) * this.radius;
                    
                    const dynamicLength = this.radius + 14 + Math.sin(this.angle * 4 + i) * 3;
                    const x2 = Math.cos(spikeAngle) * dynamicLength;
                    const y2 = Math.sin(spikeAngle) * dynamicLength;

                    ctx.beginPath();
                    ctx.moveTo(x1, y1);
                    ctx.lineTo(x2, y2);
                    ctx.strokeStyle = "#ef4444";
                    ctx.lineWidth = 2;
                    ctx.stroke();

                    ctx.beginPath();
                    ctx.arc(x2, y2, 4.5, 0, Math.PI * 2);
                    ctx.fillStyle = "#f87171";
                    ctx.fill();
                }

                ctx.restore();
            }
        }

        const virus = new VirusCell();

        function animate() {
            ctx.clearRect(0, 0, canvas.width, canvas.height);
            virus.update();
            virus.draw();
            requestAnimationFrame(animate);
        }
        animate();
    }

    // 4. MOBİL HAMBURGER MENÜ MEKANİZMASI
    const menuBtn = document.getElementById("mobile-menu-btn");
    const navMenu = document.getElementById("nav-menu-container");

    if (menuBtn && navMenu) {
        menuBtn.addEventListener("click", function() {
            navMenu.classList.toggle("active");
            
            // İkonu üç çizgiden çarpı işaretine (X) dönüştürür
            const icon = menuBtn.querySelector("i");
            if(navMenu.classList.contains("active")) {
                icon.className = "fa-solid fa-xmark";
            } else {
                icon.className = "fa-solid fa-bars";
            }
        });
    }
});
