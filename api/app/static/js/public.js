/* ════════════════════════════════════════════════════════════════════════════
   TEMPLE FITNESS — High-Performance Cinematic Bench Press & Scroll Engine
   Features:
   - High-DPI Canvas frame interpolation with volumetric chalk particles
   - Biomechanical J-curve barbell path tracking
   - Reversible scroll-tied scrubber with requestAnimationFrame lerp
   - Phase detection and telemetry HUD updates
   - Kinetic stats counter & IntersectionObserver reveals
   ════════════════════════════════════════════════════════════════════════════ */

document.addEventListener('DOMContentLoaded', () => {
    initScrollProgress();
    initNavScrollState();
    initBenchScrollEngine();
    initScrollRevealObserver();
    initStatsCounter();
});

/* ── 1. Scroll Progress Bar ── */
function initScrollProgress() {
    const bar = document.getElementById('scroll-progress');
    if (!bar) return;

    window.addEventListener('scroll', () => {
        const winScroll = document.documentElement.scrollTop || document.body.scrollTop;
        const totalHeight = document.documentElement.scrollHeight - document.documentElement.clientHeight;
        const scrolled = totalHeight > 0 ? (winScroll / totalHeight) * 100 : 0;
        bar.style.width = `${scrolled}%`;
    }, { passive: true });
}

/* ── 2. Navigation Bar Transparency Transition ── */
function initNavScrollState() {
    const header = document.getElementById('main-nav');
    if (!header) return;

    const onScroll = () => {
        if (window.scrollY > 40) {
            header.classList.add('scrolled');
        } else {
            header.classList.remove('scrolled');
        }
    };

    window.addEventListener('scroll', onScroll, { passive: true });
    onScroll();
}

