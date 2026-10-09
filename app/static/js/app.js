// CertifyPro Master Frontend Application Logic

let currentBatchId = null;
let currentBatchParticipants = [];
let allEvents = [];
let allTemplates = [];
let selectedParticipantIds = new Set();
let activeFilter = 'ALL';

document.addEventListener('DOMContentLoaded', () => {
    initApp();
});

async function initApp() {
    setupDragAndDrop();
    await loadDashboardStats();
    await loadEvents();
    await loadTemplates();
    await loadEmailLogs();
}

// Tab Switching
function switchTab(tab) {
    const tabs = ['dashboard', 'events', 'upload', 'review', 'generation', 'emails'];
    tabs.forEach(t => {
        const sec = document.getElementById(`section-${t}`);
        const btn = document.getElementById(`tab-btn-${t}`);
        if (sec) sec.classList.toggle('hidden', t !== tab);
        if (btn) {
            if (t === tab) {
                btn.className = "nav-tab px-3 py-2 rounded-lg text-emerald-400 bg-slate-800/80 transition-all font-bold";
            } else {
                btn.className = "nav-tab px-3 py-2 rounded-lg text-slate-300 hover:text-white hover:bg-slate-800 transition-all";
            }
        }
    });

    if (tab === 'dashboard') loadDashboardStats();
    if (tab === 'events') loadEvents();
    if (tab === 'emails') loadEmailLogs();
}

// Dashboard Statistics
async function loadDashboardStats() {
    try {
        const res = await fetch('/api/dashboard/stats');
        const data = await res.json();
        
        document.getElementById('stat-events').textContent = data.events_count;
        document.getElementById('stat-certs').textContent = data.certificates_count;
        document.getElementById('stat-autofixed').textContent = data.auto_fixed_count;
        document.getElementById('stat-verifications').textContent = data.verifications_count;
        document.getElementById('stat-dups').textContent = `${data.duplicates_caught} intercepted`;

        renderRecentCertsList(data.recent_certificates);
    } catch (err) {
        console.error("Failed to load dashboard stats:", err);
    }
}

function renderRecentCertsList(certs) {
    const container = document.getElementById('recent-certs-list');
    if (!certs || certs.length === 0) {
        container.innerHTML = `<p class="text-xs text-slate-400 italic py-4 text-center">No certificates generated yet. Upload a batch to get started!</p>`;
        return;
    }

    container.innerHTML = certs.map(c => `
        <div class="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-200 hover:bg-slate-100/80 transition-all">
            <div class="flex items-center space-x-3">
                <div class="w-9 h-9 rounded-lg bg-emerald-100 text-emerald-700 flex items-center justify-center font-bold text-xs">
                    <i class="fa-solid fa-file-shield"></i>
                </div>
                <div>
                    <h4 class="text-xs font-bold text-slate-800">${escapeHtml(c.participant_name)}</h4>
                    <p class="text-[11px] text-slate-500 font-mono">${escapeHtml(c.id)} &bull; ${escapeHtml(c.role || 'Participant')}</p>
                </div>
            </div>
            <div class="flex items-center space-x-2">
                <button onclick="openCertPreview('${c.id}')" class="px-2.5 py-1 text-xs bg-white hover:bg-slate-200 border border-slate-300 text-slate-700 rounded-lg font-medium transition-all">
                    <i class="fa-solid fa-eye mr-1 text-emerald-600"></i> Preview
                </button>
                <a href="/verify/${c.id}" target="_blank" class="px-2.5 py-1 text-xs bg-emerald-50 hover:bg-emerald-100 border border-emerald-200 text-emerald-700 rounded-lg font-medium transition-all">
                    <i class="fa-solid fa-shield mr-1"></i> Verify
                </a>
            </div>
        </div>
    `).join('');
}

