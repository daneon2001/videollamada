import { CONFIG } from "./config.js";

const API_BASE = (CONFIG.API_BASE || "").replace(/\/$/, "");
const SIGNAL_URL = CONFIG.SIGNAL_URL || API_BASE;

const el = (id) => document.getElementById(id);
const statusMessage = el("statusMessage");
const btnStart = el("btnStart");
const btnHang = el("btnHang");
const loginEmail = el("loginEmail");
const loginPassword = el("loginPassword");
const btnLogin = el("btnLogin");
const btnLogout = el("btnLogout");
const authStatus = el("authStatus");
const doctorPanel = el("doctorPanel");
const patientPanel = el("patientPanel");
const callPanel = el("callPanel");
const callSummary = el("callSummary");
const waitingCalls = el("waitingCalls");
const btnRefreshCalls = el("btnRefreshCalls");
const btnRequestCall = el("btnRequestCall");
const doctorAvailable = el("doctorAvailable");
const patientNote = el("patientNote");
const roomInput = el("room");

const state = {
  token: null,
  user: null,
  currentCall: null,
  callPoll: null,
};

function setStatus(msg = "", type = "info") {
  if (!statusMessage) return;
  statusMessage.textContent = msg;
  statusMessage.style.color = type === "error" ? "#b00020" : "#333";
}

function setSectionVisible(section, visible) {
  if (!section) return;
  section.classList.toggle("hidden", !visible);
}

function resetCallState() {
  state.currentCall = null;
  stopCallPolling();
  updateCallPanel();
  updatePanels();
}

function updatePanels() {
  const logged = Boolean(state.user && state.token);
  btnLogin.disabled = !API_BASE || logged;
  btnLogout.disabled = !logged;
  setSectionVisible(doctorPanel, logged && state.user.role === "doctor");
  setSectionVisible(patientPanel, logged && state.user.role === "patient");
  setSectionVisible(callPanel, Boolean(state.currentCall));
  btnRequestCall.disabled = !logged || state.user.role !== "patient" || (state.currentCall && !["ended", "cancelled"].includes(state.currentCall.status));
  if (!logged) {
    waitingCalls.innerHTML = "";
    authStatus.textContent = "Ingresa tus credenciales para comenzar.";
  }
}

function updateCallPanel() {
  if (!state.currentCall) {
    callSummary.textContent = "Aun no hay llamada asignada.";
    setSectionVisible(callPanel, false);
    btnStart.disabled = true;
    btnHang.disabled = true;
    updatePanels();
    return;
  }

  const call = state.currentCall;
  setSectionVisible(callPanel, true);
  const counterpartLabel = state.user?.role === "doctor" ? `Paciente: ${call.patient_id}` : `Doctor: ${call.doctor_id || "pendiente"}`;
  callSummary.textContent = `ID ${call.id} | Room ${call.room_id} | Estado ${call.status} | ${counterpartLabel}`;
  if (call.room_id) {
    roomInput.value = call.room_id;
  }

  const isDoctor = state.user?.role === "doctor";
  const doctorAssigned = Boolean(call.doctor_id);
  const allowedStatuses = isDoctor ? ["assigned", "in_progress"] : ["assigned", "in_progress"];
  const canStart = allowedStatuses.includes(call.status) && (isDoctor || doctorAssigned);
  btnStart.disabled = !canStart;
  btnHang.disabled = call.status === "ended" || call.status === "cancelled";

  if (["ended", "cancelled"].includes(call.status)) {
    stopCallPolling();
    btnStart.disabled = true;
  }
  updatePanels();
}

function assignCall(call) {
  state.currentCall = call;
  updateCallPanel();
  updatePanels();
  startCallPolling();
}

function startCallPolling() {
  stopCallPolling();
  if (!state.currentCall) return;
  state.callPoll = setInterval(fetchCurrentCall, 5000);
}

function stopCallPolling() {
  if (state.callPoll) {
    clearInterval(state.callPoll);
    state.callPoll = null;
  }
}

async function fetchCurrentCall() {
  if (!state.currentCall) return;
  try {
    const call = await apiFetch(`/calls/${state.currentCall.id}`);
    state.currentCall = call;
    updateCallPanel();
    if (["ended", "cancelled"].includes(call.status)) {
      stopCallPolling();
    }
  } catch (err) {
    console.error("Error fetching call", err);
  }
}

