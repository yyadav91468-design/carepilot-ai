
const $ = (s) => document.querySelector(s);
const $$ = (s) => [...document.querySelectorAll(s)];

let dashboardData = null;
let lastAssistantResponse = '';
let sessionId = 'demo-' + Math.random().toString(36).slice(2, 9);

const initials = (name = '?') =>
  name.trim().split(/\s+/).slice(0, 2).map(x => x[0]).join('').toUpperCase();

const esc = (s = '') =>
  String(s).replace(/[&<>"']/g, c => ({
    '&': '&amp;',
    '<': '&lt;',
    '>': '&gt;',
    '"': '&quot;',
    "'": '&#39;'
  }[c]));

const statusClass = s => ({
  Confirmed: 'confirmed',
  Pending: 'pending',
  Cancelled: 'cancelled',
  'Needs review': 'review',
  'Urgent escalation': 'cancelled',
  Responded: 'confirmed'
}[s] || 'pending');

function toast(msg) {
  const t = $('#toast');
  if (!t) return;
  t.textContent = msg;
  t.classList.add('show');
  setTimeout(() => t.classList.remove('show'), 2800);
}

async function api(url, options = {}) {
  const r = await fetch(url, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(options.headers || {})
    }
  });

  const data = await r.json().catch(() => ({
    detail: 'Unexpected server response'
  }));

  if (!r.ok) throw new Error(data.detail || 'Request failed');
  return data;
}

function setView(view) {
  $$('.view').forEach(v => v.classList.add('hidden'));

  const target = $('#view-' + view);
  if (target) target.classList.remove('hidden');

  $$('.nav').forEach(n =>
    n.classList.toggle('active', n.dataset.view === view)
  );

  const names = {
    overview: [
      'Good afternoon, Yash ✦',
      'Here’s what’s happening at your clinic today.'
    ],
    appointments: [
      'Appointment management',
      'Track requests and keep the booking pipeline up to date.'
    ],
    inquiries: [
      'Patient inquiry review',
      'Review AI-generated drafts before responses are marked as sent.'
    ],
    assistant: [
      'Patient assistant',
      'Test the end-to-end admin workflow using synthetic demo data.'
    ]
  };

  if (names[view]) {
    $('#page-title').textContent = names[view][0];
    $('#page-subtitle').textContent = names[view][1];
  }

  if (view === 'assistant') $('#chat-input').focus();
}

$$('.nav').forEach(n =>
  n.addEventListener('click', () => setView(n.dataset.view))
);

$$('[data-go]').forEach(n =>
  n.addEventListener('click', () => setView(n.dataset.go))
);

function appointmentRows(items, limit = 100) {
  if (!items.length) {
    return '<div class="empty-state">No appointments yet. Create a request to get started.</div>';
  }

  return `<table>
    <thead>
      <tr>
        <th>PATIENT</th>
        <th>PREFERRED TIME</th>
        <th>REASON</th>
        <th>STATUS</th>
        <th>UPDATE</th>
      </tr>
    </thead>
    <tbody>
      ${items.slice(0, limit).map(a => `
        <tr>
          <td>
            <div class="patient-cell">
              <span class="patient-mini">${esc(initials(a.patient_name))}</span>
              ${esc(a.patient_name)}
            </div>
            <small style="color:#a0a8b7;font-size:8px">
              CP-${String(a.id).padStart(4, '0')}
            </small>
          </td>
          <td>${esc(a.preferred_time)}</td>
          <td>${esc(a.reason)}</td>
          <td>
            <span class="status status-${statusClass(a.status)}">
              ${esc(a.status)}
            </span>
          </td>
          <td class="row-actions">
            <select aria-label="Update appointment ${a.id}"
                    data-status-id="${a.id}">
              <option ${a.status === 'Pending' ? 'selected' : ''}>Pending</option>
              <option ${a.status === 'Confirmed' ? 'selected' : ''}>Confirmed</option>
              <option ${a.status === 'Cancelled' ? 'selected' : ''}>Cancelled</option>
            </select>

            <button type="button"
                    class="text-button"
                    data-reschedule-id="${a.id}"
                    data-current-time="${esc(a.preferred_time)}">
              Reschedule
            </button>
          </td>
        </tr>
      `).join('')}
    </tbody>
  </table>`;
}