/* ── 3. SIGNATURE BENCH PRESS SCROLL ENGINE ── */
function initBenchScrollEngine() {
    const track = document.getElementById('bench-experience');
    const canvas = document.getElementById('bench-canvas');
    if (!track || !canvas) return;

    const ctx = canvas.getContext('2d');
    if (!ctx) return;

    // Phase Text Elements
    const phases = {
        a: document.getElementById('bench-phase-a'),
        b: document.getElementById('bench-phase-b'),
        c: document.getElementById('bench-phase-c'),
        d: document.getElementById('bench-phase-d')
    };

    // HUD Elements
    const hudPhase = document.getElementById('hud-phase-label');
    const hudHeight = document.getElementById('hud-height-val');
    const hudTension = document.getElementById('hud-tension-val');
    const scrubThumb = document.getElementById('bench-thumb');
    const redOverlay = document.getElementById('bench-red-overlay');

    // Load High-Res Lifter Frame
    const imgLockout = new Image();
    imgLockout.src = '/static/img/bench_lockout.jpg';

    let imagesLoaded = 0;
    const onImgLoad = () => {
        imagesLoaded++;
        renderFrame();
    };
    imgLockout.onload = onImgLoad;

    // Chalk Particles System
    const particleCount = 45;
    const particles = [];
    for (let i = 0; i < particleCount; i++) {
        particles.push({
            x: Math.random(),
            y: Math.random(),
            size: Math.random() * 2.5 + 0.8,
            speedY: (Math.random() - 0.5) * 0.0008,
            speedX: (Math.random() - 0.5) * 0.0006,
            opacity: Math.random() * 0.45 + 0.15
        });
    }

    // Scroll state tracking
    let targetProgress = 0;
    let currentProgress = 0;
    let isTicking = false;

    // Resize Canvas handling
    const resizeCanvas = () => {
        const rect = canvas.getBoundingClientRect();
        const dpr = Math.min(window.devicePixelRatio || 1, 2);
        canvas.width = rect.width * dpr;
        canvas.height = rect.height * dpr;
        renderFrame();
    };

    window.addEventListener('resize', resizeCanvas);
    resizeCanvas();

    // Scroll Calculation
    const updateScrollProgress = () => {
        const rect = track.getBoundingClientRect();
        const viewportHeight = window.innerHeight;
        const totalScrollable = rect.height - viewportHeight;

        if (totalScrollable <= 0) {
            targetProgress = 0;
        } else {
            // progress: 0 when top of container reaches top of viewport
            const scrolled = -rect.top;
            const rawProgress = scrolled / totalScrollable;
            targetProgress = Math.max(0, Math.min(1, rawProgress));
        }

        if (!isTicking) {
            isTicking = true;
            requestAnimationFrame(renderLoop);
        }
    };

    window.addEventListener('scroll', updateScrollProgress, { passive: true });
    updateScrollProgress();

    // Smooth Lerp Animation Loop
    function renderLoop() {
        // Linear interpolation for smooth cinematic motion
        const diff = targetProgress - currentProgress;
        currentProgress += diff * 0.12;

        if (Math.abs(diff) < 0.0005) {
            currentProgress = targetProgress;
            isTicking = false;
        } else {
            requestAnimationFrame(renderLoop);
        }

        renderFrame();
    }

    // Canvas Rendering Function
    function renderFrame() {
        const width = canvas.width;
        const height = canvas.height;
        const p = currentProgress;

        ctx.clearRect(0, 0, width, height);

        // ── 1. Calculate Biomechanical Phases ──
        // Phase A: 0.00 - 0.25 (Entering Arena & Lockout Setup)
        // Phase B: 0.25 - 0.55 (Eccentric Descent: Barbell lowers from lockout to chest)
        // Phase C: 0.55 - 0.85 (Concentric Drive: Barbell drives back up off chest)
        // Phase D: 0.85 - 1.00 (Full Lockout & Victory Hold)
        
        let barNormalizedHeight = 1.0; // 1.0 = top lockout, 0.0 = bottom touching chest
        let cameraZoom = 1.0 + (p * 0.05); // Subtle cinematic camera push-in

        if (p < 0.25) {
            // Phase A: Lockout
            barNormalizedHeight = 1.0;
        } else if (p < 0.55) {
            // Phase B: Lowering
            const bP = (p - 0.25) / 0.30; // 0 -> 1
            // Smooth ease in-out curve
            const eased = 0.5 - 0.5 * Math.cos(bP * Math.PI);
            barNormalizedHeight = 1.0 - eased;
        } else if (p < 0.85) {
            // Phase C: Pressing Up
            const cP = (p - 0.55) / 0.30; // 0 -> 1
            // Powerful explosive curve
            const eased = 0.5 - 0.5 * Math.cos(cP * Math.PI);
            barNormalizedHeight = eased;
        } else {
            // Phase D: Lockout Hold
            barNormalizedHeight = 1.0;
        }

        // ── 2. Compute Barbell Displacement ──
        // barNormalizedHeight: 1.0 = top lockout, 0.0 = chest touch
        const barDescentFactor = 1.0 - barNormalizedHeight; // 0 at top, 1 at bottom

        ctx.save();
        ctx.translate(width / 2, height / 2);
        ctx.scale(cameraZoom, cameraZoom);
        ctx.translate(-width / 2, -height / 2);

        // Aspect fit / cover calculation for high-res base image
        const img = imgLockout;
        if (img.complete && img.naturalWidth > 0) {
            const imgRatio = img.naturalWidth / img.naturalHeight;
            const canvasRatio = width / height;
            let dW, dH, dX, dY;

            if (canvasRatio > imgRatio) {
                dW = width;
                dH = width / imgRatio;
                dX = 0;
                dY = (height - dH) / 2;
            } else {
                dH = height;
                dW = height * imgRatio;
                dX = (width - dW) / 2;
                dY = 0;
            }

            // A. Draw Base Environment, Lifter Torso, Head, Legs and Bench
            ctx.drawImage(img, dX, dY, dW, dH);

            // B. Dynamic Barbell & Arm Eccentric Loading
            // When the lifter lowers the bar (barDescentFactor > 0), the barbell and upper arms
            // descend smoothly down to the sternum with natural J-curve trajectory.
            if (barDescentFactor > 0.005) {
                const maxDrop = dH * 0.165; // Bar travels down to lower sternum
                const currentDropY = barDescentFactor * maxDrop;
                const jCurveX = -Math.sin(barDescentFactor * Math.PI) * (dW * 0.008);

                ctx.save();
                
                // Clip region for barbell, plates, hands, and upper arms (top 42% of lifter)
                ctx.beginPath();
                ctx.rect(dX, dY, dW, dH * 0.44 + currentDropY);
                ctx.clip();

                // Translate barbell & arms down toward chest
                ctx.translate(jCurveX, currentDropY);

                // Slight dynamic barbell bend & plate inertia on deceleration
                const flexAngle = (p >= 0.48 && p <= 0.62) ? Math.sin((p - 0.48) / 0.14 * Math.PI * 2) * 0.35 : 0;
                if (Math.abs(flexAngle) > 0.01) {
                    ctx.translate(dX + dW * 0.5, dY + dH * 0.32);
                    ctx.rotate((flexAngle * Math.PI) / 180);
                    ctx.translate(-(dX + dW * 0.5), -(dY + dH * 0.32));
                }

                // Draw moving Barbell, Weights & Arms from source
                ctx.drawImage(
                    img,
                    0, 0, img.naturalWidth, img.naturalHeight * 0.44,
                    dX, dY, dW, dH * 0.44
                );

                ctx.restore();

                // C. Soft feathered blend along the sternum contact zone
                const blendHeight = dH * 0.08;
                const blendY = dY + (dH * 0.40) + currentDropY;
                const featherGrad = ctx.createLinearGradient(0, blendY - blendHeight, 0, blendY + blendHeight);
                featherGrad.addColorStop(0, 'rgba(8, 8, 8, 0)');
                featherGrad.addColorStop(0.5, `rgba(8, 8, 8, ${(barDescentFactor * 0.45).toFixed(2)})`);
                featherGrad.addColorStop(1, 'rgba(8, 8, 8, 0)');
                ctx.fillStyle = featherGrad;
                ctx.fillRect(dX + dW * 0.25, blendY - blendHeight, dW * 0.50, blendHeight * 2);
            }

        } else {
            // Dark fallback if image is loading
            ctx.fillStyle = '#080808';
            ctx.fillRect(0, 0, width, height);
        }

        // ── 3. Overhead Volumetric Spotlight Beam ──
        const spotGrad = ctx.createRadialGradient(
            width * 0.5, height * 0.02, 10,
            width * 0.5, height * 0.45, height * 0.65
        );
        spotGrad.addColorStop(0, 'rgba(255, 255, 255, 0.18)');
        spotGrad.addColorStop(0.4, 'rgba(255, 255, 255, 0.05)');
        spotGrad.addColorStop(1, 'rgba(0, 0, 0, 0)');
        ctx.fillStyle = spotGrad;
        ctx.fillRect(0, 0, width, height);

        // ── 4. Dynamic Red Rim Lighting on Effort (Concentric Phase) ──
        let effortIntensity = 0;
        if (p >= 0.48 && p <= 0.88) {
            effortIntensity = Math.sin(((p - 0.48) / 0.40) * Math.PI);
        }
        if (effortIntensity > 0.02) {
            const redGlow = ctx.createRadialGradient(
                width * 0.52, height * 0.55, 20,
                width * 0.52, height * 0.55, height * 0.50
            );
            redGlow.addColorStop(0, `rgba(255, 45, 45, ${(effortIntensity * 0.32).toFixed(3)})`);
            redGlow.addColorStop(0.55, `rgba(255, 45, 45, ${(effortIntensity * 0.12).toFixed(3)})`);
            redGlow.addColorStop(1, 'transparent');
            ctx.fillStyle = redGlow;
            ctx.fillRect(0, 0, width, height);
        }

        // ── 5. Atmospheric Floating Chalk Particles ──
        ctx.fillStyle = 'rgba(255, 255, 255, 0.65)';
        particles.forEach(pt => {
            pt.x += pt.speedX;
            pt.y += pt.speedY;

            // Extra upward drift during concentric explosion
            if (effortIntensity > 0.1) {
                pt.y -= effortIntensity * 0.0015;
            }

            // Wrap around
            if (pt.x < 0) pt.x = 1;
            if (pt.x > 1) pt.x = 0;
            if (pt.y < 0) pt.y = 1;
            if (pt.y > 1) pt.y = 0;

            const px = pt.x * width;
            const py = pt.y * height;

            ctx.save();
            ctx.globalAlpha = pt.opacity * (1 + effortIntensity * 0.5);
            ctx.beginPath();
            ctx.arc(px, py, pt.size, 0, Math.PI * 2);
            ctx.fill();
            ctx.restore();
        });

        ctx.restore(); // Restore camera zoom

        // ── 6. Update Phase Text Overlays & HUD ──
        updatePhaseUI(p, barNormalizedHeight, effortIntensity);
    }

    // Update Text & Telemetry
    function updatePhaseUI(p, barHeight, effort) {
        // Update Scrub Bar Thumb
        if (scrubThumb) {
            scrubThumb.style.height = `${(p * 100).toFixed(1)}%`;
        }

        // Update Red Ambient Overlay on concentric peak
        if (redOverlay) {
            redOverlay.style.opacity = (effort * 0.75).toFixed(2);
        }

        // Toggle active class on text phases
        const setPhaseActive = (activeKey) => {
            Object.keys(phases).forEach(k => {
                if (phases[k]) {
                    if (k === activeKey) {
                        phases[k].classList.add('active');
                    } else {
                        phases[k].classList.remove('active');
                    }
                }
            });
        };

        if (p < 0.25) {
            setPhaseActive('a');
            if (hudPhase) hudPhase.textContent = 'LOCKOUT SETUP';
            if (hudHeight) hudHeight.textContent = '100%';
            if (hudTension) {
                hudTension.textContent = 'SETTING BASE';
                hudTension.className = 'hud-value';
            }
        } else if (p < 0.55) {
            setPhaseActive('b');
            if (hudPhase) hudPhase.textContent = 'ECCENTRIC LOAD';
            const hPct = Math.round(barHeight * 100);
            if (hudHeight) hudHeight.textContent = `${hPct}%`;
            if (hudTension) {
                hudTension.textContent = 'CONTROLLED';
                hudTension.className = 'hud-value text-accent-red';
            }
        } else if (p < 0.85) {
            setPhaseActive('c');
            if (hudPhase) hudPhase.textContent = 'CONCENTRIC DRIVE';
            const hPct = Math.round(barHeight * 100);
            if (hudHeight) hudHeight.textContent = `${hPct}%`;
            if (hudTension) {
                hudTension.textContent = 'EXPLOSIVE';
                hudTension.className = 'hud-value text-accent-red';
            }
        } else {
            setPhaseActive('d');
            if (hudPhase) hudPhase.textContent = 'REP COMPLETE';
            if (hudHeight) hudHeight.textContent = '100%';
            if (hudTension) {
                hudTension.textContent = 'EARNED';
                hudTension.className = 'hud-value text-accent-red';
            }
        }
    }
}