async function apiFetch(path, { method = "GET", body, headers } = {}) {
  if (!API_BASE) throw new Error("API_BASE no configurado");
  const url = path.startsWith("http") ? path : `${API_BASE}${path}`;
  const opts = { method, headers: { Accept: "application/json", ...(headers || {}) } };
  if (state.token) {
    opts.headers.Authorization = `Bearer ${state.token}`;
  }
  if (body !== undefined && body !== null) {
    if (body instanceof FormData) {
      opts.body = body;
    } else {
      opts.headers["Content-Type"] = "application/json";
      opts.body = JSON.stringify(body);
    }
  }
  const resp = await fetch(url, opts);
  if (!resp.ok) {
    const text = await resp.text();
    throw new Error(text || `Error HTTP ${resp.status}`);
  }
  if (resp.status === 204) return null;
  return resp.json();
}

async function handleLogin() {
  try {
    if (!API_BASE) {
      setStatus("Configura CONFIG.API_BASE", "error");
      return;
    }
    const email = loginEmail.value.trim();
    const password = loginPassword.value;
    if (!email || !password) {
      setStatus("Ingresa correo y contrasena", "error");
      return;
    }
    btnLogin.disabled = true;
    const params = new URLSearchParams();
    params.append("username", email);
    params.append("password", password);
    const resp = await fetch(`${API_BASE}/auth/token`, {
      method: "POST",
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
      body: params,
    });
    if (!resp.ok) {
      throw new Error("Credenciales invalidas");
    }
    const data = await resp.json();
    state.token = data.access_token;
    loginPassword.value = "";
    await loadProfile();
    setStatus("Sesion iniciada", "info");
  } catch (err) {
    console.error(err);
    setStatus(err.message || "No se pudo iniciar sesion", "error");
  } finally {
    btnLogin.disabled = false;
  }
}

async function loadProfile() {
  try {
    const user = await apiFetch("/users/me");
    state.user = user;
    authStatus.textContent = `Sesion activa: ${user.full_name} (${user.role})`;
    if (user.role === "doctor") {
      doctorAvailable.checked = Boolean(user.is_available);
      await refreshWaitingCalls();
    }
    updatePanels();
  } catch (err) {
    setStatus("No se pudo obtener el perfil", "error");
  }
}

function logout() {
  state.token = null;
  state.user = null;
  authStatus.textContent = "Ingresa tus credenciales para comenzar.";
  setStatus("Sesion cerrada", "info");
  resetCallState();
  updatePanels();
  waitingCalls.innerHTML = "";
  hangup();
}

async function requestCall() {
  try {
    if (!state.user || state.user.role !== "patient") {
      setStatus("Inicia sesion como paciente", "error");
      return;
    }
    if (state.currentCall && !["ended", "cancelled"].includes(state.currentCall.status)) {
      setStatus("Ya tienes una llamada activa", "error");
      return;
    }
    const note = patientNote.value.trim();
    const payload = {};
    if (note) payload.metadata = { note };
    const call = await apiFetch("/calls/request", { method: "POST", body: payload });
    assignCall(call);
    setStatus(`Consulta solicitada (#${call.id})`, "info");
  } catch (err) {
    setStatus(err.message || "No se pudo solicitar la llamada", "error");
  }
}

async function refreshWaitingCalls() {
  if (!state.user || state.user.role !== "doctor") return;
  try {
    const calls = await apiFetch("/calls/waiting");
    renderWaitingCalls(calls);
  } catch (err) {
    setStatus("No se pudieron obtener las llamadas en espera", "error");
  }
}

function renderWaitingCalls(calls = []) {
  if (!calls.length) {
    waitingCalls.innerHTML = "<p>No hay pacientes en espera.</p>";
    return;
  }
  waitingCalls.innerHTML = calls
    .map(
      (call) => `
      <div class="waiting-item">
        <div>
          <strong>ID ${call.id}</strong> | Room ${call.room_id} | Paciente ${call.patient_id}
        </div>
        <button data-call-id="${call.id}">Tomar llamada</button>
      </div>`
    )
    .join("\n");
}

async function claimCall(callId) {
  try {
    const call = await apiFetch(`/calls/${callId}/claim`, { method: "POST" });
    assignCall(call);
    setStatus(`Llamada ${call.id} asignada`, "info");
  } catch (err) {
    setStatus(err.message || "No se pudo asignar la llamada", "error");
  }
}

async function toggleDoctorAvailability(available) {
  if (!state.user || state.user.role !== "doctor") return;
  try {
    const user = await apiFetch("/users/me/availability", {
      method: "PATCH",
      body: { is_available: available },
    });
    state.user = user;
    setStatus(available ? "Marcado como disponible" : "Marcado como no disponible", "info");
  } catch (err) {
    setStatus("No se pudo actualizar disponibilidad", "error");
  }
}

