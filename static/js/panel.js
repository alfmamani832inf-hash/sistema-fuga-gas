/* =====================================================================
   Panel de monitoreo (M6).
   JavaScript puro, sin frameworks (RNF06).
   ===================================================================== */

const INTERVALO_MS = 2000;
const TIMEOUT_CONEXION_MS = 5000;

let ultimoEstado = null;
let ultimoDatoBueno = null;
let fallosConsecutivos = 0;
let audioCtx = null;
let oscilador = null;
let ganancia = null;

// --- Referencias DOM ---
const $ = (id) => document.getElementById(id);
const tarjetaEstado = $("tarjeta-estado");
const estadoTexto = $("estado-texto");
const estadoDesc = $("estado-descripcion");
const led = $("led");
const medidorBarra = $("medidor-barra");
const medidorValor = $("medidor-valor");
const diagnostico = $("diagnostico");
const valvulaEstado = $("valvula-estado");
const valvulaDetalle = $("valvula-detalle");
const temperatura = $("temperatura");
const humedad = $("humedad");
// const fuente = $("fuente"); // <- Eliminado porque ya no está en el HTML
const escenario = $("escenario");
const tablaEventos = $("tabla-eventos-cuerpo");
const badgeConexion = $("badge-conexion");
const pieConexion = $("pie-conexion");

// ---------------------------------------------------------------------------
// Audio de alarma (Web Audio API)
// ---------------------------------------------------------------------------
function iniciarAudio() {
  if (audioCtx) return;
  try {
    audioCtx = new (window.AudioContext || window.webkitAudioContext)();
  } catch (e) {
    console.warn("Web Audio no disponible:", e);
  }
}

function pararSonido() {
  if (oscilador) {
    try { oscilador.stop(); } catch (e) {}
    oscilador = null;
  }
  if (ganancia) { ganancia = null; }
}

function reproducirSonido(frecuencia, patron) {
  if (!audioCtx) return;
  pararSonido();
  if (patron === "silencio" || frecuencia <= 0) return;

  oscilador = audioCtx.createOscillator();
  ganancia = audioCtx.createGain();
  oscilador.type = "square";
  oscilador.frequency.value = frecuencia;
  ganancia.gain.value = 0.03;
  oscilador.connect(ganancia).connect(audioCtx.destination);
  oscilador.start();

  if (patron === "intermitente") {
    const periodo = 0.25;
    const ahora = audioCtx.currentTime;
    for (let t = 0; t < 4; t += periodo * 2) {
      ganancia.gain.setValueAtTime(0.0, ahora + t);
      ganancia.gain.setValueAtTime(0.06, ahora + t + periodo);
    }
  } else if (patron === "largo") {
    ganancia.gain.value = 0.08;
  } else if (patron === "pitido") {
    const periodo = 2.0;
    const ahora = audioCtx.currentTime;
    for (let t = 0; t < 10; t += periodo) {
      ganancia.gain.setValueAtTime(0.0, ahora + t);
      ganancia.gain.setValueAtTime(0.05, ahora + t + 0.2);
      ganancia.gain.setValueAtTime(0.0, ahora + t + 0.5);
    }
  }
}

// ---------------------------------------------------------------------------
// Renderizado del estado
// ---------------------------------------------------------------------------
function claseEstado(estado) {
  return "tarjeta-estado estado-" + estado.toLowerCase();
}

function claseLed(color, patron) {
  let clases = "led led-" + color;
  if (patron === "parpadeante") clases += " led-parpadeante";
  return clases;
}

function pintarEstado(datos) {
  const estado = datos.estado;
  const alarma = datos.alarma || {};

  tarjetaEstado.className = claseEstado(estado);
  estadoTexto.textContent = estado;
  estadoDesc.textContent = alarma.descripcion || "";

  led.className = claseLed(alarma.color_led || "apagado", alarma.patron_led || "apagado");

  // Medidor
  const valor = datos.valor_mq2;
  if (valor === null || valor === undefined) {
    medidorBarra.style.width = "0%";
    medidorValor.textContent = "—";
  } else {
    const pct = Math.max(0, Math.min(100, (valor / 1000) * 100));
    medidorBarra.style.width = pct + "%";
    medidorValor.textContent = valor.toFixed(1) + " / 1000";
  }

  // Diagnóstico
  if (datos.diagnostico && datos.diagnostico.componentes) {
    diagnostico.innerHTML = datos.diagnostico.componentes.map(function (c) {
      const ok = c.operativo ? "diag-ok" : "diag-error";
      const icono = c.operativo ? "✓" : "✗";
      return '<li><span class="diag-icono ' + ok + '">' + icono + '</span> '
        + c.nombre + ': ' + c.detalle + '</li>';
    }).join("");
  }

  // Válvula
  const v = datos.valvula || {};
  valvulaEstado.textContent = datos.valvula_estado_reportado || "—";
  if (v.orden) {
    valvulaDetalle.textContent = v.orden + " → " + v.estado_reportado
      + (v.confirmado === false ? " (NO confirmado)" : " (confirmado)");
  } else {
    valvulaDetalle.textContent = "—";
  }

  // Ambiente
  temperatura.textContent = (datos.temperatura ?? "—") + " °C";
  humedad.textContent = (datos.humedad ?? "—") + " %";
  // fuente.textContent = datos.fuente || "—"; // <- Oculto, no se pinta en el HTML
  escenario.textContent = datos.escenario || "—";

  // Sonido
  if (alarma.sonido && alarma.sonido !== "silencio") {
    iniciarAudio();
    reproducirSonido(alarma.frecuencia_sonido_hz || 880, alarma.sonido);
  } else {
    pararSonido();
  }
}

