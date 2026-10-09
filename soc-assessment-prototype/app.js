const toast = document.getElementById('toast');
const toastMessage = document.getElementById('toast-message');

function showToast(message) {
  toastMessage.textContent = message;
  toast.classList.add('show');
  window.clearTimeout(showToast.timer);
  showToast.timer = window.setTimeout(() => toast.classList.remove('show'), 3600);
}

document.querySelectorAll('.nav-item').forEach((item) => {
  item.addEventListener('click', () => {
    document.querySelectorAll('.nav-item').forEach((link) => link.classList.remove('active'));
    item.classList.add('active');
    document.getElementById('page-name').textContent = item.textContent.replace(/\d/g, '').trim();
  });
});

document.getElementById('run-assessment').addEventListener('click', (event) => {
  const button = event.currentTarget;
  button.classList.add('is-running');
  button.textContent = 'Assessing telemetry…';
  window.setTimeout(() => {
    document.getElementById('soc-score').textContent = '76';
    document.getElementById('detection-value').textContent = '88%';
    button.classList.remove('is-running');
    button.innerHTML = 'Assessment complete <span>✓</span>';
    showToast('Assessment complete — SOC score improved to 76/100.');
  }, 1150);
});

const scenarios = [
  { title: 'Compromised VPN administrator', description: 'Test whether the SOC can follow a privileged remote-access compromise through endpoint execution and outbound communication.', risk: '89', coverage: '66.7%' },
  { title: 'Phishing-led endpoint compromise', description: 'Replay a controlled credential-harvesting scenario and assess endpoint, identity and network visibility.', risk: '81', coverage: '71.4%' },
  { title: 'Unusual service account activity', description: 'Assess whether lateral movement from a service account is detected before critical asset exposure.', risk: '77', coverage: '62.5%' }
];
let scenarioIndex = 0;
document.getElementById('change-scenario').addEventListener('click', () => {
  scenarioIndex = (scenarioIndex + 1) % scenarios.length;
  const scenario = scenarios[scenarioIndex];
  document.getElementById('scenario-title').textContent = scenario.title;
  document.getElementById('scenario-description').textContent = scenario.description;
  document.getElementById('projected-risk').innerHTML = `${scenario.risk}<span>/100</span>`;
  document.getElementById('projected-coverage').textContent = scenario.coverage;
  showToast(`Scenario loaded: ${scenario.title}.`);
});

document.getElementById('run-replay').addEventListener('click', (event) => {
  const button = event.currentTarget;
  button.classList.add('is-running');
  button.innerHTML = '<span>◌</span> Replaying scenario…';
  document.querySelectorAll('.sim-node').forEach((node, index) => {
    window.setTimeout(() => node.classList.add('active'), index * 220);
  });
  window.setTimeout(() => {
    button.classList.remove('is-running');
    button.innerHTML = '<span>✓</span> Replay complete';
    showToast('Safe replay complete — 2 detection gaps confirmed for review.');
  }, 1300);
});

document.querySelectorAll('.fix-button, .approve-button').forEach((button) => {
  button.addEventListener('click', () => showToast(`${button.dataset.action} added to the analyst queue.`));
});

document.getElementById('open-incident').addEventListener('click', () => showToast('Incident INC-4821 opened in the analyst workspace.'));
document.getElementById('view-coverage').addEventListener('click', () => showToast('Coverage map filtered to the active incident.'));
document.getElementById('highlight-graph').addEventListener('click', () => document.getElementById('risk').scrollIntoView({ behavior: 'smooth', block: 'center' }));
document.getElementById('focus-graph').addEventListener('click', () => showToast('Risk graph focused on INC-4821 and its connected entities.'));