function renderInquiries(items) {
  const target = $('#all-inquiries');
  const pending = items.filter(i => i.status !== 'Responded');

  if (!items.length) {
    target.innerHTML = '<div class="panel empty-state">No inquiries yet.</div>';
    return;
  }

  target.innerHTML = items.map(i => `
    <article class="review-card">
      <div style="display:flex;justify-content:space-between;gap:8px">
        <h3>${esc(i.intent.replaceAll('_', ' ').replace(/^./, x => x.toUpperCase()))}</h3>
        <span class="status status-${statusClass(i.status)}">${esc(i.status)}</span>
      </div>

      <div class="meta">
        ${esc(i.patient_name || 'Patient not identified')} ·
        ${new Date(i.created_at).toLocaleString()}
      </div>

      <blockquote>
        <b>Patient message</b><br>${esc(i.message)}
      </blockquote>

      <label for="reply-${i.id}">AI-generated draft / staff response</label>

      <textarea id="reply-${i.id}" ${i.status === 'Responded' ? 'disabled' : ''}>${esc(i.reviewed_response || i.draft_response)}</textarea>

      ${i.status !== 'Responded'
        ? `<button class="primary-btn" data-send-inquiry="${i.id}">Approve & mark sent →</button>`
        : '<small style="color:#27936e">✓ Staff-reviewed response recorded in demo log</small>'}
    </article>
  `).join('');

  target.querySelectorAll('[data-send-inquiry]').forEach(btn =>
    btn.addEventListener('click', async () => {
      const id = btn.dataset.sendInquiry;
      const response = $(`#reply-${id}`).value.trim();

      if (!response) return toast('Please enter a response first.');

      try {
        await api(`/api/inquiries/${id}/send`, {
          method: 'POST',
          body: JSON.stringify({ response })
        });

        toast('Reviewed response marked as sent.');
        await refreshDashboard();
      } catch (e) {
        toast(e.message);
      }
    })
  );
}

function renderAttention(items) {
  const pending = items.filter(i => i.status !== 'Responded');

  $('#inquiry-count').textContent = pending.length;
  $('#nav-inquiries').textContent = pending.length;

  $('#attention-list').innerHTML = pending.slice(0, 2).map(i => `
    <div class="inquiry-item">
      <div class="inquiry-symbol">✉</div>
      <div>
        <b>${esc(i.intent.replaceAll('_', ' '))} · ${esc(i.patient_name || 'Unknown patient')}</b>
        <p>${esc(i.message.slice(0, 90))}${i.message.length > 90 ? '…' : ''}</p>
        <button class="text-button" data-open-inquiries>Review response →</button>
      </div>
    </div>
  `).join('') || '<div class="empty-state">You’re all caught up. No inquiries need review.</div>';

  $$('[data-open-inquiries]').forEach(b =>
    b.addEventListener('click', () => setView('inquiries'))
  );
}

async function refreshDashboard() {
  try {
    dashboardData = await api('/api/dashboard');
    const d = dashboardData;

    $('#stat-total').textContent = d.total_appointments;
    $('#stat-pending').textContent = d.pending_appointments;
    $('#stat-confirmed').textContent = d.confirmed_appointments;
    $('#stat-cancelled').textContent = d.cancelled_appointments;
    $('#nav-appointments').textContent = d.total_appointments;

    $('#upcoming-table').innerHTML = appointmentRows(d.appointments, 5);
    $('#all-appointments').innerHTML = appointmentRows(d.appointments);

    // Attach status and reschedule handlers to both appointment tables.
    ['#all-appointments', '#upcoming-table'].forEach(selector => {
      const table = $(selector);

      table.querySelectorAll('[data-status-id]').forEach(el => {
        el.addEventListener('change', () =>
          updateStatus(el.dataset.statusId, el.value)
        );
      });

      table.querySelectorAll('[data-reschedule-id]').forEach(btn => {
        btn.addEventListener('click', () =>
          rescheduleAppointment(
            btn.dataset.rescheduleId,
            btn.dataset.currentTime
          )
        );
      });
    });

    renderAttention(d.inquiries);
    renderInquiries(d.inquiries);
  } catch (e) {
    toast('Could not load dashboard: ' + e.message);
  }
}

