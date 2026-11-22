/* ═══════════════════════════════════════════════════════════
   FITNESS TEMPLE — Client-side JavaScript
   Handles: attendance polling, member search, card assignment
   polling, form submissions, and UI interactions.
   ═══════════════════════════════════════════════════════════ */

// ── Utility ──

function formatTime(isoString) {
    if (!isoString) return '—';
    const d = new Date(isoString);
    return d.toLocaleTimeString('en-IN', {
        hour: '2-digit', minute: '2-digit', second: '2-digit',
        hour12: true, timeZone: 'Asia/Kolkata'
    });
}

function formatDate(isoString) {
    if (!isoString) return '—';
    const d = new Date(isoString + 'T00:00:00');
    return d.toLocaleDateString('en-IN', {
        day: '2-digit', month: 'short', year: 'numeric'
    });
}

function showAlert(container, message, type) {
    const div = document.createElement('div');
    div.className = `alert alert-${type}`;
    div.textContent = message;
    container.prepend(div);
    setTimeout(() => div.remove(), 5000);
}

// ═══════════════════════════════════════════════════════════
//  Live Attendance Polling (Home page)
// ═══════════════════════════════════════════════════════════

function initAttendancePolling() {
    const tbody = document.getElementById('attendance-tbody');
    const countEl = document.getElementById('attendance-count');
    if (!tbody) return;

    let sinceId = 0;
    let count = 0;

    // Get initial max ID from existing rows
    const rows = tbody.querySelectorAll('tr[data-id]');
    rows.forEach(row => {
        const id = parseInt(row.dataset.id, 10);
        if (id > sinceId) sinceId = id;
        count++;
    });
    if (countEl) countEl.textContent = count;

    async function poll() {
        try {
            const resp = await fetch(`/api/attendance/today?since_id=${sinceId}`);
            if (resp.status === 401) {
                window.location.href = '/login';
                return;
            }
            const data = await resp.json();

            if (data.rows && data.rows.length > 0) {
                const emptyState = document.getElementById('empty-state');
                if (emptyState) emptyState.remove();

                data.rows.forEach(row => {
                    if (row.id > sinceId) sinceId = row.id;
                    count++;

                    const tr = document.createElement('tr');
                    tr.dataset.id = row.id;
                    tr.className = row.is_expired ? 'expired new-row' : 'new-row';
                    tr.innerHTML = `
                        <td>${count}</td>
                        <td><a href="/members/${row.member_id}">${escHtml(row.name)}</a></td>
                        <td>${formatTime(row.checkin_time)}</td>
                        <td>
                            <span class="badge ${row.is_expired ? 'badge-danger' : 'badge-success'}">
                                ${formatDate(row.expiry_date)}
                            </span>
                        </td>
                    `;
                    tbody.prepend(tr);
                });

                if (countEl) countEl.textContent = count;
            }
        } catch (e) {
            console.error('Polling error:', e);
        }
    }

    setInterval(poll, 2000);
}

function escHtml(s) {
    const div = document.createElement('div');
    div.textContent = s;
    return div.innerHTML;
}

// ═══════════════════════════════════════════════════════════
//  Member Search (Members page + Renew page dropdown)
// ═══════════════════════════════════════════════════════════

function initMemberSearch() {
    const input = document.getElementById('member-search');
    const tbody = document.getElementById('members-tbody');
    if (!input || !tbody) return;

    let debounceTimer;

    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(() => doSearch(input.value), 300);
    });

    // Initial load
    doSearch('');

    async function doSearch(query) {
        try {
            const resp = await fetch(`/api/members?search=${encodeURIComponent(query)}`);
            if (resp.status === 401) { window.location.href = '/login'; return; }
            const data = await resp.json();

            tbody.innerHTML = '';

            if (!data.members || data.members.length === 0) {
                tbody.innerHTML = `<tr><td colspan="6" class="empty-state"><p>No members found</p></td></tr>`;
                return;
            }

            data.members.forEach(m => {
                const tr = document.createElement('tr');
                tr.className = 'clickable' + (m.is_expired ? ' expired' : '');
                tr.onclick = () => window.location.href = `/members/${m.id}`;
                tr.innerHTML = `
                    <td>${escHtml(m.name)}</td>
                    <td>${escHtml(m.phone)}</td>
                    <td>${m.current_plan || '—'}</td>
                    <td>${m.expiry_date ? formatDate(m.expiry_date) : '—'}</td>
                    <td>
                        <span class="badge ${m.is_expired ? 'badge-danger' : 'badge-success'}">
                            ${m.is_expired ? 'Expired' : 'Active'}
                        </span>
                    </td>
                    <td>
                        <span class="badge ${m.has_active_card ? 'badge-accent' : 'badge-warning'}">
                            ${m.has_active_card ? 'Card' : 'No Card'}
                        </span>
                    </td>
                `;
                tbody.appendChild(tr);
            });
        } catch (e) {
            console.error('Search error:', e);
        }
    }
}

