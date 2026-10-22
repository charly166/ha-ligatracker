/*
 * Team card for Home Assistant (shipped with the "HA Liga Tracker" integration).
 *
 *   type: custom:ligatracker-team-card
 *   entity: sensor.vfb_stuttgart_ubersicht   # the team's "Übersicht"/"Overview" sensor (required)
 *   name: VfB Stuttgart                      # optional, defaults to the team name
 *
 * Shows the team with logo, then its league (table position, last and next match) and
 * further competitions (cup, European cups) with the same details.
 */
(() => {
  const VERSION = "1";

  const TEXT = {
    de: {
      league: "Liga",
      other: "Weitere Wettbewerbe",
      last: "Letztes Spiel",
      next: "Nächstes Spiel",
      live: "Läuft",
      pos: "Platz",
      pts: "Pkt",
      none: "Kein Spiel angesetzt",
      noData: "Keine Daten",
      missing: "Entität nicht gefunden",
    },
    en: {
      league: "League",
      other: "Other competitions",
      last: "Last match",
      next: "Next match",
      live: "Live",
      pos: "Position",
      pts: "pts",
      none: "No match scheduled",
      noData: "No data",
      missing: "Entity not found",
    },
  };

  const CSS = `
    :host { display: block; }
    ha-card { padding: 12px 16px; }
    .team { display: flex; align-items: center; gap: 12px; margin-bottom: 4px; }
    .team img { width: 44px; height: 44px; object-fit: contain; flex: none; }
    .team .title { font-size: 1.3em; font-weight: 700; min-width: 0; overflow: hidden;
      text-overflow: ellipsis; white-space: nowrap; }
    .section-title { font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.04em;
      color: var(--secondary-text-color); margin: 16px 0 2px; }
    .comp { margin-top: 10px; padding-top: 10px; border-top: 1px solid var(--divider-color, #e0e0e0); }
    .team + .comp { border-top: none; padding-top: 0; margin-top: 6px; }
    .section-title + .comp { border-top: none; padding-top: 0; }
    .comp-head { display: flex; align-items: baseline; justify-content: space-between; gap: 8px; }
    .comp-name { font-weight: 600; font-size: 1.05em; }
    .table { color: var(--secondary-text-color); font-size: 0.9em; white-space: nowrap; }
    .table b { color: var(--primary-text-color); }
    .label { color: var(--secondary-text-color); font-size: 0.8em; margin-top: 8px; }
    .match { display: grid; grid-template-columns: 1fr auto 1fr; align-items: center; gap: 8px; margin-top: 2px; }
    .side { display: flex; align-items: center; gap: 6px; min-width: 0; }
    .side.home { justify-content: flex-end; text-align: right; }
    .side img { width: 24px; height: 24px; object-fit: contain; flex: none; }
    .side span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .side.me span { font-weight: 700; }
    .mid { min-width: 3.4em; text-align: center; font-weight: 700; }
    .mid.win { color: var(--success-color, #2e7d32); }
    .mid.loss { color: var(--error-color, #c62828); }
    .mid.draw { color: var(--warning-color, #ef6c00); }
    .mid.vs { font-weight: 400; color: var(--secondary-text-color); }
    .when { color: var(--secondary-text-color); font-size: 0.82em; text-align: center; margin-top: 1px; }
    .live { color: var(--error-color, #c62828); font-weight: 700; }
    .empty { color: var(--secondary-text-color); font-size: 0.9em; }
    .warn { color: var(--secondary-text-color); padding: 8px 0; }
  `;

  const esc = (v) =>
    String(v == null ? "" : v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  class LigaTrackerTeamCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
    }

    setConfig(config) {
      if (!config || !config.entity) {
        throw new Error("Bitte 'entity' (den Übersicht-Sensor der Mannschaft) angeben.");
      }
      this._config = config;
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }

    getCardSize() {
      const comps = (((this._state() || {}).attributes || {}).competitions || []).length;
      return 3 + comps * 3;
    }

    static getConfigForm() {
      return {
        schema: [
          { name: "entity", required: true, selector: { entity: { domain: "sensor", integration: "ligatracker" } } },
          { name: "name", selector: { text: {} } },
        ],
      };
    }

    static getStubConfig(hass) {
      const ent = Object.values(hass.entities || {}).find(
        (e) => e.platform === "ligatracker" && e.translation_key === "overview"
      );
      return { entity: ent ? ent.entity_id : "sensor.example_overview" };
    }

    _state() {
      return this._hass && this._config ? this._hass.states[this._config.entity] : undefined;
    }

    _t() {
      const lang = ((this._hass && this._hass.language) || "en").toLowerCase();
      return lang.startsWith("de") ? TEXT.de : TEXT.en;
    }

    _fmt(iso) {
      const hass = this._hass;
      try {
        return new Date(iso).toLocaleString((hass.locale && hass.locale.language) || hass.language, {
          weekday: "short",
          day: "2-digit",
          month: "2-digit",
          hour: "2-digit",
          minute: "2-digit",
          timeZone: hass.config && hass.config.time_zone,
        });
      } catch (e) {
        return iso;
      }
    }

    _logo(url) {
      return url
        ? `<img src="${esc(url)}" alt="" referrerpolicy="no-referrer" onerror="this.style.visibility='hidden'">`
        : `<img alt="" style="visibility:hidden">`;
    }

    // One match line: "[home] [logo]   score / -   [logo] [away]" plus a date line.
    _match(m, kind) {
      const t = this._t();
      const hasScore = m.score && m.score.length === 2;
      let mid;
      if (kind === "last" && hasScore) {
        mid = `<div class="mid ${esc(m.result || "")}">${m.score[0]}:${m.score[1]}</div>`;
      } else if (kind === "live" && hasScore) {
        mid = `<div class="mid live">${m.score[0]}:${m.score[1]}</div>`;
      } else if (kind === "live") {
        mid = `<div class="mid live">${esc(t.live)}</div>`;
      } else {
        mid = `<div class="mid vs">–</div>`;
      }
      const homeMe = m.team_is_home ? "me" : "";
      const awayMe = m.team_is_home ? "" : "me";
      const when = `${esc(this._fmt(m.kickoff))}${m.matchday ? " · " + esc(m.matchday) : ""}`;
      return `
        <div class="match">
          <div class="side home ${homeMe}"><span title="${esc(m.home)}">${esc(m.home_short || m.home)}</span>${this._logo(m.home_logo)}</div>
          ${mid}
          <div class="side away ${awayMe}">${this._logo(m.away_logo)}<span title="${esc(m.away)}">${esc(m.away_short || m.away)}</span></div>
        </div>
        <div class="when">${when}</div>`;
    }

    _competition(c, headline) {
      const t = this._t();
      const tab = c.table
        ? `<div class="table">${esc(t.pos)} <b>${c.table.position}</b> · ${c.table.points} ${esc(t.pts)}</div>`
        : "";
      const live = c.live ? `<div class="label live">${esc(t.live)}</div>${this._match(c.live, "live")}` : "";
      const last = c.last
        ? `<div class="label">${esc(t.last)}</div>${this._match(c.last, "last")}`
        : `<div class="label">${esc(t.last)}</div><div class="empty">${esc(t.none)}</div>`;
      const next = c.next
        ? `<div class="label">${esc(t.next)}</div>${this._match(c.next, "next")}`
        : c.live
          ? ""
          : `<div class="label">${esc(t.next)}</div><div class="empty">${esc(t.none)}</div>`;
      return `
        <div class="comp">
          <div class="comp-head"><div class="comp-name">${esc(headline)}</div>${tab}</div>
          ${live}${last}${next}
        </div>`;
    }

    _render() {
      if (!this._hass || !this._config) return;
      const t = this._t();
      const st = this._state();
      let body;
      if (!st) {
        body = `<div class="warn">${esc(t.missing)}: ${esc(this._config.entity)}</div>`;
      } else {
        const a = st.attributes || {};
        const team = a.team || {};
        const comps = a.competitions || [];
        const name = this._config.name || team.name || "";
        const leagues = comps.filter((c) => c.league);
        const others = comps.filter((c) => !c.league);
        const logo = team.logo
          ? `<img src="${esc(team.logo)}" alt="" referrerpolicy="no-referrer" onerror="this.style.display='none'">`
          : "";
        const head = `<div class="team">${logo}<div class="title">${esc(name)}</div></div>`;
        const leagueHtml = leagues.map((c) => this._competition(c, `${t.league}: ${c.name}`)).join("");
        const otherHtml = others.length
          ? `<div class="section-title">${esc(t.other)}</div>` + others.map((c) => this._competition(c, c.name)).join("")
          : "";
        body = head + (comps.length ? leagueHtml + otherHtml : `<div class="warn">${esc(t.noData)}</div>`);
      }
      this.shadowRoot.innerHTML = `<style>${CSS}</style><ha-card>${body}</ha-card>`;
    }
  }

  if (!customElements.get("ligatracker-team-card")) {
    customElements.define("ligatracker-team-card", LigaTrackerTeamCard);
  }

  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "ligatracker-team-card",
    name: "HA Liga Tracker Mannschaftskarte",
    description: "Mannschaft mit Logo, Liga und weitere Wettbewerbe mit Tabellenplatz, letztem und nächstem Spiel",
    preview: false,
  });
  console.info(`%c LIGATRACKER-TEAM-CARD %c v${VERSION}`, "color:white;background:#1b5e20", "");
})();