async function updateStatus(id, status) {
  try {
    let opts = {
      method: 'PATCH',
      body: JSON.stringify({ status })
    };

    let d;

    try {
      d = await api(`/api/appointments/${id}`, opts);
    } catch (first) {
      if (!String(first.message).toLowerCase().includes('passcode')) {
        throw first;
      }

      const pass = window.prompt(
        'Clinic admin passcode required to update appointment status:'
      );

      if (!pass) throw new Error('Status update cancelled.');

      opts = {
        ...opts,
        headers: { 'X-Admin-Passcode': pass }
      };

      d = await api(`/api/appointments/${id}`, opts);
    }

    toast(d.message);
    await refreshDashboard();
  } catch (e) {
    toast(e.message);
    await refreshDashboard();
  }
}

async function rescheduleAppointment(id, currentTime) {
  const preferredTime = window.prompt(
    'Enter the new preferred date and time:',
    currentTime || ''
  );

  if (preferredTime === null) return;

  if (!preferredTime.trim()) {
    return toast('Please enter a new date and time.');
  }

  let opts = {
    method: 'PATCH',
    body: JSON.stringify({
      preferred_time: preferredTime.trim()
    })
  };

  try {
    let d;

    try {
      d = await api(`/api/appointments/${id}/reschedule`, opts);
    } catch (first) {
      if (!String(first.message).toLowerCase().includes('passcode')) {
        throw first;
      }

      const pass = window.prompt(
        'Clinic admin passcode required to reschedule this appointment:'
      );

      if (!pass) throw new Error('Rescheduling cancelled.');

      opts = {
        ...opts,
        headers: { 'X-Admin-Passcode': pass }
      };

      d = await api(`/api/appointments/${id}/reschedule`, opts);
    }

    toast(d.message || 'Appointment rescheduled.');
    await refreshDashboard();
  } catch (e) {
    toast(e.message);
  }
}

function addMessage(role, text, label) {
  const box = $('#chat-messages');
  const d = document.createElement('div');

  d.className = 'message ' + (role === 'user' ? 'user-message' : 'bot-message');
  d.innerHTML = `${role === 'bot' ? '<div class="mini-avatar">✳</div>' : ''}
    <div>
      <div class="bubble">${esc(text).replace(/\n/g, '<br>')}</div>
      <small>${esc(label)}</small>
    </div>`;

  box.appendChild(d);
  box.scrollTop = box.scrollHeight;
}

function renderTrace(data) {
  $('#trace-empty').classList.add('hidden');

  const t = $('#trace-data');
  t.classList.remove('hidden');

  const ap = data.appointment;

  const steps = [
    ['✓', 'Message received', 'Persisted to conversation history.'],
    ['✓', 'Intent detected', `Classified as: ${data.intent.replaceAll('_', ' ')}.`],
    ['✓', 'Safety check', data.urgent
      ? 'Urgent phrase detected; emergency guidance returned and staff escalation created.'
      : 'No configured urgent keyword detected. This is not a clinical assessment.'],
    ['✓', 'Information extraction', ap
      ? `Name: ${ap.patient_name}; requested time: ${ap.preferred_time}; reason: ${ap.reason}.`
      : 'No complete appointment record extracted. ' +
        (data.needs_staff_review ? 'Routed to the staff review queue.' : 'FAQ/general response returned.')],
    ['✓', ap ? 'Appointment request created' : 'Response generated', ap
      ? `CP-${String(ap.id).padStart(4, '0')} · status ${ap.status}. Saved to database.`
      : `Provider: ${data.provider}. AI-generated or fallback response is labelled in the chat.`],
    ['↗', data.needs_staff_review || data.urgent ? 'Human review required' : 'Next step',
      data.needs_staff_review || data.urgent
        ? 'Open Inquiry review to approve or respond.'
        : 'Staff can confirm appointment availability in the dashboard.']
  ];

  t.innerHTML = steps.map(s => `
    <div class="trace-step">
      <span class="check">${s[0]}</span>
      <div><b>${esc(s[1])}</b><small>${esc(s[2])}</small></div>
    </div>
  `).join('');
}

