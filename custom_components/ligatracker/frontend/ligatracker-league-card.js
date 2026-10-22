/*
 * League card for Home Assistant (shipped with the "HA Liga Tracker" integration).
 *
 *   type: custom:ligatracker-league-card
 *   entity: sensor.bundesliga_spieltage   # the league's "Spieltage"/"Matchdays" sensor (required)
 *   matchday: next                        # next (default) | last
 *   name: Bundesliga                      # optional, defaults to the competition name
 *
 * Header: league logo and name. Below: all matches of the next or the last matchday,
 * grouped by day, with both teams' logos; results for played matches, kick-off time otherwise.
 */
(() => {
  const VERSION = "1";

  const TEXT = {
    de: {
      next: "Nächster Spieltag",
      last: "Letzter Spieltag",
      live: "Läuft",
      none: "Kein Spieltag verfügbar",
      missing: "Entität nicht gefunden",
    },
    en: {
      next: "Next matchday",
      last: "Last matchday",
      live: "Live",
      none: "No matchday available",
      missing: "Entity not found",
    },
  };

  const CSS = `
    :host { display: block; }
    ha-card { padding: 12px 16px; }
    .head { display: flex; align-items: center; gap: 12px; }
    .logo { flex: none; width: 64px; height: 44px; border-radius: 8px; background: #fff;
      display: flex; align-items: center; justify-content: center; padding: 4px; box-sizing: border-box; }
    .logo img { max-width: 100%; max-height: 100%; object-fit: contain; }
    .titles { min-width: 0; }
    .title { font-size: 1.3em; font-weight: 700; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .sub { color: var(--secondary-text-color); font-size: 0.9em; }
    .day { color: var(--secondary-text-color); font-size: 0.8em; text-transform: uppercase;
      letter-spacing: 0.04em; margin: 14px 0 4px; }
    .match { display: grid; grid-template-columns: 1fr 3.6em 1fr; align-items: center; gap: 8px; padding: 3px 0; }
    .side { display: flex; align-items: center; gap: 6px; min-width: 0; }
    .side.home { justify-content: flex-end; text-align: right; }
    .side img { width: 24px; height: 24px; object-fit: contain; flex: none; }
    .side span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
    .mid { text-align: center; font-weight: 700; white-space: nowrap; }
    .mid.time { font-weight: 400; color: var(--secondary-text-color); }
    .mid.live { color: var(--error-color, #c62828); }
    .empty, .warn { color: var(--secondary-text-color); padding: 8px 0; }
  `;

  const esc = (v) =>
    String(v == null ? "" : v).replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  class LigaTrackerLeagueCard extends HTMLElement {
    constructor() {
      super();
      this.attachShadow({ mode: "open" });
    }

    setConfig(config) {
      if (!config || !config.entity) {
        throw new Error("Bitte 'entity' (den Spieltage-Sensor der Liga) angeben.");
      }
      if (config.matchday && !["next", "last"].includes(config.matchday)) {
        throw new Error("'matchday' muss 'next' oder 'last' sein.");
      }
      this._config = config;
    }

    set hass(hass) {
      this._hass = hass;
      this._render();
    }

    getCardSize() {
      const a = (this._state() || {}).attributes || {};
      const day = a[this._which()] || {};
      return 2 + (day.matches || []).length;
    }

    static getConfigForm() {
      return {
        schema: [
          { name: "entity", required: true, selector: { entity: { domain: "sensor", integration: "ligatracker" } } },
          {
            name: "matchday",
            selector: {
              select: {
                mode: "dropdown",
                options: [
                  { value: "next", label: "Nächster Spieltag" },
                  { value: "last", label: "Letzter Spieltag" },
                ],
              },
            },
          },
          { name: "name", selector: { text: {} } },
        ],
        computeLabel: (schema) => ({ entity: "Entität (Spieltage-Sensor)", matchday: "Spieltag", name: "Name" }[schema.name]),
      };
    }

    static getStubConfig(hass) {
      const ent = Object.values(hass.entities || {}).find(
        (e) => e.platform === "ligatracker" && e.translation_key === "league_overview"
      );
      return { entity: ent ? ent.entity_id : "sensor.example_matchdays", matchday: "next" };
    }

    _which() {
      return (this._config && this._config.matchday) === "last" ? "last" : "next";
    }

    _state() {
      return this._hass && this._config ? this._hass.states[this._config.entity] : undefined;
    }

    _t() {
      const lang = ((this._hass && this._hass.language) || "en").toLowerCase();
      return lang.startsWith("de") ? TEXT.de : TEXT.en;
    }

    _locale() {
      const hass = this._hass;
      return (hass.locale && hass.locale.language) || hass.language;
    }

    _dayKey(iso) {
      try {
        return new Date(iso).toLocaleDateString(this._locale(), {
          weekday: "short",
          day: "2-digit",
          month: "2-digit",
          timeZone: this._hass.config && this._hass.config.time_zone,
        });
      } catch (e) {
        return iso;
      }
    }

    _time(iso) {
      try {
        return new Date(iso).toLocaleTimeString(this._locale(), {
          hour: "2-digit",
          minute: "2-digit",
          timeZone: this._hass.config && this._hass.config.time_zone,
        });
      } catch (e) {
        return "";
      }
    }

    // The league's image entity (same device as the sensor) is served by Home Assistant itself,
    // which is more reliable than hot-linking; fall back to the plain URL otherwise.
    _leagueLogo(comp) {
      const hass = this._hass;
      const ents = hass.entities || {};
      const me = ents[this._config.entity];
      if (me && me.device_id) {
        const img = Object.values(ents).find((e) => e.device_id === me.device_id && e.translation_key === "league_logo");
        const st = img && hass.states[img.entity_id];
        if (st && st.attributes && st.attributes.entity_picture) return st.attributes.entity_picture;
      }
      return comp.logo;
    }

    _logo(url) {
      return url
        ? `<img src="${esc(url)}" alt="" referrerpolicy="no-referrer" onerror="this.style.visibility='hidden'">`
        : `<img alt="" style="visibility:hidden">`;
    }

    _match(m) {
      const t = this._t();
      const hasScore = m.score && m.score.length === 2;
      let mid;
      if (m.live) {
        mid = `<div class="mid live" title="${esc(t.live)}">${hasScore ? `${m.score[0]}:${m.score[1]}` : esc(t.live)}</div>`;
      } else if (m.finished && hasScore) {
        mid = `<div class="mid">${m.score[0]}:${m.score[1]}</div>`;
      } else {
        mid = `<div class="mid time">${esc(this._time(m.kickoff))}</div>`;
      }
      return `
        <div class="match">
          <div class="side home"><span title="${esc(m.home)}">${esc(m.home_short || m.home)}</span>${this._logo(m.home_logo)}</div>
          ${mid}
          <div class="side away">${this._logo(m.away_logo)}<span title="${esc(m.away)}">${esc(m.away_short || m.away)}</span></div>
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
        const comp = a.competition || {};
        const which = this._which();
        const day = a[which];
        const name = this._config.name || comp.name || "";
        const logoUrl = this._leagueLogo(comp);
        const logo = logoUrl
          ? `<div class="logo"><img src="${esc(logoUrl)}" alt="" referrerpolicy="no-referrer" onerror="this.parentNode.style.display='none'"></div>`
          : "";
        const sub = `${esc(t[which])}${day && day.name ? " · " + esc(day.name) : ""}`;
        const head = `<div class="head">${logo}<div class="titles"><div class="title">${esc(name)}</div><div class="sub">${sub}</div></div></div>`;
        let list = "";
        if (day && day.matches && day.matches.length) {
          let lastDay = null;
          for (const m of day.matches) {
            const key = this._dayKey(m.kickoff);
            if (key !== lastDay) {
              list += `<div class="day">${esc(key)}</div>`;
              lastDay = key;
            }
            list += this._match(m);
          }
        } else {
          list = `<div class="empty">${esc(t.none)}</div>`;
        }
        body = head + list;
      }
      this.shadowRoot.innerHTML = `<style>${CSS}</style><ha-card>${body}</ha-card>`;
    }
  }

  if (!customElements.get("ligatracker-league-card")) {
    customElements.define("ligatracker-league-card", LigaTrackerLeagueCard);
  }

  window.customCards = window.customCards || [];
  window.customCards.push({
    type: "ligatracker-league-card",
    name: "HA Liga Tracker Ligakarte",
    description: "Liga mit Logo und allen Partien des nächsten oder letzten Spieltags",
    preview: false,
  });
  console.info(`%c LIGATRACKER-LEAGUE-CARD %c v${VERSION}`, "color:white;background:#1b5e20", "");
})();
