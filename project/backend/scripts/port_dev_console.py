"""Port the interactive console to the new backend.

The console of the design backend (``project/design/test_voice.html``) is the
only interface of the five pillars.  It is ported here with the gamified path
removed (the milestones of the plan replaced it) and with the paths of the
new API.

Run it from the backend directory::

    python scripts/port_dev_console.py
"""

from __future__ import annotations

import re
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parent.parent
SOURCE = BACKEND_DIR.parent / "design" / "test_voice.html"
TARGET = BACKEND_DIR / "app" / "static" / "dev-console.html"


def _drop_section(html: str, section_id: str) -> str:
    """Remove a ``<section id="...">`` block."""
    pattern = re.compile(
        rf'\s*<section id="{re.escape(section_id)}".*?</section>', re.DOTALL
    )
    new_html, count = pattern.subn("", html, count=1)
    if count != 1:
        raise SystemExit(f"the section {section_id} was not found")
    return new_html


def _drop_function(html: str, name: str) -> str:
    """Remove a function and its body."""
    pattern = re.compile(rf"\n(?:async )?function {re.escape(name)}\(.*?\n\}}\n", re.DOTALL)
    new_html, count = pattern.subn("\n", html, count=1)
    if count != 1:
        raise SystemExit(f"the function {name} was not found")
    return new_html


