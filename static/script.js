"use strict";

const WORK_MINUTES = window.WORK_MINUTES; // 8h30m = 510

const STORAGE_KEY = "arrivalTime";
const OVERTIME_KEY = "overtime";
const ACTUAL_KEY = "actualDeparture";

const arrivalInput = document.getElementById("arrival");
const overtimeInput = document.getElementById("overtime");
const actualInput = document.getElementById("actual");
const resultBox = document.getElementById("result");
const departureEl = document.getElementById("departure");
const countdownEl = document.getElementById("countdown");
const statusEl = document.getElementById("status");

const overtimeResult = document.getElementById("overtimeResult");
const departureOtEl = document.getElementById("departureOt");
const countdownOtEl = document.getElementById("countdownOt");
const statusOtEl = document.getElementById("statusOt");

const actualResult = document.getElementById("actualResult");
const workedEl = document.getElementById("worked");
const actualDiffEl = document.getElementById("actualDiff");
const actualStatusEl = document.getElementById("actualStatus");
const balanceResult = document.getElementById("balanceResult");
const balanceLabelEl = document.getElementById("balanceLabel");
const balanceValueEl = document.getElementById("balanceValue");

/* ---------- Odpočet ---------- */

// Vrátí "HH:MM" -> minuty od půlnoci, nebo null když je vstup neplatný
function parseTime(str) {
  const m = /^(\d{1,2}):(\d{2})$/.exec(str.trim());
  if (!m) return null;
  const h = parseInt(m[1], 10);
  const min = parseInt(m[2], 10);
  if (h > 23 || min > 59) return null;
  return h * 60 + min;
}

function fmtHM(totalMin) {
  const h = Math.floor(totalMin / 60) % 24;
  const m = totalMin % 60;
  return String(h).padStart(2, "0") + ":" + String(m).padStart(2, "0");
}

let timer = null;
let departureMain = null; // Date – plná pracovní doba
let departureOt = null;   // Date – zkráceno o přesčas (nebo null)

function startCountdown() {
  const arrivalMin = parseTime(arrivalInput.value);
  if (arrivalMin === null) {
    resultBox.hidden = true;
    actualResult.hidden = true;
    localStorage.removeItem(STORAGE_KEY);
    if (timer) clearInterval(timer);
    return;
  }

  // Ulož platné hodnoty, ať přežijí refresh
  localStorage.setItem(STORAGE_KEY, arrivalInput.value);

  const departureMin = arrivalMin + WORK_MINUTES;
  departureEl.textContent = fmtHM(departureMin);
  resultBox.hidden = false;

  const now0 = new Date();
  departureMain = new Date(now0);
  departureMain.setHours(0, departureMin, 0, 0);

  // Přesčas: zkrátí potřebnou pracovní dobu (min. 0)
  const overtimeMin = parseTime(overtimeInput.value);
  if (overtimeMin !== null && overtimeMin > 0) {
    localStorage.setItem(OVERTIME_KEY, overtimeInput.value);
    const requiredMin = Math.max(0, WORK_MINUTES - overtimeMin);
    const departureOtMin = arrivalMin + requiredMin;
    departureOtEl.textContent = fmtHM(departureOtMin);
    departureOt = new Date(now0);
    departureOt.setHours(0, departureOtMin, 0, 0);
    overtimeResult.hidden = false;
  } else {
    if (overtimeMin === null) localStorage.removeItem(OVERTIME_KEY);
    departureOt = null;
    overtimeResult.hidden = true;
  }

  updateActual(arrivalMin);

  if (timer) clearInterval(timer);
  tick();
  timer = setInterval(tick, 1000);
}

// Porovná skutečný odchod s plnou pracovní dobou od příchodu
function updateActual(arrivalMin) {
  const actualMin = parseTime(actualInput.value);
  if (actualMin === null) {
    localStorage.removeItem(ACTUAL_KEY);
    actualResult.hidden = true;
    return;
  }

  localStorage.setItem(ACTUAL_KEY, actualInput.value);

  // Odchod před příchodem = práce přes půlnoc
  let workedMin = actualMin - arrivalMin;
  if (workedMin < 0) workedMin += 24 * 60;

  const diff = workedMin - WORK_MINUTES;
  workedEl.textContent = fmtDur(workedMin);

  if (diff >= 0) {
    actualDiffEl.textContent = "+" + fmtDur(diff);
    actualDiffEl.className = "countdown small green";
    actualStatusEl.className = "status small green";
    actualStatusEl.textContent = "Přesčas";
  } else {
    actualDiffEl.textContent = "−" + fmtDur(-diff);
    actualDiffEl.className = "countdown small red";
    actualStatusEl.className = "status small red";
    actualStatusEl.textContent = "Chybí do naplnění pracovní doby";
  }

  // Se zadaným přesčasem: dnešní manko se odečte z naspořeného přesčasu
  const overtimeMin = parseTime(overtimeInput.value);
  if (overtimeMin !== null && overtimeMin > 0) {
    const balance = overtimeMin + diff;
    if (balance >= 0) {
      balanceLabelEl.className = "status green";
      balanceLabelEl.textContent = "Zbývá přesčasu";
      balanceValueEl.className = "countdown green";
      balanceValueEl.textContent = "+" + fmtDur(balance);
    } else {
      balanceLabelEl.className = "status red";
      balanceLabelEl.textContent = "Přesčas vyčerpán, chybí odpracovat";
      balanceValueEl.className = "countdown red";
      balanceValueEl.textContent = "−" + fmtDur(-balance);
    }
    balanceResult.hidden = false;
  } else {
    balanceResult.hidden = true;
  }

  actualResult.hidden = false;
}