/* ── 4. Scroll Reveal Observer ── */
function initScrollRevealObserver() {
    const revealEls = document.querySelectorAll('.scroll-reveal');
    const divider = document.getElementById('philosophy-divider');

    if (!revealEls.length) return;

    const checkAndReveal = () => {
        const windowHeight = window.innerHeight;
        revealEls.forEach(el => {
            const rect = el.getBoundingClientRect();
            // Reveal if top of element is within bottom 90% of screen or already scrolled past
            if (rect.top <= windowHeight * 0.90) {
                el.classList.add('revealed');
            }
        });

        if (divider) {
            const rect = divider.getBoundingClientRect();
            if (rect.top <= windowHeight * 0.90) {
                divider.classList.add('expanded');
            }
        }
    };

    window.addEventListener('scroll', checkAndReveal, { passive: true });
    window.addEventListener('resize', checkAndReveal, { passive: true });
    
    // Check immediately and on short timeouts
    checkAndReveal();
    setTimeout(checkAndReveal, 150);
    setTimeout(checkAndReveal, 600);
}

/* ── 5. Kinetic Gym Statistics Counter ── */
function initStatsCounter() {
    const counters = document.querySelectorAll('.stat-counter');
    if (!counters.length) return;

    let started = false;

    const checkCounterTrigger = () => {
        if (started) return;
        const banner = document.querySelector('.stats-banner');
        if (!banner) return;

        const rect = banner.getBoundingClientRect();
        if (rect.top <= window.innerHeight * 0.85) {
            started = true;
            counters.forEach(el => {
                const targetVal = parseInt(el.dataset.count, 10);
                if (isNaN(targetVal)) return;

                let current = 0;
                const duration = 1400; // ms
                const stepTime = 25;
                const totalSteps = duration / stepTime;
                const increment = targetVal / totalSteps;

                const timer = setInterval(() => {
                    current += increment;
                    if (current >= targetVal) {
                        el.textContent = targetVal;
                        clearInterval(timer);
                    } else {
                        el.textContent = Math.floor(current);
                    }
                }, stepTime);
            });
        }
    };

    window.addEventListener('scroll', checkCounterTrigger, { passive: true });
    checkCounterTrigger();
    setTimeout(checkCounterTrigger, 200);
}