$('#chat-form').addEventListener('submit', async e => {
  e.preventDefault();

  const input = $('#chat-input');
  const message = input.value.trim();
  if (!message) return;

  input.value = '';
  addMessage('user', message, 'Patient · Demo conversation');

  const send = $('.send-btn');
  send.disabled = true;
  send.textContent = '…';

  try {
    const d = await api('/api/chat', {
      method: 'POST',
      body: JSON.stringify({ message, session_id: sessionId })
    });

    lastAssistantResponse = d.reply;

    addMessage(
      'bot',
      d.reply,
      `${d.provider} · ${d.needs_staff_review ? 'Staff review required' : 'Generated response'}${d.urgent ? ' · Urgent escalation' : ''}`
    );

    renderTrace(d);
    await refreshDashboard();
  } catch (err) {
    addMessage(
      'bot',
      'I’m sorry, the request could not be processed. Please try again or contact clinic staff.',
      'System fallback'
    );
    toast(err.message);
  } finally {
    send.disabled = false;
    send.textContent = '↑';
  }
});

$$('[data-prompt]').forEach(b =>
  b.addEventListener('click', () => {
    $('#chat-input').value = b.dataset.prompt;
    $('#chat-form').requestSubmit();
  })
);

$('#reset-chat').addEventListener('click', () => {
  sessionId = 'demo-' + Math.random().toString(36).slice(2, 9);

  $('#chat-messages').innerHTML = `
    <div class="chat-day">NEW SESSION</div>
    <div class="message bot-message">
      <div class="mini-avatar">✳</div>
      <div>
        <div class="bubble">Hello! I can help start an appointment request, answer basic clinic FAQs, or route a message to clinic staff. How can I help?</div>
        <small>CarePilot AI · Generated response</small>
      </div>
    </div>`;

  $('#trace-empty').classList.remove('hidden');
  $('#trace-data').classList.add('hidden');
  lastAssistantResponse = '';
});

$('#speak-last').addEventListener('click', () => {
  if (!lastAssistantResponse) return toast('Send a patient message first.');

  if (!('speechSynthesis' in window)) {
    return toast('Speech output is not supported in this browser.');
  }

  speechSynthesis.cancel();
  speechSynthesis.speak(new SpeechSynthesisUtterance(lastAssistantResponse));
});

$('#voice-input').addEventListener('click', () => {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;

  if (!SR) {
    return toast('Voice input is not supported here. Try Chrome and allow microphone access.');
  }

  const rec = new SR();
  rec.lang = 'en-IN';
  rec.interimResults = false;

  rec.onresult = e => {
    $('#chat-input').value = e.results[0][0].transcript;
    $('#chat-input').focus();
  };

  rec.onerror = () => toast('Voice input failed. Check microphone permission.');
  rec.start();
});

function showModal() {
  $('#appointment-modal').classList.remove('hidden');
}

function hideModal() {
  $('#appointment-modal').classList.add('hidden');
}

$('#new-appointment').addEventListener('click', showModal);
$('#new-appointment-2').addEventListener('click', showModal);
$('#close-modal').addEventListener('click', hideModal);
$('#cancel-modal').addEventListener('click', hideModal);

$('#appointment-modal').addEventListener('click', e => {
  if (e.target.id === 'appointment-modal') hideModal();
});

$('#appointment-form').addEventListener('submit', async e => {
  e.preventDefault();

  const f = new FormData(e.target);

  try {
    const d = await api('/api/appointments', {
      method: 'POST',
      body: JSON.stringify({
        patient_name: f.get('name'),
        preferred_time: f.get('time'),
        reason: f.get('reason')
      })
    });

    hideModal();
    e.target.reset();

    await refreshDashboard();
    toast(d.message);
    setView('appointments');
  } catch (err) {
    toast(err.message);
  }
});

$('#refresh').addEventListener('click', () =>
  refreshDashboard().then(() => toast('Dashboard refreshed.'))
);

refreshDashboard();
