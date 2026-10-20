(() => {
  const cache = new Map();
  const pending = new Set();

  const esc = value => escapeHtml(String(value ?? ""));

  const valid = value =>
    value !== null &&
    value !== undefined &&
    Number.isFinite(Number(value));

  const pct = value =>
    valid(value) ? `${Number(value).toFixed(1)}%` : "No data";

  const colors = [
    "var(--accent-primary)",
    "var(--accent-ocean)"
  ];

  const sourceNames = {
    qilt_ses_2025: "QILT 2025",
    study_australia_2025: "Study Australia 2025",
    daad_bintho_2023_24: "DAAD BintHo 2023/24",
    jasso_lifestyle_2023: "JASSO 2023",
    sesaba_2022: "SeSaBa 2022 - not loaded"
  };

  function confidenceInterval(row) {
    if (!valid(row.ci_lower_pct) || !valid(row.ci_upper_pct)) {
      return "";
    }

    return `${Number(row.ci_level) * 100}% CI: ` +
      `${pct(row.ci_lower_pct)} - ${pct(row.ci_upper_pct)}`;
  }

  function sourceLink(row) {
    const name = esc(
      sourceNames[row.source_id] || row.source_id
    );

    if (!/^https?:\/\//i.test(row.source_url || "")) {
      return name;
    }

    return `
      <a href="${esc(row.source_url)}"
         target="_blank"
         rel="noopener noreferrer">
        ${name}
      </a>
    `;
  }

  function renderChart(title, rows) {
    const indicators = new Map();

    for (const row of rows) {
      if (!indicators.has(row.indicator_code)) {
        indicators.set(row.indicator_code, []);
      }

      indicators.get(row.indicator_code).push(row);
    }

    const groups = [
      ...new Set(rows.map(row => row.group_label))
    ].sort();

    const body = [...indicators.values()].map(items => `
      <div style="margin:1rem 0">
        <div style="
          font-size:.85rem;
          font-weight:600;
          margin-bottom:.4rem">
          ${esc(items[0].indicator_label)}
        </div>

        ${items.map(row => {
          const width = valid(row.value_pct)
            ? Math.max(0, Math.min(100, Number(row.value_pct)))
            : 0;

          const color = colors[
            Math.max(0, groups.indexOf(row.group_label)) %
            colors.length
          ];

          return `
            <div style="margin:.4rem 0"
                 title="${esc(confidenceInterval(row))}">
              ${items.length > 1 ? `
                <div style="
                  font-size:.75rem;
                  color:var(--text-muted)">
                  ${esc(row.group_label)}
                </div>
              ` : ""}

              <div style="
                display:flex;
                align-items:center;
                gap:.5rem">
                <div style="
                  flex:1;
                  height:12px;
                  background:var(--bg-primary);
                  border-radius:3px">
                  <div style="
                    width:${width}%;
                    height:100%;
                    border-radius:3px;
                    background:${color}">
                  </div>
                </div>

                <span style="
                  min-width:48px;
                  text-align:right;
                  font-size:.8rem">
                  ${pct(row.value_pct)}
                </span>
              </div>
            </div>
          `;
        }).join("")}
      </div>
    `).join("");

    return `
      <div class="pbi-chart-visual">
        <div class="pbi-chart-header">
          <div class="pbi-chart-title">${esc(title)}</div>
        </div>
        ${body || "<p>No data available.</p>"}
      </div>
    `;
  }

  function render() {
    const item = cache.get(pbiSelectedDestination);

    const button = `
      <button type="button"
              onclick="refreshDestinationDashboard()">
        Refresh data
      </button>
    `;

    if (!item?.result) {
      return `
        <div class="pbi-chart-visual">
          <p>
            ${item?.error
              ? "Destination API is unavailable. Please retry."
              : "Loading destination data..."}
          </p>
          ${button}
        </div>
      `;
    }

    const result = item.result;
    const data = result.data;

    const time = new Date(result.data_as_of).toLocaleString(
      "en-GB",
      { timeZone: "Asia/Ho_Chi_Minh" }
    );

    return `
      <p style="font-size:.8rem;color:var(--text-muted)">
        Prepared: ${esc(time)} (Vietnam time)
        ${button}
      </p>

      ${item.error ? `
        <p>Refresh failed. Showing previously loaded data.</p>
      ` : ""}

      <div class="pbi-cards-grid">
        ${data.cards.map(row => `
          <div class="pbi-card-visual">
            <div class="pbi-card-callout">
              ${pct(row.value_pct)}
            </div>
            <div class="pbi-card-label">
              ${esc(row.card_label)}
            </div>
            <div style="
              font-size:.72rem;
              color:var(--text-muted);
              margin-top:.5rem">
              ${sourceLink(row)}<br>
              ${esc(row.home_group)}
              ${confidenceInterval(row)
                ? `<br>${esc(confidenceInterval(row))}`
                : ""}
            </div>
          </div>
        `).join("")}
      </div>

      <div class="pbi-charts-grid" style="margin-top:1rem">
        ${renderChart(
          data.config.left_title,
          data.charts.filter(row => row.panel === "left")
        )}
        ${renderChart(
          data.config.right_title,
          data.charts.filter(row => row.panel === "right")
        )}
      </div>

      <p style="
        font-size:.8rem;
        color:var(--text-muted);
        margin-top:1rem">
        ${esc(data.config.note)}
      </p>
    `;
  }

  async function load(country) {
    if (pending.has(country)) return;

    pending.add(country);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort(), 15000);

    try {
      const base = typeof API_BASE !== "undefined"
        ? API_BASE
        : "http://localhost:8000/api/v1";

      const response = await fetch(
        `${base}/dashboard/destinations?country=` +
        encodeURIComponent(country),
        {
          cache: "no-store",
          signal: controller.signal
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      if (
        result.country_code !== country ||
        result.data?.cards?.length !== 4 ||
        !Array.isArray(result.data?.charts)
      ) {
        throw new Error("Invalid destination response");
      }

      cache.set(country, { result, error: null });

      AISC_DASHBOARD_DATA.destinationConfig =
        result.data.countries;
    } catch (error) {
      cache.set(country, {
        ...cache.get(country),
        error: String(error)
      });

      console.error("Destination dashboard:", error);
    } finally {
      clearTimeout(timer);
      pending.delete(country);

      if (
        pbiCurrentPage === 2 &&
        pbiSelectedDestination === country
      ) {
        renderPowerBIDashboard();
      }
    }
  }

  renderDestinationPage = render;

  selectPbiDestination = country => {
    pbiSelectedDestination = country;
    renderPowerBIDashboard();
    load(country);
  };

  window.refreshDestinationDashboard = () =>
    load(pbiSelectedDestination);

  document.addEventListener("DOMContentLoaded", () =>
    load(pbiSelectedDestination)
  );
})();