// Délka trvání jako "H:MM" (bez omezení na 24 h)
function fmtDur(totalMin) {
  const h = Math.floor(totalMin / 60);
  const m = totalMin % 60;
  return h + ":" + String(m).padStart(2, "0");
}

function tick() {
  renderRemaining(departureMain, countdownEl, statusEl, "countdown", "status");
  if (departureOt) {
    renderRemaining(departureOt, countdownOtEl, statusOtEl, "countdown small", "status small");
  }
}

// Vykreslí zbývající/přesčasový čas do daných elementů + nastaví barvu
function renderRemaining(departure, cdEl, stEl, cdBase, stBase) {
  const remainingMs = departure - new Date();

  if (remainingMs > 0) {
    // Ještě ubývá -> ČERVENÁ
    const sec = Math.floor(remainingMs / 1000);
    cdEl.textContent = fmtHMS(sec);
    cdEl.className = cdBase + " red";
    stEl.className = stBase + " red";
    stEl.textContent = "Zbývá do konce pracovní doby";
  } else {
    // Naplněno -> ZELENÁ
    const sec = Math.floor(-remainingMs / 1000);
    cdEl.textContent = "+" + fmtHMS(sec);
    cdEl.className = cdBase + " green";
    stEl.className = stBase + " green";
    stEl.textContent = "Pracovní doba naplněna 🎉";
  }
}

function fmtHMS(totalSec) {
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  return String(h).padStart(2, "0") + ":" +
         String(m).padStart(2, "0") + ":" +
         String(s).padStart(2, "0");
}

arrivalInput.addEventListener("input", startCountdown);
overtimeInput.addEventListener("input", startCountdown);
actualInput.addEventListener("input", startCountdown);

// Po načtení stránky obnov naposledy zadané hodnoty
const savedOvertime = localStorage.getItem(OVERTIME_KEY);
if (savedOvertime) overtimeInput.value = savedOvertime;

const savedActual = localStorage.getItem(ACTUAL_KEY);
if (savedActual) actualInput.value = savedActual;

const saved = localStorage.getItem(STORAGE_KEY);
if (saved) {
  arrivalInput.value = saved;
  startCountdown();
}

/* ---------- Kolečkový výběr (ciferník) ---------- */

const overlay = document.getElementById("overlay");
const svg = document.getElementById("clockFace");
const pickHourEl = document.getElementById("pickHour");
const pickMinuteEl = document.getElementById("pickMinute");
const clockModeEl = document.getElementById("clockMode");
const SVGNS = "http://www.w3.org/2000/svg";

const CX = 120, CY = 120;
const R_OUTER = 96, R_INNER = 60;

let mode = "hour";      // "hour" | "minute"
let selHour = 0;
let selMinute = 0;
let clockTarget = arrivalInput; // vstup, do kterého ciferník zapíše

document.getElementById("openClock").addEventListener("click", () => openClock(arrivalInput));
document.getElementById("openClockOt").addEventListener("click", () => openClock(overtimeInput));
document.getElementById("openClockActual").addEventListener("click", () => openClock(actualInput));
document.getElementById("clockCancel").addEventListener("click", closeClock);
document.getElementById("clockOk").addEventListener("click", confirmClock);
pickHourEl.addEventListener("click", () => setMode("hour"));
pickMinuteEl.addEventListener("click", () => setMode("minute"));
overlay.addEventListener("click", (e) => { if (e.target === overlay) closeClock(); });

function openClock(target) {
  clockTarget = target;
  const existing = parseTime(target.value);
  if (existing !== null) {
    selHour = Math.floor(existing / 60);
    selMinute = existing % 60;
  } else {
    selHour = 0;
    selMinute = 0;
  }
  setMode("hour");
  overlay.hidden = false;
}

function closeClock() { overlay.hidden = true; }

function confirmClock() {
  clockTarget.value =
    String(selHour).padStart(2, "0") + ":" + String(selMinute).padStart(2, "0");
  closeClock();
  startCountdown();
}

function setMode(m) {
  mode = m;
  clockModeEl.textContent = m === "hour" ? "Vyber hodinu" : "Vyber minutu";
  pickHourEl.classList.toggle("active", m === "hour");
  pickMinuteEl.classList.toggle("active", m === "minute");
  render();
}