async function handleStartVideo() {
  if (!state.currentCall) {
    setStatus("No hay llamada activa", "error");
    return;
  }
  if (state.user?.role === "patient" && !state.currentCall.doctor_id) {
    setStatus("Aun no hay medico conectado. Espera a que acepten tu llamada.", "error");
    return;
  }
  try {
    await apiFetch(`/calls/${state.currentCall.id}/start`, { method: "POST" });
    await fetchCurrentCall();
    await startCall();
    setStatus("Sesion WebRTC iniciada", "info");
  } catch (err) {
    console.error(err);
    setStatus(err.message || "No se pudo iniciar el video", "error");
  }
}

async function handleHangup() {
  try {
    await hangup();
    if (state.currentCall) {
      await apiFetch(`/calls/${state.currentCall.id}/end`, { method: "POST" });
      await fetchCurrentCall();
      setStatus("Llamada finalizada", "info");
    }
  } catch (err) {
    setStatus(err.message || "No se pudo finalizar la llamada", "error");
  }
}

waitingCalls.addEventListener("click", (ev) => {
  const target = ev.target.closest("button[data-call-id]");
  if (!target) return;
  claimCall(target.dataset.callId);
});

btnLogin.addEventListener("click", (ev) => {
  ev.preventDefault();
  handleLogin();
});

btnLogout.addEventListener("click", (ev) => {
  ev.preventDefault();
  logout();
});

btnRequestCall.addEventListener("click", (ev) => {
  ev.preventDefault();
  requestCall();
});

btnRefreshCalls.addEventListener("click", (ev) => {
  ev.preventDefault();
  refreshWaitingCalls();
});

doctorAvailable.addEventListener("change", (ev) => {
  toggleDoctorAvailability(ev.target.checked);
});

btnStart.addEventListener("click", (ev) => {
  ev.preventDefault();
  handleStartVideo();
});

btnHang.addEventListener("click", (ev) => {
  ev.preventDefault();
  handleHangup();
});

// -------------------------------------------------------------------
// WebRTC + Socket.IO (logic mostly from original client)
// -------------------------------------------------------------------

const btnStartLegacy = btnStart; // alias for readability inside startCall/hangup
const btnHangLegacy = btnHang;

let sio = null;
let pc = null;
let localStream = null;
let remoteStream = null;
let currentPeerSid = null;

const constraintsByRes = {
  qvga: { width: { exact: 320 }, height: { exact: 240 } },
  vga: { width: { exact: 640 }, height: { exact: 480 } },
  hd: { width: { exact: 1280 }, height: { exact: 720 } },
  fhd: { width: { exact: 1920 }, height: { exact: 1080 } },
};

function log(...args) {
  console.log("[VIDEOCALL]", ...args);
}

function preferCodec(sdp, codec) {
  if (!sdp || !codec) return sdp;
  const lines = sdp.split("\r\n");
  const rtpmap = lines.filter((l) => l.startsWith("a=rtpmap:"));
  const m = rtpmap.find((l) => l.toUpperCase().includes(codec.toUpperCase()));
  if (!m) return sdp;
  const pt = m.split(":")[1].split(" ")[0];
  const idx = lines.findIndex((l) => l.startsWith("m=video"));
  if (idx === -1) return sdp;
  const parts = lines[idx].split(" ");
  const header = parts.slice(0, 3);
  const payloads = parts.slice(3).filter((x) => x !== pt);
  lines[idx] = [...header, pt, ...payloads].join(" ");
  return lines.join("\r\n");
}

function relay(msg) {
  if (!sio) {
    console.warn("relay() llamado sin Socket.IO conectado");
    return;
  }
  log("relay ->", msg.type, "hacia", msg.to);
  sio.emit("relay", msg);
}