// ═══════════════════════════════════════════════════════════
//  Member Search Dropdown (Renew page)
// ═══════════════════════════════════════════════════════════

function initRenewSearch() {
    const input = document.getElementById('renew-member-search');
    const dropdown = document.getElementById('renew-dropdown');
    const selectedDiv = document.getElementById('selected-member');
    const memberIdInput = document.getElementById('renew-member-id');
    const renewForm = document.getElementById('renew-form');
    if (!input) return;

    let debounceTimer;

    input.addEventListener('input', () => {
        clearTimeout(debounceTimer);
        debounceTimer = setTimeout(async () => {
            const query = input.value.trim();
            if (query.length < 2) { dropdown.classList.add('hidden'); return; }

            const resp = await fetch(`/api/members?search=${encodeURIComponent(query)}`);
            const data = await resp.json();

            dropdown.innerHTML = '';
            if (data.members && data.members.length > 0) {
                data.members.forEach(m => {
                    const div = document.createElement('div');
                    div.className = 'dropdown-item';
                    div.textContent = `${m.name} — ${m.phone}`;
                    div.onclick = () => selectMember(m);
                    dropdown.appendChild(div);
                });
                dropdown.classList.remove('hidden');
            } else {
                dropdown.classList.add('hidden');
            }
        }, 300);
    });

    function selectMember(m) {
        input.value = `${m.name} — ${m.phone}`;
        memberIdInput.value = m.id;
        dropdown.classList.add('hidden');
        selectedDiv.innerHTML = `
            <div class="detail-row"><span class="label">Name</span><span class="value">${escHtml(m.name)}</span></div>
            <div class="detail-row"><span class="label">Phone</span><span class="value">${m.phone}</span></div>
            <div class="detail-row"><span class="label">Current Plan</span><span class="value">${m.current_plan || '—'}</span></div>
            <div class="detail-row"><span class="label">Expiry</span><span class="value ${m.is_expired ? 'text-danger' : 'text-success'}">${m.expiry_date ? formatDate(m.expiry_date) : '—'}</span></div>
        `;
        selectedDiv.classList.remove('hidden');
        if (renewForm) renewForm.classList.remove('hidden');
    }

    // Close dropdown on outside click
    document.addEventListener('click', (e) => {
        if (!e.target.closest('.search-dropdown-wrapper')) {
            dropdown.classList.add('hidden');
        }
    });
}

// ═══════════════════════════════════════════════════════════
//  Register Form
// ═══════════════════════════════════════════════════════════

function initRegisterForm() {
    const form = document.getElementById('register-form');
    if (!form) return;

    // Auto-fill amount when plan changes
    const planSelect = form.querySelector('[name="plan_id"]');
    const amountInput = form.querySelector('[name="amount_paid"]');
    if (planSelect && amountInput) {
        planSelect.addEventListener('change', () => {
            const option = planSelect.selectedOptions[0];
            if (option && option.dataset.price) {
                amountInput.value = option.dataset.price;
            }
        });
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const btn = form.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Registering...';

        try {
            const formData = new FormData(form);
            const resp = await fetch('/api/members', {
                method: 'POST',
                body: formData,
            });
            const data = await resp.json();

            if (data.success) {
                window.location.href = `/assign-card/${data.member_id}`;
            } else {
                showAlert(form, data.error || 'Registration failed', 'error');
                btn.disabled = false;
                btn.textContent = 'Register Member';
            }
        } catch (err) {
            showAlert(form, 'Network error', 'error');
            btn.disabled = false;
            btn.textContent = 'Register Member';
        }
    });
}

// ═══════════════════════════════════════════════════════════
//  Renew Form
// ═══════════════════════════════════════════════════════════

function initRenewForm() {
    const form = document.getElementById('renew-submit-form');
    if (!form) return;

    const planSelect = form.querySelector('[name="plan_id"]');
    const amountInput = form.querySelector('[name="amount_paid"]');
    if (planSelect && amountInput) {
        planSelect.addEventListener('change', () => {
            const option = planSelect.selectedOptions[0];
            if (option && option.dataset.price) {
                amountInput.value = option.dataset.price;
            }
        });
    }

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const memberId = document.getElementById('renew-member-id').value;
        if (!memberId) { alert('Please select a member first'); return; }

        const btn = form.querySelector('button[type="submit"]');
        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Renewing...';

        try {
            const formData = new FormData(form);
            const resp = await fetch(`/api/members/${memberId}/renew`, {
                method: 'POST',
                body: formData,
            });
            const data = await resp.json();

            if (data.success) {
                showAlert(form.closest('.card') || form, data.message, 'success');
                btn.disabled = false;
                btn.textContent = 'Renew Membership';
            } else {
                showAlert(form, data.error || 'Renewal failed', 'error');
                btn.disabled = false;
                btn.textContent = 'Renew Membership';
            }
        } catch (err) {
            showAlert(form, 'Network error', 'error');
            btn.disabled = false;
            btn.textContent = 'Renew Membership';
        }
    });
}