// Úhel (0 = nahoře, roste po směru hod. ručiček) -> souřadnice
function pos(angleDeg, radius) {
  const rad = (angleDeg * Math.PI) / 180;
  return { x: CX + radius * Math.sin(rad), y: CY - radius * Math.cos(rad) };
}

function render() {
  pickHourEl.textContent = String(selHour).padStart(2, "0");
  pickMinuteEl.textContent = String(selMinute).padStart(2, "0");

  while (svg.firstChild) svg.removeChild(svg.firstChild);

  // Pozadí
  const bg = document.createElementNS(SVGNS, "circle");
  bg.setAttribute("cx", CX);
  bg.setAttribute("cy", CY);
  bg.setAttribute("r", 110);
  bg.setAttribute("class", "clock-bg");
  svg.appendChild(bg);

  // Ručička k aktuálně vybrané hodnotě
  const selAngle = mode === "hour" ? (selHour % 12) * 30 : selMinute * 6;
  const selRadius = (mode === "hour" && (selHour === 0 || selHour > 12)) ? R_INNER : R_OUTER;
  const knob = pos(selAngle, selRadius);
  const hand = document.createElementNS(SVGNS, "line");
  hand.setAttribute("x1", CX);
  hand.setAttribute("y1", CY);
  hand.setAttribute("x2", knob.x);
  hand.setAttribute("y2", knob.y);
  hand.setAttribute("class", "clock-hand");
  svg.appendChild(hand);

  const knobC = document.createElementNS(SVGNS, "circle");
  knobC.setAttribute("cx", knob.x);
  knobC.setAttribute("cy", knob.y);
  knobC.setAttribute("r", 16);
  knobC.setAttribute("class", "clock-knob");
  svg.appendChild(knobC);

  const center = document.createElementNS(SVGNS, "circle");
  center.setAttribute("cx", CX);
  center.setAttribute("cy", CY);
  center.setAttribute("r", 4);
  center.setAttribute("class", "clock-center");
  svg.appendChild(center);

  if (mode === "hour") {
    // Vnější prstenec 1-12
    for (let h = 1; h <= 12; h++) addNumber(h, h * 30, R_OUTER, false, h === selHour);
    // Vnitřní prstenec 13-23 a 00
    for (let h = 13; h <= 23; h++) addNumber(h, (h % 12) * 30, R_INNER, true, h === selHour);
    addNumber(0, 0, R_INNER, true, selHour === 0);
  } else {
    // Minuty po 5
    for (let m = 0; m < 60; m += 5) addNumber(m, m * 6, R_OUTER, false, m === selMinute);
  }
}

function addNumber(value, angleDeg, radius, inner, selected) {
  const p = pos(angleDeg, radius);
  const label = value === 0 && !inner ? "00" : String(value).padStart(2, "0");

  const t = document.createElementNS(SVGNS, "text");
  t.setAttribute("x", p.x);
  t.setAttribute("y", p.y);
  t.setAttribute("class", "clock-num" + (inner ? " inner" : "") + (selected ? " selected" : ""));
  t.textContent = label;
  svg.appendChild(t);
}

// Výběr klikem/tažením kdekoliv po ciferníku -> libovolná minuta / hodina
let dragging = false;

function pickFromPointer(e) {
  const rect = svg.getBoundingClientRect();
  const x = (e.clientX - rect.left) * (240 / rect.width);
  const y = (e.clientY - rect.top) * (240 / rect.height);
  const dx = x - CX, dy = y - CY;

  let deg = (Math.atan2(dx, -dy) * 180) / Math.PI; // 0 = nahoře, po směru hod. ručiček
  if (deg < 0) deg += 360;

  if (mode === "hour") {
    const hp = Math.round(deg / 30) % 12; // 0..11
    const inner = Math.hypot(dx, dy) < (R_OUTER + R_INNER) / 2;
    if (inner) selHour = hp === 0 ? 0 : hp + 12; // 00, 13..23
    else selHour = hp === 0 ? 12 : hp;           // 1..12
  } else {
    selMinute = Math.round(deg / 6) % 60;        // 0..59
  }
  render();
}

svg.addEventListener("pointerdown", (e) => {
  dragging = true;
  svg.setPointerCapture(e.pointerId);
  pickFromPointer(e);
});
svg.addEventListener("pointermove", (e) => {
  if (dragging) pickFromPointer(e);
});
svg.addEventListener("pointerup", () => {
  dragging = false;
  if (mode === "hour") setMode("minute"); // po výběru hodiny přepni na minuty
});

/* ---------- Vymazání údajů ---------- */

document.getElementById("clearData").addEventListener("click", () => {
  if (!confirm("Opravdu vymazat zadaný čas příchodu, přesčas i skutečný odchod?")) return;

  localStorage.removeItem(STORAGE_KEY);
  localStorage.removeItem(OVERTIME_KEY);
  localStorage.removeItem(ACTUAL_KEY);
  arrivalInput.value = "";
  overtimeInput.value = "";
  actualInput.value = "";
  resultBox.hidden = true;
  overtimeResult.hidden = true;
  actualResult.hidden = true;
  if (timer) clearInterval(timer);
});