// Events & Templates
async function loadEvents() {
    try {
        const res = await fetch('/api/events');
        allEvents = await res.json();
        
        // Populate Upload dropdown
        const uploadSelect = document.getElementById('upload-event-select');
        if (uploadSelect) {
            uploadSelect.innerHTML = allEvents.map(e => `
                <option value="${e.id}">${escapeHtml(e.name)} (${escapeHtml(e.category)})</option>
            `).join('');
        }

        // Populate Events Grid
        const grid = document.getElementById('events-grid');
        grid.innerHTML = allEvents.map(e => {
            const currentTpl = allTemplates.find(t => t.id === e.template_id) || { name: e.template_id || 'Modern Tech', accent_color: '#0284c7' };
            return `
            <div class="glass-card rounded-2xl p-5 border border-slate-200 shadow-sm hover:shadow-md transition-all flex flex-col justify-between">
                <div>
                    <div class="flex items-center justify-between mb-2">
                        <span class="px-2.5 py-0.5 rounded-full text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-700 border border-slate-200">
                            ${escapeHtml(e.category)}
                        </span>
                        <span class="text-xs text-slate-400"><i class="fa-solid fa-calendar mr-1"></i> ${escapeHtml(e.event_date)}</span>
                    </div>
                    <h3 class="text-base font-bold text-slate-900 mt-1">${escapeHtml(e.name)}</h3>
                    <p class="text-xs text-slate-500 mt-0.5 font-medium">${escapeHtml(e.organization)}</p>

                    <!-- Active Template Indicator -->
                    <div class="mt-3 py-1.5 px-3 rounded-xl bg-slate-50 border border-slate-200 flex items-center justify-between text-xs">
                        <span class="text-slate-500 font-semibold text-[11px]">Active Template:</span>
                        <span class="font-bold text-slate-800 flex items-center text-[11px]">
                            <span class="w-2.5 h-2.5 rounded-full mr-1.5 inline-block" style="background-color: ${currentTpl.accent_color}"></span>
                            ${escapeHtml(currentTpl.name)}
                        </span>
                    </div>

                    <p class="text-xs text-slate-600 mt-2.5 line-clamp-2">${escapeHtml(e.description || 'No description.')}</p>

                    <div class="mt-3 pt-2.5 border-t border-slate-100 space-y-1 text-[11px] text-slate-500">
                        <div class="flex justify-between">
                            <span>Signatory 1:</span>
                            <strong class="text-slate-700">${escapeHtml(e.signatory1_name)}</strong>
                        </div>
                        <div class="flex justify-between">
                            <span>Signatory 2:</span>
                            <strong class="text-slate-700">${escapeHtml(e.signatory2_name)}</strong>
                        </div>
                    </div>
                </div>

                <div class="mt-5 pt-3 border-t border-slate-100 flex flex-wrap items-center justify-between gap-2">
                    <span class="text-xs font-semibold text-emerald-600">
                        <i class="fa-solid fa-award mr-1"></i> ${e.cert_count || 0} Issued
                    </span>
                    <div class="flex items-center space-x-1.5">
                        <button onclick="openChangeTemplateModal(${e.id})" class="px-2.5 py-1.5 rounded-lg bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 font-bold text-xs transition-all flex items-center space-x-1" title="Change design template for this event">
                            <i class="fa-solid fa-palette text-indigo-500"></i>
                            <span>Change Template</span>
                        </button>
                        <button onclick="openEditEventModal(${e.id})" class="px-2.5 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 border border-slate-300 font-bold text-xs transition-all flex items-center space-x-1" title="Edit event details">
                            <i class="fa-solid fa-pen"></i>
                            <span>Edit</span>
                        </button>
                        <button onclick="prepareUploadForEvent(${e.id})" class="px-2.5 py-1.5 rounded-lg bg-emerald-50 hover:bg-emerald-100 text-emerald-700 border border-emerald-200 font-bold text-xs transition-all flex items-center space-x-1" title="Upload participants">
                            <i class="fa-solid fa-cloud-arrow-up"></i>
                            <span>Upload</span>
                        </button>
                    </div>
                </div>
            </div>
            `;
        }).join('');

        // Populate batches dropdown in review and gen
        await loadBatchesDropdown();

    } catch (err) {
        console.error("Failed to load events:", err);
    }
}

function prepareUploadForEvent(eventId) {
    document.getElementById('upload-event-select').value = eventId;
    switchTab('upload');
}

async function loadTemplates() {
    try {
        const res = await fetch('/api/templates');
        allTemplates = await res.json();
        
        // Populate Template selector in Bulk Generation tab
        const genTplSelect = document.getElementById('gen-template-select');
        if (genTplSelect) {
            genTplSelect.innerHTML = allTemplates.map(t => `
                <option value="${t.id}">${escapeHtml(t.name)} (${escapeHtml(t.category)})</option>
            `).join('');
        }

        // Populate Template selector in Edit Event modal
        const editEvTpl = document.getElementById('edit-ev-template');
        if (editEvTpl) {
            editEvTpl.innerHTML = allTemplates.map(t => `
                <option value="${t.id}">${escapeHtml(t.name)} (${escapeHtml(t.category)})</option>
            `).join('');
        }

        const grid = document.getElementById('templates-grid');
        grid.innerHTML = allTemplates.map(t => `
            <div class="p-4 rounded-xl border border-slate-200 bg-white shadow-xs hover:border-emerald-400 transition-all flex flex-col justify-between">
                <div>
                    <div class="h-24 rounded-lg flex items-center justify-center p-2 mb-3 relative overflow-hidden" style="background-color: ${t.primary_color};">
                        <div class="absolute inset-2 border border-dashed rounded opacity-40" style="border-color: ${t.accent_color};"></div>
                        <span class="text-[10px] font-bold tracking-widest uppercase text-white z-10 text-center px-1">${escapeHtml(t.badge_text)}</span>
                    </div>
                    <h4 class="text-xs font-bold text-slate-800">${escapeHtml(t.name)}</h4>
                    <p class="text-[11px] text-slate-500 mt-1 line-clamp-2">${escapeHtml(t.description)}</p>
                </div>
                <div class="mt-4 pt-2.5 border-t border-slate-100 space-y-2">
                    <div class="flex items-center justify-between text-[10px] font-semibold text-slate-400">
                        <span>${escapeHtml(t.category)}</span>
                        <span class="flex items-center"><span class="w-2.5 h-2.5 rounded-full mr-1 inline-block" style="background-color: ${t.accent_color}"></span> Theme</span>
                    </div>
                    <div class="flex items-center justify-between gap-1.5 pt-1">
                        <button onclick="previewTemplateImage('${t.id}', '${escapeHtml(t.name)}')" class="flex-1 py-1 px-2 text-center text-[11px] bg-slate-100 hover:bg-slate-200 rounded-lg font-bold text-slate-700 transition-all">
                            <i class="fa-solid fa-eye mr-1 text-slate-500"></i> Preview
                        </button>
                        <button onclick="promptApplyTemplateToEvent('${t.id}')" class="flex-1 py-1 px-2 text-center text-[11px] bg-indigo-50 hover:bg-indigo-100 text-indigo-700 border border-indigo-200 rounded-lg font-bold transition-all">
                            <i class="fa-solid fa-check mr-1"></i> Apply
                        </button>
                    </div>
                </div>
            </div>
        `).join('');

    } catch (err) {
        console.error("Failed to load templates:", err);
    }
}