async function startCall() {
  if (!navigator.mediaDevices || !navigator.mediaDevices.getUserMedia) {
    alert("Tu navegador requiere HTTPS o localhost para usar camara y microfono.");
    return;
  }

  btnStartLegacy.disabled = true;
  btnHangLegacy.disabled = false;

  const roomId = roomInput.value || "demo-123";
  const resKey = el("resolution").value;
  const fps = parseInt(el("fps").value, 10) || 30;
  const codec = el("codec").value;
  const bitrateKbps = Math.max(150, parseInt(el("bitrate").value, 10) || 1200);

  try {
    const iceResp = await fetch(`${API_BASE}/ice`, {
      credentials: "include",
    });
    if (!iceResp.ok) {
      throw new Error(`ICE config HTTP ${iceResp.status}`);
    }
    const iceJson = await iceResp.json();
    const iceServers = iceJson.iceServers || [];

    const mediaConstraints = {
      video: {
        ...(constraintsByRes[resKey] || {}),
        frameRate: { ideal: fps, max: fps },
      },
      audio: true,
    };

    localStream = await navigator.mediaDevices.getUserMedia(mediaConstraints);
    const localVideo = el("local");
    localVideo.srcObject = localStream;
    try { await localVideo.play(); } catch (_) {}

    pc = new RTCPeerConnection({ iceServers });
    pc.oniceconnectionstatechange = () => {
      console.log("[VIDEOCALL] iceConnectionState =", pc.iceConnectionState);
    };
    pc.onconnectionstatechange = () => {
      console.log("[VIDEOCALL] connectionState =", pc.connectionState);
    };

    remoteStream = new MediaStream();
    const remoteVideo = el("remote");
    remoteVideo.autoplay = true;
    remoteVideo.playsInline = true;

    pc.ontrack = (ev) => {
      ev.streams[0].getTracks().forEach((t) => remoteStream.addTrack(t));
      remoteVideo.srcObject = remoteStream;
    };

    pc.onicecandidate = (ev) => {
      if (ev.candidate && currentPeerSid) {
        relay({ type: "candidate", payload: ev.candidate, to: currentPeerSid });
      }
    };

    localStream.getTracks().forEach((t) => pc.addTrack(t, localStream));

    const sender = pc
      .getSenders()
      .find((s) => s.track && s.track.kind === "video");

    if (sender) {
      const params = sender.getParameters();
      params.encodings = [
        {
          maxBitrate: bitrateKbps * 1000,
          maxFramerate: fps,
        },
      ];
      try {
        await sender.setParameters(params);
      } catch (e) {
        console.warn("No se pudieron ajustar parametros de envio:", e);
      }
    }

    sio = io(SIGNAL_URL, {
      path: "/socket.io",   // respeta el path del ASGIApp
      // Dejamos que Socket.IO haga su handshake normal:
      //   - primero polling
      //   - luego upgrade a websocket
      transports: ["polling", "websocket"],
      withCredentials: false,
      reconnectionAttempts: 3,
      timeout: 20000,
      // 👇 NO forzamos upgrade:false, que a veces rompe con proxies
      // upgrade: true (valor por defecto)
    });



    sio.on("connect_error", (err) => console.error("connect_error", err));
    sio.on("error", (err) => console.error("socket error", err));

    sio.on("connect", () => {
      log("Socket.IO conectado, sid:", sio.id);
      sio.emit("join", { room: roomId }, async (res) => {
        const peers = (res && res.peers) || [];
        if (peers.length) {
          currentPeerSid = peers[0];
          let offer = await pc.createOffer();
          offer.sdp = preferCodec(offer.sdp, codec);
          await pc.setLocalDescription(offer);
          relay({ type: "offer", to: currentPeerSid, payload: offer });
        }
      });
    });

    sio.on("peer-joined", async ({ sid }) => {
      log("peer-joined recibido:", sid);
      if (!pc.currentLocalDescription) {
        currentPeerSid = sid;
        let offer = await pc.createOffer();
        offer.sdp = preferCodec(offer.sdp, codec);
        await pc.setLocalDescription(offer);
        relay({ type: "offer", to: sid, payload: offer });
      }
    });

    sio.on("signal", async ({ from, type, payload }) => {
      log("signal recibido:", type, "de", from);
      currentPeerSid = from;
      try {
        if (type === "offer") {
          await pc.setRemoteDescription(payload);
          let answer = await pc.createAnswer();
          answer.sdp = preferCodec(answer.sdp, codec);
          await pc.setLocalDescription(answer);
          relay({ type: "answer", to: from, payload: answer });
        } else if (type === "answer") {
          await pc.setRemoteDescription(payload);
        } else if (type === "candidate") {
          await pc.addIceCandidate(payload);
        }
      } catch (err) {
        console.error("Error manejando senal", type, err);
      }
    });

    sio.on("disconnect", (reason) => log("Socket.IO desconectado:", reason));
  } catch (err) {
    console.error("Error en startCall:", err);
    alert("Error al iniciar la llamada: " + err.message);
    btnStartLegacy.disabled = false;
    btnHangLegacy.disabled = true;
  }
}

async function hangup() {
  btnStartLegacy.disabled = false;
  btnHangLegacy.disabled = true;

  try { sio && sio.disconnect(); } catch (_) {}
  try { pc && pc.close(); } catch (_) {}
  try {
    localStream && localStream.getTracks().forEach((t) => t.stop());
  } catch (_) {}

  pc = null;
  sio = null;
  localStream = null;
  remoteStream = null;

  const localVideo = el("local");
  const remoteVideo = el("remote");
  if (localVideo) localVideo.srcObject = null;
  if (remoteVideo) remoteVideo.srcObject = null;
}