function pintarEventos(eventos) {
  if (!eventos || eventos.length === 0) {
    tablaEventos.innerHTML = '<tr><td colspan="3" class="vacio">Sin eventos registrados.</td></tr>';
    return;
  }
  tablaEventos.innerHTML = eventos.map(function (e) {
    const fecha = e.fecha_hora ? e.fecha_hora.replace("T", " ").slice(0, 19) : "";
    return '<tr>'
      + '<td>' + fecha + '</td>'
      + '<td><span class="estado-tag estado-tag-' + e.estado + '">' + e.estado + '</span></td>'
      + '<td>' + (e.descripcion || "") + '</td>'
      + '</tr>';
  }).join("");
}

function pintarConexion(conectado) {
  if (conectado) {
    badgeConexion.textContent = "Conectado";
    badgeConexion.className = "badge badge-ok";
    pieConexion.textContent = "Conectado";
  } else {
    badgeConexion.textContent = "NO ACTUALIZADO";
    badgeConexion.className = "badge badge-off";
    pieConexion.textContent = "NO ACTUALIZADO";
    tarjetaEstado.className = "tarjeta-estado estado-no_actualizado";
    estadoDesc.textContent = "Último dato conocido (sin actualización).";
    pararSonido();
  }
}

// ---------------------------------------------------------------------------
// Ciclo de actualización
// ---------------------------------------------------------------------------
async function consultarEstado() {
  try {
    const control = new AbortController();
    const timeout = setTimeout(function () { control.abort(); }, TIMEOUT_CONEXION_MS);

    const respuesta = await fetch("/api/estado", { signal: control.signal });
    clearTimeout(timeout);

    if (!respuesta.ok) throw new Error("HTTP " + respuesta.status);
    const datos = await respuesta.json();

    ultimoDatoBueno = datos;
    fallosConsecutivos = 0;
    pintarConexion(true);
    pintarEstado(datos);
  } catch (e) {
    fallosConsecutivos++;
    console.warn("Fallo consulta #" + fallosConsecutivos, e);
    if (fallosConsecutivos >= 1) {
      pintarConexion(false);
      if (ultimoDatoBueno) pintarEstado(ultimoDatoBueno);
    }
  }
}

async function consultarEventos() {
  try {
    const respuesta = await fetch("/api/eventos?limite=10");
    if (!respuesta.ok) return;
    const datos = await respuesta.json();
    pintarEventos(datos.eventos);
  } catch (e) {
    // silencioso
  }
}

// ---------------------------------------------------------------------------
// Acciones
// ---------------------------------------------------------------------------
async function forzarEscenario(nombre) {
  try {
    const r = await fetch("/api/escenario", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ escenario: nombre }),
    });
    if (!r.ok) {
      const err = await r.json();
      alert("Error: " + (err.error || "no se pudo forzar el escenario"));
    }
    await consultarEstado();
    await consultarEventos();
  } catch (e) {
    alert("Error de red: " + e.message);
  }
}

async function reabrirValvula() {
  if (!confirm("¿Reabrir la válvula manualmente? Solo debe hacerlo el administrador.")) return;
  try {
    const r = await fetch("/api/valvula/reabrir", { method: "POST" });
    const datos = await r.json();
    if (!datos.confirmado) {
      alert("No se pudo reabrir: " + datos.razon);
    }
    await consultarEstado();
    await consultarEventos();
  } catch (e) {
    alert("Error de red: " + e.message);
  }
}

// ---------------------------------------------------------------------------
// Inicio
// ---------------------------------------------------------------------------
document.addEventListener("DOMContentLoaded", function () {
  // Un click en cualquier parte activa el audio (política del navegador).
  document.body.addEventListener("click", iniciarAudio, { once: true });

  // Botones de escenarios
  document.querySelectorAll("[data-escenario]").forEach(function (boton) {
    boton.addEventListener("click", function () {
      forzarEscenario(boton.dataset.escenario);
    });
  });

  // Botón reabrir
  const btnReabrir = $("btn-reabrir");
  if (btnReabrir) btnReabrir.addEventListener("click", reabrirValvula);

  // Primera consulta inmediata
  consultarEstado();
  consultarEventos();

  // Polling
  setInterval(consultarEstado, INTERVALO_MS);
  setInterval(consultarEventos, INTERVALO_MS * 3);
});