// Drag & Drop CSV Uploader
function setupDragAndDrop() {
    const dropZone = document.getElementById('drop-zone');
    const fileInput = document.getElementById('csv-file-input');
    const analyzeBtn = document.getElementById('btn-upload-analyze');
    const fileNameBadge = document.getElementById('file-chosen-name');

    ['dragenter', 'dragover'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.add('border-emerald-500', 'bg-emerald-50/50');
        });
    });

    ['dragleave', 'drop'].forEach(eventName => {
        dropZone.addEventListener(eventName, (e) => {
            e.preventDefault();
            e.stopPropagation();
            dropZone.classList.remove('border-emerald-500', 'bg-emerald-50/50');
        });
    });

    dropZone.addEventListener('drop', (e) => {
        const dt = e.dataTransfer;
        const files = dt.files;
        if (files.length > 0) {
            fileInput.files = files;
            updateFileSelectedUI(files[0].name);
        }
    });

    fileInput.addEventListener('change', () => {
        if (fileInput.files.length > 0) {
            updateFileSelectedUI(fileInput.files[0].name);
        }
    });

    function updateFileSelectedUI(name) {
        fileNameBadge.textContent = `Selected: ${name}`;
        fileNameBadge.classList.remove('hidden');
        analyzeBtn.disabled = false;
        analyzeBtn.className = "px-6 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-sm transition-all flex items-center space-x-2 shadow-md cursor-pointer";
    }
}

async function handleCsvUpload() {
    const fileInput = document.getElementById('csv-file-input');
    const eventId = document.getElementById('upload-event-select').value;
    const analyzeBtn = document.getElementById('btn-upload-analyze');

    if (!fileInput.files.length) {
        alert("Please select a CSV file first.");
        return;
    }

    const file = fileInput.files[0];
    const formData = new FormData();
    formData.append('file', file);

    analyzeBtn.disabled = true;
    analyzeBtn.innerHTML = `<i class="fa-solid fa-circle-notch fa-spin"></i><span>Analyzing & Sanitizing via AI...</span>`;

    try {
        const res = await fetch(`/api/events/${eventId}/upload-csv`, {
            method: 'POST',
            body: formData
        });

        const data = await res.json();
        if (!res.ok) {
            throw new Error(data.detail || "Upload failed");
        }

        // Show AI hygiene analysis result card
        const card = document.getElementById('upload-result-card');
        document.getElementById('res-total').textContent = data.summary.total;
        document.getElementById('res-clean').textContent = data.summary.clean;
        document.getElementById('res-fixed').textContent = data.summary.auto_fixed;
        document.getElementById('res-flagged').textContent = data.summary.flagged;
        document.getElementById('res-dups').textContent = data.summary.duplicates;
        card.classList.remove('hidden');

        // Update current batch and refresh dropdowns
        currentBatchId = data.batch.id;
        await loadBatchesDropdown();
        await loadBatchForReview(currentBatchId);

        // Update nav badge
        const badge = document.getElementById('nav-review-badge');
        badge.textContent = data.summary.flagged + data.summary.duplicates;
        if (data.summary.flagged + data.summary.duplicates > 0) badge.classList.remove('hidden');

    } catch (err) {
        alert(`Error uploading CSV: ${err.message}`);
    } finally {
        analyzeBtn.disabled = false;
        analyzeBtn.innerHTML = `<i class="fa-solid fa-wand-magic-sparkles"></i><span>Upload & Run AI Data Cleaning</span>`;
    }
}

// Batches Dropdown Loader
async function loadBatchesDropdown() {
    const reviewSelect = document.getElementById('review-batch-select');
    const genSelect = document.getElementById('gen-batch-select');

    // Retrieve batches for all events
    let allBatches = [];
    for (const evt of allEvents) {
        try {
            const res = await fetch(`/api/events/${evt.id}`);
            const d = await res.json();
            if (d.batches) {
                d.batches.forEach(b => {
                    b.event_name = evt.name;
                    allBatches.push(b);
                });
            }
        } catch (e) {}
    }

    if (allBatches.length > 0) {
        const optionsHtml = allBatches.map(b => `
            <option value="${b.id}" ${b.id === currentBatchId ? 'selected' : ''}>
                Batch #${b.id}: ${escapeHtml(b.filename)} (${escapeHtml(b.event_name)}) [${b.total_records} rows]
            </option>
        `).join('');

        if (reviewSelect) reviewSelect.innerHTML = optionsHtml;
        if (genSelect) genSelect.innerHTML = optionsHtml;

        if (!currentBatchId) {
            currentBatchId = allBatches[0].id;
        }
        await updateGenBatchDetails(currentBatchId);
    } else {
        if (reviewSelect) reviewSelect.innerHTML = `<option value="">No batches yet</option>`;
        if (genSelect) genSelect.innerHTML = `<option value="">No batches yet</option>`;
    }
}

