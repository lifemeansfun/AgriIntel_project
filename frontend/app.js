const API_URL = 'http://127.0.0.1:8000';

async function fetchState() {
    try {
        const res = await fetch(`${API_URL}/api/state`);
        const data = await res.json();
        renderGauges(data);
        document.getElementById('version-display').textContent = `v${data.version}`;
    } catch (err) {
        console.error('Failed to fetch state:', err);
    }
}

function renderGauges(data) {
    const grid = document.getElementById('gauges-grid');
    grid.innerHTML = '';

    for (const [crop, committed] of Object.entries(data.committed_area)) {
        const threshold = data.glut_thresholds[crop];
        const headroom = data.headroom[crop];
        const percent = Math.min(100, (committed / threshold) * 100);
        
        const isDanger = percent >= 95;
        
        const card = document.createElement('div');
        card.className = 'gauge-card';
        card.innerHTML = `
            <div class="gauge-header">
                <span>${crop}</span>
                <span style="color: ${isDanger ? 'var(--danger)' : 'var(--text)'}">${percent.toFixed(1)}%</span>
            </div>
            <div class="progress-track">
                <div class="progress-fill ${isDanger ? 'danger-fill' : ''}" style="width: ${percent}%"></div>
            </div>
            <div style="font-size: 0.8rem; color: rgba(255,255,255,0.6)">
                Committed: ${committed.toFixed(1)} / ${threshold.toFixed(1)} ha<br>
                Headroom: ${headroom.toFixed(1)} ha
            </div>
        `;
        grid.appendChild(card);
    }
}

document.getElementById('allocate-form').addEventListener('submit', async (e) => {
    e.preventDefault();
    const btn = e.target.querySelector('button');
    btn.textContent = 'Committing...';
    btn.style.opacity = '0.7';
    
    const payload = {
        farmer_id: document.getElementById('farmer-id').value,
        crop: document.getElementById('crop-select').value,
        area_ha: parseFloat(document.getElementById('area-ha').value)
    };
    
    try {
        const res = await fetch(`${API_URL}/api/commit`, {
            method: 'POST',
            headers: {'Content-Type': 'application/json'},
            body: JSON.stringify(payload)
        });
        
        const msgDiv = document.getElementById('status-message');
        if (res.ok) {
            const data = await res.json();
            msgDiv.style.color = 'var(--accent)';
            msgDiv.textContent = `Success: ${data.message}`;
            fetchState(); // Refresh gauges
        } else {
            const error = await res.json();
            msgDiv.style.color = 'var(--danger)';
            msgDiv.textContent = `Error: ${error.detail}`;
        }
    } catch (err) {
        console.error(err);
    } finally {
        btn.textContent = 'Commit Allocation';
        btn.style.opacity = '1';
    }
});

// Initial load
fetchState();
// Polling every 2 seconds for live updates
setInterval(fetchState, 2000);