def port(html: str) -> str:
    """Apply every change to the console."""
    # 1. The gamified path is gone.
    html = _drop_section(html, "tab-roadmap")
    html = _drop_function(html, "renderPathAndGoals")
    html = _drop_function(html, "completeLevel")
    html = _drop_function(html, "resetDemoProgress")

    # 2. The tab bar loses the path and is renumbered.
    html = html.replace(
        '<button class="tab-btn active" onclick="switchTab(\'roadmap\', this)">'
        "🗺️ 1. Mapa de Viaje y Micro-Victorias</button>\n    ",
        "",
    )
    html = html.replace(
        "⚡ 2. Laboratorio de Decisiones", "⚡ 1. Laboratorio de Decisiones"
    )
    html = html.replace("💡 3. Mentor Proactivo", "💡 2. Mentor Proactivo")
    html = html.replace("👨‍👩‍👧‍👦 4. Modo Multijugador", "👨‍👩‍👧‍👦 3. Modo Multijugador")
    html = html.replace("🎬 5. Vídeo Introductorio", "🎬 4. Vídeo Introductorio")
    html = html.replace(
        '["roadmap", "simulator", "jargon", "multiplayer", "story"]',
        '["simulator", "jargon", "multiplayer", "story"]',
    )
    html = html.replace(
        '<button class="tab-btn" onclick="switchTab(\'simulator\', this)">',
        '<button class="tab-btn active" onclick="switchTab(\'simulator\', this)">',
    )

    # 3. The header no longer announces the path.
    html = html.replace(
        "<p class=\"sub\">1. Mapa de Viaje · 2. Simulador What-If · 3. Micro-Victorias "
        "· 4. Mentor Proactivo y Jerga · 5. Modo Multijugador</p>",
        "<p class=\"sub\">1. Laboratorio de Decisiones · 2. Mentor Proactivo y Jerga "
        "· 3. Modo Multijugador · 4. Vídeo Introductorio</p>",
    )
    html = html.replace(
        '<a href="/prototype" target="_blank" style="text-decoration:none;">'
        "<button class=\"btn-secondary\">📱 Abrir Prototipo Móvil</button></a>\n    ",
        "",
    )

    # 4. The banner shows the score of the plan, without the route of the path.
    html = html.replace(
        '<div class="gps-text" id="gpsBannerText">🚗 Cargando ruta de la familia...</div>',
        '<div class="gps-text" id="gpsBannerText">🚗 Cargando el plan de la familia...</div>',
    )
    html = html.replace(
        '<button class="btn-secondary" onclick="resetDemoProgress()" '
        'title="Reiniciar niveles para repetir la demo">↺ Reiniciar Demo</button>',
        '<span class="badge badge-blue" id="planSourceBadge">Origen: --</span>',
    )
    html = html.replace(
        '<div id="celebrationBox" class="celebration-banner"></div>\n\n', ""
    )
    html = html.replace(
        '  $("celebrationBox").style.display = "none";\n', ""
    )

    # 5. The data of the couple comes from its own endpoint.
    html = html.replace(
        "let currentPathData = null, currentSimData = null, currentInsights = null, "
        "kidsViewActive = false;",
        "let currentCoupleData = null, currentSimData = null, currentInsights = null, "
        "currentStoryData = null, kidsViewActive = false;",
    )
    html = html.replace(
        """  const [pathRes, simRes, insRes, storyRes] = await Promise.all([
    fetch(`/api/path/${cid}`).then(r => r.json()),
    fetch(`/api/simulator/${cid}`).then(r => r.json()),
    fetch(`/api/mentor/insights/${cid}`).then(r => r.json()),
    fetch(`/api/story/${cid}`).then(r => r.json())
  ]);
  currentPathData = pathRes;
  currentSimData = simRes;
  currentInsights = insRes;

  renderPathAndGoals(pathRes);
  renderSimulator(simRes, true);
  renderInsightsAndJargon(insRes);
  renderMultiplayer(pathRes);
  renderStory(storyRes);""",
        """  const [coupleRes, simRes, insRes, storyRes] = await Promise.all([
    fetch(`/api/cases/${cid}/couple`).then(r => r.json()),
    fetch(`/api/cases/${cid}/simulator`).then(r => r.json()),
    fetch(`/api/cases/${cid}/mentor/insights`).then(r => r.json()),
    fetch(`/api/cases/${cid}/story`).then(r => r.json())
  ]);
  currentCoupleData = coupleRes;
  currentSimData = simRes;
  currentInsights = insRes;
  currentStoryData = storyRes;

  renderPlan(coupleRes);
  renderSimulator(simRes, true);
  renderInsightsAndJargon(insRes);
  renderMultiplayer(coupleRes);
  renderStory(storyRes);""",
    )

    # 6. The couple is rendered from the couple endpoint.
    html = html.replace(
        """function renderMultiplayer(pathData) {
  const c = pathData.couple_info;
  if (!c) return;""",
        """function renderMultiplayer(coupleData) {
  const c = coupleData;
  if (!c) return;""",
    )
    html = html.replace(
        """  $("membersGrid").innerHTML = (c.members || []).map(m => `""",
        """  $("membersGrid").innerHTML = (c.members || []).map(m => `""",
    )
    html = html.replace(
        """        <span><b>${hf.from_member}</b> → <b>${hf.to_member}</b> · ${hf.milestone_title}</span>
        <span>${hf.timestamp}</span>""",
        """        <span><b>${hf.from_member}</b> → <b>${hf.to_member}</b> · ${hf.milestone_title}</span>
        <span>${hf.created_at}</span>""",
    )
    html = html.replace(
        """      <div style="font-weight:750; font-size:15px;">${k.icono} ${k.titulo_amigable}</div>
      <div class="badge badge-mint" style="margin:6px 0;">${k.meta_visual}</div>
      <div class="progress-bar"><span style="width:${k.progreso_porcentaje}%"></span></div>
      <div style="font-size:13px;">${k.explicacion_ninos}</div>""",
        """      <div style="font-weight:750; font-size:15px;">${k.icon} ${k.friendly_title}</div>
      <div class="badge badge-mint" style="margin:6px 0;">${k.visual_meta}</div>
      <div class="progress-bar"><span style="width:${k.progress_percentage}%"></span></div>
      <div style="font-size:13px;">${k.children_explanation}</div>""",
    )
    html = html.replace(
        """  const members = (currentPathData?.couple_info?.members) || [];""",
        """  const members = (currentCoupleData?.members) || [];""",
    )
    html = html.replace(
        """      message: `¡Choca esos cinco, ${toM}! Revisé nuestro Mapa de Viaje y vamos por buen camino 👋`
    })
  });
  const updatedPath = await fetch(`/api/path/${cid}`).then(r => r.json());
  currentPathData = updatedPath;
  renderMultiplayer(updatedPath);""",
        """      message: `¡Choca esos cinco, ${toM}! Vamos por buen camino 👋`
    })
  });
  const updated = await fetch(`/api/cases/${cid}/couple`).then(r => r.json());
  currentCoupleData = updated;
  renderMultiplayer(updated);""",
    )

    # 7. The plan of the family is shown in the banner.
    html = html.replace(
        """function switchTab(tabName, btn) {""",
        """function renderPlan(coupleData) {
  const story = currentStoryData || {};
  $("gpsBannerText").textContent = story.main_challenge
    ? `🚗 ${story.main_challenge}`
    : "🚗 El plan de la familia está listo.";
  $("scorePill").textContent = `Score: ${story.score ?? "--"} / 100 (${story.band || "--"})`;
  $("planSourceBadge").textContent = `Registro: ${story.style_label || "--"}`;
  $("quickQuestions").innerHTML = (story.first_step_cta?.title
    ? [story.first_step_cta.title]
    : []
  ).map(q => `<button class="pill-btn" onclick="askMentorQuestion('${String(q).replace(/'/g, "\\\\'")}')">${q}</button>`).join("");
}

function switchTab(tabName, btn) {""",
    )

    # 8. The live voice runs on the same origin as the page.
    html = html.replace(
        '  const host = location.hostname || "127.0.0.1";\n'
        "  const wsUrl = `ws://${host}:8000/ws/voice/${cid}?model=${model}&style=${style}&partner=${partner}`;",
        '  const scheme = location.protocol === "https:" ? "wss" : "ws";\n'
        "  const wsUrl = `${scheme}://${location.host}/api/voice/ws/${cid}"
        "?model=${model}&style=${style}&partner=${partner}`;",
    )

    # 9. The mentor answers with `answer` and an audio file.
    html = html.replace(
        "    bubble.querySelector(\".content\").textContent = res.respuesta_ia;",
        "    bubble.querySelector(\".content\").textContent = res.answer || res.respuesta_ia;",
    )
    html = html.replace(
        '      body: JSON.stringify({ client_id: cid, question: q, style, partner })',
        '      body: JSON.stringify({ case_id: cid, question: q, style, partner })',
    )

    # 10. The households come from the API.
    html = html.replace(
        """        <option value="timothy-melanie-weah" selected>Timothy &amp; Melanie Weah (Pareja · Refranero)</option>
        <option value="daniel-emily-johnson">Daniel &amp; Emily Johnson (Pareja · Sencillo)</option>
        <option value="michael-carter">Michael Carter (Individual · Sencillo)</option>
        <option value="samantha-lewis">Samantha Lewis (Ejecutivo · Formal)</option>""",
        """        <option value="timothy-melanie-weah" selected>Cargando…</option>""",
    )
    html = html.replace(
        """updatePartnerOptions();
loadAllFamilyData();""",
        """loadHouseholds();

async function loadHouseholds() {
  try {
    const cases = await fetch("/api/cases").then(r => r.json());
    const select = $("caseSelect");
    select.innerHTML = cases.map(c =>
      `<option value="${c.case_id}">${c.household_name} (${c.is_couple ? "Pareja" : "Individual"} · ${c.voice_label})</option>`
    ).join("");
    await onFamilyChange();
  } catch (e) {
    $("gpsBannerText").textContent = "⚠️ El backend no responde.";
  }
}""",
    )

    # The partner options are read from the household itself.
    html = re.sub(
        r"const PARTNER_OPTIONS = \{.*?\n\};\n",
        "const PARTNER_OPTIONS = {};\n",
        html,
        flags=re.DOTALL,
    )
    html = html.replace(
        """function updatePartnerOptions() {
  const cid = $("caseSelect").value;
  const sel = $("partnerSelect");
  const opts = PARTNER_OPTIONS[cid] || [{ value: "auto", label: "Automático" }];
  sel.innerHTML = opts.map(o => `<option value="${o.value}">${o.label}</option>`).join("");
  $("lblPartner").textContent = sel.value;
}""",
        """function updatePartnerOptions() {
  const cid = $("caseSelect").value;
  const sel = $("partnerSelect");
  const members = (currentCoupleData?.members) || [];
  const opts = members.length >= 2
    ? [{ value: "both", label: "👫 Ambos (Mediador de pareja)" }].concat(
        members.map(m => ({ value: m.key, label: `👤 Habla ${m.name} (${m.risk_profile})` }))
      )
    : [{ value: "auto", label: "Automático" }];
  sel.innerHTML = opts.map(o => `<option value="${o.value}">${o.label}</option>`).join("");
  $("lblPartner").textContent = sel.value;
}""",
    )

    return html


def main() -> int:
    """Write the ported console."""
    html = SOURCE.read_text(encoding="utf-8")
    ported = port(html)
    TARGET.parent.mkdir(parents=True, exist_ok=True)
    TARGET.write_text(ported, encoding="utf-8")
    print(f"Wrote {TARGET.relative_to(BACKEND_DIR)} ({len(ported)} chars)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