// Human Review & Audit Workspace
async function loadBatchForReview(batchId) {
    if (!batchId) return;
    currentBatchId = parseInt(batchId);
    selectedParticipantIds.clear();
    document.getElementById('check-all').checked = false;

    try {
        const res = await fetch(`/api/batches/${batchId}/participants`);
        const data = await res.json();
        currentBatchParticipants = data.participants;
        renderReviewTable();
        await updateGenBatchDetails(batchId);
    } catch (err) {
        console.error("Failed to load batch participants:", err);
    }
}

function filterReviewTable(filter) {
    activeFilter = filter;
    ['all', 'clean', 'autofixed', 'flagged', 'duplicate'].forEach(f => {
        const btn = document.getElementById(`filter-btn-${f}`);
        if (btn) {
            if (f.toUpperCase() === filter.replace('_', '')) {
                btn.className = "filter-btn px-3 py-1.5 rounded-lg bg-slate-800 text-white font-bold";
            } else {
                btn.className = "filter-btn px-3 py-1.5 rounded-lg bg-slate-100 text-slate-600 hover:bg-slate-200";
            }
        }
    });
    renderReviewTable();
}

function renderReviewTable() {
    const tbody = document.getElementById('review-table-body');
    const filtered = currentBatchParticipants.filter(p => {
        if (activeFilter === 'ALL') return true;
        return p.validation_status === activeFilter;
    });

    if (filtered.length === 0) {
        tbody.innerHTML = `<tr><td colspan="9" class="p-8 text-center text-slate-400 italic">No records match the active filter (${activeFilter}).</td></tr>`;
        return;
    }

    tbody.innerHTML = filtered.map(p => {
        // Status Badge
        let statusBadge = '';
        if (p.validation_status === 'CLEAN') {
            statusBadge = `<span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[10px]"><i class="fa-solid fa-check mr-1"></i>Clean</span>`;
        } else if (p.validation_status === 'AUTO_FIXED') {
            statusBadge = `<span class="px-2 py-0.5 rounded-full bg-purple-100 text-purple-800 font-bold text-[10px]"><i class="fa-solid fa-wand-magic-sparkles mr-1"></i>Auto-Fixed</span>`;
        } else if (p.validation_status === 'FLAGGED') {
            statusBadge = `<span class="px-2 py-0.5 rounded-full bg-amber-100 text-amber-800 font-bold text-[10px]"><i class="fa-solid fa-triangle-exclamation mr-1"></i>Flagged</span>`;
        } else if (p.validation_status === 'DUPLICATE') {
            statusBadge = `<span class="px-2 py-0.5 rounded-full bg-red-100 text-red-800 font-bold text-[10px]"><i class="fa-solid fa-copy mr-1"></i>Duplicate</span>`;
        }

        // Issues tags
        let issuesHtml = '';
        if (p.validation_issues && p.validation_issues.length > 0) {
            issuesHtml = p.validation_issues.map(iss => {
                let badgeClass = 'bg-slate-100 text-slate-600';
                if (iss.type === 'fix') badgeClass = 'bg-purple-50 text-purple-700 border border-purple-200';
                if (iss.type === 'warning') badgeClass = 'bg-amber-50 text-amber-700 border border-amber-200';
                if (iss.type === 'error' || iss.type === 'duplicate') badgeClass = 'bg-red-50 text-red-700 border border-red-200';
                return `<span class="inline-block px-1.5 py-0.5 rounded text-[10px] font-medium mr-1 mb-1 ${badgeClass}">${escapeHtml(iss.message)}</span>`;
            }).join('');
        } else {
            issuesHtml = `<span class="text-slate-400 text-[11px]">&mdash;</span>`;
        }

        const isChecked = selectedParticipantIds.has(p.id);

        return `
            <tr class="hover:bg-slate-50/80 transition-colors ${p.validation_status === 'DUPLICATE' ? 'bg-red-50/20' : ''}">
                <td class="p-3">
                    <input type="checkbox" onchange="toggleSelectRow(${p.id}, this.checked)" ${isChecked ? 'checked' : ''} class="rounded">
                </td>
                <td class="p-3 whitespace-nowrap">${statusBadge}</td>
                <td class="p-3">
                    <strong class="text-slate-900 block font-semibold">${escapeHtml(p.clean_name)}</strong>
                    ${p.original_name !== p.clean_name ? `<span class="text-[10px] text-slate-400 line-through">Raw: ${escapeHtml(p.original_name)}</span>` : ''}
                </td>
                <td class="p-3 text-slate-600 font-mono text-[11px]">${escapeHtml(p.clean_email || 'N/A')}</td>
                <td class="p-3">
                    <span class="block text-slate-800 font-medium">${escapeHtml(p.department || 'General')}</span>
                    <span class="text-[10px] text-slate-500">${escapeHtml(p.college || '')}</span>
                </td>
                <td class="p-3 font-mono text-slate-600">${escapeHtml(p.roll_number || 'N/A')}</td>
                <td class="p-3">
                    <span class="inline-block px-2 py-0.5 rounded bg-slate-100 text-slate-700 font-medium text-[11px]">${escapeHtml(p.role)}</span>
                </td>
                <td class="p-3 max-w-xs">${issuesHtml}</td>
                <td class="p-3 text-right whitespace-nowrap space-x-1">
                    <button onclick="openEditModal(${p.id})" class="px-2 py-1 text-slate-600 hover:text-purple-600 hover:bg-purple-50 rounded font-bold text-xs" title="Edit row">
                        <i class="fa-solid fa-pen-to-square"></i>
                    </button>
                    ${p.is_approved ? 
                        `<span class="text-emerald-600 font-bold text-xs" title="Approved"><i class="fa-solid fa-circle-check"></i></span>` : 
                        `<span class="text-slate-300 text-xs" title="Not Approved"><i class="fa-solid fa-circle"></i></span>`
                    }
                </td>
            </tr>
        `;
    }).join('');
}