// ═══════════════════════════════════════════════════════════
//  Card Assignment Polling
// ═══════════════════════════════════════════════════════════

function initCardAssignment() {
    const container = document.getElementById('assign-container');
    const startBtn = document.getElementById('start-assign-btn');
    if (!container || !startBtn) return;

    const memberId = container.dataset.memberId;
    const csrfToken = container.dataset.csrf;

    startBtn.addEventListener('click', async () => {
        startBtn.disabled = true;
        startBtn.innerHTML = '<span class="spinner"></span> Starting...';

        try {
            const formData = new FormData();
            formData.append('csrf_token', csrfToken);

            const resp = await fetch(`/api/members/${memberId}/assign-card`, {
                method: 'POST',
                body: formData,
            });
            const data = await resp.json();

            if (data.success) {
                startPolling(data.assignment_id, data.expires_in_seconds);
            } else {
                showAlert(container, data.error || 'Failed to start assignment', 'error');
                startBtn.disabled = false;
                startBtn.textContent = 'Start Assignment';
            }
        } catch (err) {
            showAlert(container, 'Network error', 'error');
            startBtn.disabled = false;
            startBtn.textContent = 'Start Assignment';
        }
    });

    function startPolling(assignmentId, ttl) {
        let remaining = ttl;

        // Show waiting UI
        container.innerHTML = `
            <div class="assign-status">
                <div class="waiting-icon">📡</div>
                <h3>Waiting for card tap...</h3>
                <p>Ask the member to tap their new card on the reader</p>
                <div class="countdown" id="countdown">${remaining}s</div>
                <p class="text-muted">Assignment expires in ${remaining} seconds</p>
            </div>
        `;

        const countdownEl = document.getElementById('countdown');

        // Countdown timer
        const countdownInterval = setInterval(() => {
            remaining--;
            if (countdownEl) countdownEl.textContent = remaining + 's';
            if (remaining <= 0) clearInterval(countdownInterval);
        }, 1000);

        // Poll every second
        const pollInterval = setInterval(async () => {
            try {
                const resp = await fetch(`/api/assign/status?assignment_id=${assignmentId}`);
                const data = await resp.json();

                if (data.status === 'done') {
                    clearInterval(pollInterval);
                    clearInterval(countdownInterval);
                    container.innerHTML = `
                        <div class="assign-status">
                            <div class="success-icon">✅</div>
                            <h3>Card Assigned Successfully!</h3>
                            <p>Card <strong>${data.card_uid || ''}</strong> linked to <strong>${escHtml(data.member_name || '')}</strong></p>
                            <a href="/members/${memberId}" class="btn btn-primary mt-2">View Profile</a>
                        </div>
                    `;
                } else if (data.status === 'expired') {
                    clearInterval(pollInterval);
                    clearInterval(countdownInterval);
                    container.innerHTML = `
                        <div class="assign-status">
                            <div class="waiting-icon" style="background: var(--danger-dim)">⏰</div>
                            <h3>Assignment Expired</h3>
                            <p>No card was tapped within the time limit</p>
                            <button class="btn btn-primary mt-2" onclick="location.reload()">Try Again</button>
                        </div>
                    `;
                }
            } catch (e) {
                console.error('Assignment poll error:', e);
            }
        }, 1000);
    }
}

// ═══════════════════════════════════════════════════════════
//  Report Lost Card
// ═══════════════════════════════════════════════════════════

function initReportLost() {
    const form = document.getElementById('report-lost-form');
    if (!form) return;

    form.addEventListener('submit', async (e) => {
        e.preventDefault();
        const memberId = form.dataset.memberId;
        const btn = form.querySelector('button[type="submit"]');

        if (!confirm('Are you sure you want to deactivate this card? This cannot be undone.')) return;

        btn.disabled = true;
        btn.innerHTML = '<span class="spinner"></span> Deactivating...';

        try {
            const formData = new FormData(form);
            const resp = await fetch(`/api/members/${memberId}/report-lost`, {
                method: 'POST',
                body: formData,
            });
            const data = await resp.json();

            if (data.success) {
                showAlert(form, data.message, 'success');
                setTimeout(() => {
                    window.location.href = `/assign-card/${memberId}`;
                }, 1500);
            } else {
                showAlert(form, data.error || 'Failed', 'error');
                btn.disabled = false;
                btn.textContent = 'Report Lost & Deactivate';
            }
        } catch (err) {
            showAlert(form, 'Network error', 'error');
            btn.disabled = false;
            btn.textContent = 'Report Lost & Deactivate';
        }
    });
}

// ═══════════════════════════════════════════════════════════
//  Init on page load
// ═══════════════════════════════════════════════════════════

document.addEventListener('DOMContentLoaded', () => {
    initAttendancePolling();
    initMemberSearch();
    initRenewSearch();
    initRegisterForm();
    initRenewForm();
    initCardAssignment();
    initReportLost();
});