function toggleSelectRow(id, checked) {
    if (checked) selectedParticipantIds.add(id);
    else selectedParticipantIds.delete(id);
}

function toggleSelectAll(checked) {
    currentBatchParticipants.forEach(p => {
        if (checked) selectedParticipantIds.add(p.id);
        else selectedParticipantIds.delete(p.id);
    });
    renderReviewTable();
}

async function bulkApprove(approveState) {
    if (selectedParticipantIds.size === 0) {
        alert("Please select one or more participants first.");
        return;
    }

    try {
        await fetch(`/api/batches/${currentBatchId}/bulk-action`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                participant_ids: Array.from(selectedParticipantIds),
                action: approveState ? 'approve' : 'reject'
            })
        });
        await loadBatchForReview(currentBatchId);
    } catch (err) {
        alert("Bulk action failed.");
    }
}

async function applyAllAIFixes() {
    if (!currentBatchId) return;
    try {
        const res = await fetch(`/api/batches/${currentBatchId}/apply-all-fixes`, { method: 'POST' });
        const data = await res.json();
        alert(data.message);
        await loadBatchForReview(currentBatchId);
    } catch (err) {
        alert("Failed to apply all fixes.");
    }
}

// Inline Edit Modal
function openEditModal(participantId) {
    const p = currentBatchParticipants.find(x => x.id === participantId);
    if (!p) return;

    document.getElementById('edit-id').value = p.id;
    document.getElementById('edit-name').value = p.clean_name;
    document.getElementById('edit-email').value = p.clean_email || '';
    document.getElementById('edit-dept').value = p.department || '';
    document.getElementById('edit-roll').value = p.roll_number || '';
    document.getElementById('edit-college').value = p.college || '';
    document.getElementById('edit-role').value = p.role || 'Participant';
    document.getElementById('edit-approved').checked = Boolean(p.is_approved);

    document.getElementById('modal-edit-participant').classList.remove('hidden');
}

function closeEditModal() {
    document.getElementById('modal-edit-participant').classList.add('hidden');
}

async function submitEditParticipant(e) {
    e.preventDefault();
    const id = document.getElementById('edit-id').value;
    const payload = {
        clean_name: document.getElementById('edit-name').value,
        clean_email: document.getElementById('edit-email').value,
        department: document.getElementById('edit-dept').value,
        roll_number: document.getElementById('edit-roll').value,
        college: document.getElementById('edit-college').value,
        role: document.getElementById('edit-role').value,
        is_approved: document.getElementById('edit-approved').checked ? 1 : 0
    };

    try {
        const res = await fetch(`/api/participants/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            closeEditModal();
            await loadBatchForReview(currentBatchId);
        }
    } catch (err) {
        alert("Failed to update participant record.");
    }
}

// Bulk Generation Engine
async function updateGenBatchDetails(batchId) {
    if (!batchId) return;
    try {
        const res = await fetch(`/api/batches/${batchId}/participants`);
        const data = await res.json();
        const approvedCount = data.participants.filter(p => p.is_approved && !p.certificate_id).length;
        document.getElementById('gen-approved-count').textContent = `${approvedCount} Ready to Generate`;

        // Match template dropdown with the event's template
        if (data.batch && data.batch.event_id) {
            const evt = allEvents.find(e => e.id === data.batch.event_id);
            const genTplSelect = document.getElementById('gen-template-select');
            if (evt && genTplSelect) {
                genTplSelect.value = evt.template_id;
            }
        }

        // Check if batch has generated certificates
        const hasGenerated = data.participants.some(p => Boolean(p.certificate_id));
        const zipBtn = document.getElementById('btn-download-zip');
        if (hasGenerated) {
            zipBtn.href = `/api/batches/${batchId}/download-zip`;
            zipBtn.classList.remove('hidden');
        } else {
            zipBtn.classList.add('hidden');
        }

        renderGeneratedGallery(data.participants.filter(p => Boolean(p.certificate_id)));
    } catch (err) {}
}

async function startGeneration() {
    if (!currentBatchId) {
        alert("Please select a batch first.");
        return;
    }

    const startBtn = document.getElementById('btn-start-generation');
    const progressContainer = document.getElementById('gen-progress-container');
    const progressBar = document.getElementById('gen-progress-bar');
    const progressStatus = document.getElementById('gen-progress-status');
    const chosenTemplate = document.getElementById('gen-template-select') ? document.getElementById('gen-template-select').value : null;

    startBtn.disabled = true;
    progressContainer.classList.remove('hidden');
    progressBar.style.width = '30%';

    try {
        let url = `/api/batches/${currentBatchId}/generate`;
        if (chosenTemplate) {
            url += `?template_id=${encodeURIComponent(chosenTemplate)}`;
        }
        const res = await fetch(url, { method: 'POST' });
        const data = await res.json();
        progressBar.style.width = '100%';
        progressStatus.innerHTML = `<i class="fa-solid fa-circle-check text-emerald-400 mr-2"></i> ${data.message}`;

        setTimeout(async () => {
            progressContainer.classList.add('hidden');
            startBtn.disabled = false;
            await loadBatchForReview(currentBatchId);
            await loadDashboardStats();
            await loadEvents();
        }, 1200);

    } catch (err) {
        alert("Generation encountered an error.");
        startBtn.disabled = false;
        progressContainer.classList.add('hidden');
    }
}

// Template Switching & Customizer Modals
function openChangeTemplateModal(eventId) {
    const evt = allEvents.find(e => e.id === eventId);
    if (!evt) return;

    document.getElementById('change-tpl-event-id').value = eventId;
    document.getElementById('modal-change-tpl-subtitle').textContent = `For event: ${evt.name}`;

    const container = document.getElementById('template-options-cards');
    container.innerHTML = allTemplates.map(t => {
        const isCurrent = (t.id === evt.template_id);
        return `
        <div class="p-4 rounded-xl border-2 ${isCurrent ? 'border-emerald-500 bg-emerald-50/20' : 'border-slate-200 bg-white hover:border-slate-300'} transition-all flex flex-col justify-between">
            <div>
                <div class="flex items-center justify-between mb-2">
                    <span class="px-2 py-0.5 rounded text-[10px] font-bold uppercase tracking-wider bg-slate-100 text-slate-700">
                        ${escapeHtml(t.category)}
                    </span>
                    ${isCurrent ? '<span class="text-xs font-bold text-emerald-600 flex items-center"><i class="fa-solid fa-circle-check mr-1"></i> CURRENT ACTIVE</span>' : ''}
                </div>
                
                <!-- Preview Thumbnail Card -->
                <div class="relative h-28 rounded-lg overflow-hidden border border-slate-200 mb-3 group cursor-pointer" onclick="previewTemplateImage('${t.id}', '${escapeHtml(t.name)}')">
                    <img src="/api/templates/${t.id}/preview" alt="${escapeHtml(t.name)}" class="w-full h-full object-cover">
                    <div class="absolute inset-0 bg-slate-950/40 opacity-0 group-hover:opacity-100 transition-opacity flex items-center justify-center text-white text-xs font-bold space-x-1">
                        <i class="fa-solid fa-magnifying-glass-plus"></i>
                        <span>Inspect Design</span>
                    </div>
                </div>

                <h4 class="text-sm font-bold text-slate-900">${escapeHtml(t.name)}</h4>
                <p class="text-xs text-slate-500 mt-1 line-clamp-2">${escapeHtml(t.description)}</p>
            </div>

            <div class="mt-4 pt-3 border-t border-slate-100 flex items-center justify-between gap-2">
                <button type="button" onclick="previewTemplateImage('${t.id}', '${escapeHtml(t.name)}')" class="px-3 py-1.5 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-700 font-bold text-xs flex items-center">
                    <i class="fa-solid fa-eye mr-1"></i> Preview
                </button>
                <button type="button" onclick="selectTemplateForEvent(${eventId}, '${t.id}')" class="px-4 py-1.5 rounded-lg ${isCurrent ? 'bg-slate-200 text-slate-500 cursor-default' : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-sm'} font-bold text-xs flex items-center">
                    <i class="fa-solid fa-check mr-1"></i> ${isCurrent ? 'Selected' : 'Use This Template'}
                </button>
            </div>
        </div>
        `;
    }).join('');

    document.getElementById('modal-change-template').classList.remove('hidden');
}

function closeChangeTemplateModal() {
    document.getElementById('modal-change-template').classList.add('hidden');
}

async function selectTemplateForEvent(eventId, templateId) {
    try {
        const res = await fetch(`/api/events/${eventId}/change-template`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ template_id: templateId })
        });
        const data = await res.json();
        if (res.ok) {
            closeChangeTemplateModal();
            await loadEvents();
            if (currentBatchId) await updateGenBatchDetails(currentBatchId);
            alert(`Template updated successfully! Future certificates for this event will use '${data.template.name}'.`);
        } else {
            alert(data.detail || "Failed to update template.");
        }
    } catch (err) {
        alert("Error changing template.");
    }
}

function promptApplyTemplateToEvent(templateId) {
    if (!allEvents.length) {
        alert("No events available to apply to.");
        return;
    }
    const eventNames = allEvents.map((e, idx) => `${idx + 1}. ${e.name}`).join('\n');
    const input = prompt(`Which event would you like to apply this template to?\n\nEnter number (1-${allEvents.length}):\n${eventNames}`, "1");
    if (input) {
        const idx = parseInt(input) - 1;
        if (idx >= 0 && idx < allEvents.length) {
            selectTemplateForEvent(allEvents[idx].id, templateId);
        }
    }
}

function previewCurrentGenTemplate() {
    const sel = document.getElementById('gen-template-select');
    if (!sel) return;
    const tplId = sel.value;
    const tpl = allTemplates.find(t => t.id === tplId);
    previewTemplateImage(tplId, tpl ? tpl.name : tplId);
}

function previewTemplateImage(templateId, templateName) {
    document.getElementById('modal-preview-title').textContent = `Template Preview: ${templateName}`;
    document.getElementById('modal-preview-img').src = `/api/templates/${templateId}/preview`;
    document.getElementById('modal-preview-hash').textContent = `Template ID: ${templateId}`;
    document.getElementById('modal-preview-download-png').href = `/api/templates/${templateId}/preview`;
    
    // Hide pdf & verify buttons for preview
    const pdfBtn = document.getElementById('modal-preview-download-pdf');
    const verifyBtn = document.getElementById('modal-preview-verify-btn');
    if (pdfBtn) pdfBtn.style.display = 'none';
    if (verifyBtn) verifyBtn.style.display = 'none';

    document.getElementById('modal-cert-preview').classList.remove('hidden');
}

// Edit Event Details Modal
function openEditEventModal(eventId) {
    const evt = allEvents.find(e => e.id === eventId);
    if (!evt) return;

    document.getElementById('edit-ev-id').value = evt.id;
    document.getElementById('edit-ev-name').value = evt.name;
    document.getElementById('edit-ev-org').value = evt.organization;
    document.getElementById('edit-ev-date').value = evt.event_date;
    document.getElementById('edit-ev-cat').value = evt.category;
    document.getElementById('edit-ev-template').value = evt.template_id;
    document.getElementById('edit-ev-cite').value = evt.citation_text || '';
    document.getElementById('edit-ev-sig1-name').value = evt.signatory1_name;
    document.getElementById('edit-ev-sig1-title').value = evt.signatory1_title;
    document.getElementById('edit-ev-sig2-name').value = evt.signatory2_name;
    document.getElementById('edit-ev-sig2-title').value = evt.signatory2_title;

    document.getElementById('modal-edit-event').classList.remove('hidden');
}

function closeEditEventModal() {
    document.getElementById('modal-edit-event').classList.add('hidden');
}

async function submitEditEvent(e) {
    e.preventDefault();
    const id = document.getElementById('edit-ev-id').value;
    const payload = {
        name: document.getElementById('edit-ev-name').value,
        organization: document.getElementById('edit-ev-org').value,
        event_date: document.getElementById('edit-ev-date').value,
        category: document.getElementById('edit-ev-cat').value,
        template_id: document.getElementById('edit-ev-template').value,
        citation_text: document.getElementById('edit-ev-cite').value,
        signatory1_name: document.getElementById('edit-ev-sig1-name').value,
        signatory1_title: document.getElementById('edit-ev-sig1-title').value,
        signatory2_name: document.getElementById('edit-ev-sig2-name').value,
        signatory2_title: document.getElementById('edit-ev-sig2-title').value,
    };

    try {
        const res = await fetch(`/api/events/${id}`, {
            method: 'PUT',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            closeEditEventModal();
            await loadEvents();
            await loadDashboardStats();
            if (currentBatchId) await updateGenBatchDetails(currentBatchId);
            alert("Event and certificate template details updated successfully!");
        } else {
            alert("Failed to update event.");
        }
    } catch (err) {
        alert("Error saving event updates.");
    }
}

function renderGeneratedGallery(certs) {
    const grid = document.getElementById('generated-certs-grid');
    document.getElementById('gen-gallery-count').textContent = `${certs.length} certificates issued`;

    if (!certs || certs.length === 0) {
        grid.innerHTML = `<div class="col-span-3 text-center py-8 text-slate-400 italic">No certificates generated for this batch yet. Click 'Generate Certificates in Bulk' above.</div>`;
        return;
    }

    grid.innerHTML = certs.map(p => `
        <div class="glass-card rounded-xl border border-slate-200 overflow-hidden shadow-xs hover:shadow-md transition-all flex flex-col justify-between">
            <div class="relative bg-slate-900 group cursor-pointer" onclick="openCertPreview('${p.certificate_id}')">
                <img src="/certificates-files/${p.certificate_id}.png" alt="Certificate" class="w-full h-44 object-cover opacity-90 group-hover:opacity-100 transition-opacity">
                <div class="absolute inset-0 bg-slate-950/40 opacity-0 group-hover:opacity-100 flex items-center justify-center transition-opacity text-white text-xs font-bold space-x-1">
                    <i class="fa-solid fa-magnifying-glass-plus"></i>
                    <span>Click to Inspect Full Size</span>
                </div>
            </div>
            <div class="p-4 space-y-2">
                <div class="flex items-center justify-between">
                    <span class="font-mono text-[10px] font-bold text-slate-400 uppercase tracking-wider">${escapeHtml(p.certificate_id)}</span>
                    <span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">Active</span>
                </div>
                <h4 class="text-sm font-bold text-slate-900">${escapeHtml(p.clean_name)}</h4>
                <p class="text-xs text-slate-500 line-clamp-1">${escapeHtml(p.department || 'General')} &bull; ${escapeHtml(p.role)}</p>

                <div class="pt-3 border-t border-slate-100 flex items-center justify-between gap-1 text-xs">
                    <a href="/api/certificates/${p.certificate_id}/download/pdf" download class="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] flex items-center">
                        <i class="fa-solid fa-file-pdf mr-1 text-red-600"></i> PDF
                    </a>
                    <a href="/api/certificates/${p.certificate_id}/download/png" download class="px-2.5 py-1 rounded bg-slate-100 hover:bg-slate-200 text-slate-700 font-semibold text-[11px] flex items-center">
                        <i class="fa-solid fa-file-image mr-1 text-blue-600"></i> PNG
                    </a>
                    <button onclick="dispatchEmail('${p.certificate_id}')" class="px-2.5 py-1 rounded bg-purple-50 hover:bg-purple-100 text-purple-700 font-semibold text-[11px] flex items-center">
                        <i class="fa-solid fa-paper-plane mr-1"></i> Email
                    </button>
                    <a href="/verify/${p.certificate_id}" target="_blank" class="px-2.5 py-1 rounded bg-emerald-50 hover:bg-emerald-100 text-emerald-700 font-semibold text-[11px] flex items-center" title="Public Verification">
                        <i class="fa-solid fa-qrcode mr-1"></i> QR
                    </a>
                </div>
            </div>
        </div>
    `).join('');
}

// Certificate Full Size Preview Modal
async function openCertPreview(certId) {
    try {
        const res = await fetch(`/api/certificates/${certId}`);
        const cert = await res.json();

        document.getElementById('modal-preview-title').textContent = `Certificate: ${cert.participant_name} (${cert.id})`;
        document.getElementById('modal-preview-img').src = `/certificates-files/${cert.id}.png`;
        document.getElementById('modal-preview-hash').textContent = `Security Hash: ${cert.cert_hash}`;
        document.getElementById('modal-preview-download-png').href = `/api/certificates/${cert.id}/download/png`;
        const pdfBtn = document.getElementById('modal-preview-download-pdf');
        const verifyBtn = document.getElementById('modal-preview-verify-btn');
        if (pdfBtn) {
            pdfBtn.style.display = '';
            pdfBtn.href = `/api/certificates/${cert.id}/download/pdf`;
        }
        if (verifyBtn) {
            verifyBtn.style.display = '';
            verifyBtn.href = `/verify/${cert.id}`;
        }

        document.getElementById('modal-cert-preview').classList.remove('hidden');
    } catch (err) {
        alert("Failed to load certificate preview.");
    }
}

function closeCertPreviewModal() {
    document.getElementById('modal-cert-preview').classList.add('hidden');
}

// Create New Event Modal
function openNewEventModal() {
    document.getElementById('ev-date').value = new Date().toISOString().split('T')[0];
    document.getElementById('modal-new-event').classList.remove('hidden');
}

function closeNewEventModal() {
    document.getElementById('modal-new-event').classList.add('hidden');
}

async function submitNewEvent(e) {
    e.preventDefault();
    const payload = {
        name: document.getElementById('ev-name').value,
        organization: document.getElementById('ev-org').value,
        event_date: document.getElementById('ev-date').value,
        category: document.getElementById('ev-cat').value,
        template_id: document.getElementById('ev-template').value,
        citation_text: document.getElementById('ev-cite').value,
        signatory1_name: document.getElementById('ev-sig1-name').value,
        signatory1_title: document.getElementById('ev-sig1-title').value,
        signatory2_name: document.getElementById('ev-sig2-name').value,
        signatory2_title: document.getElementById('ev-sig2-title').value,
    };

    try {
        const res = await fetch('/api/events', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify(payload)
        });
        if (res.ok) {
            closeNewEventModal();
            await loadEvents();
            await loadDashboardStats();
            alert("New event created successfully!");
        }
    } catch (err) {
        alert("Error creating event.");
    }
}

// Email Dispatcher Simulation
async function dispatchEmail(certId) {
    try {
        const res = await fetch(`/api/certificates/${certId}/send-email`, { method: 'POST' });
        const data = await res.json();
        alert(data.message);
        await loadEmailLogs();
    } catch (err) {
        alert("Email dispatch simulation failed.");
    }
}

async function loadEmailLogs() {
    try {
        const res = await fetch('/api/email-logs');
        const logs = await res.json();
        const tbody = document.getElementById('email-logs-body');

        if (!logs || logs.length === 0) {
            tbody.innerHTML = `<tr><td colspan="7" class="p-8 text-center text-slate-400 italic">No email delivery logs recorded yet. Send a certificate to view dispatches here.</td></tr>`;
            return;
        }

        tbody.innerHTML = logs.map(l => `
            <tr class="hover:bg-slate-50 text-slate-700">
                <td class="p-3 font-mono font-bold text-slate-400">#${l.id}</td>
                <td class="p-3 font-mono font-bold text-slate-900">${escapeHtml(l.certificate_id)}</td>
                <td class="p-3 font-bold">${escapeHtml(l.recipient_name)}</td>
                <td class="p-3 font-mono text-emerald-700">${escapeHtml(l.recipient_email)}</td>
                <td class="p-3">${escapeHtml(l.event_name)}</td>
                <td class="p-3"><span class="px-2 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold text-[10px]">DELIVERED</span></td>
                <td class="p-3 text-slate-500 font-mono text-[11px]">${escapeHtml(l.sent_at)}</td>
            </tr>
        `).join('');
    } catch (err) {}
}

function escapeHtml(text) {
    if (!text) return '';
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}
