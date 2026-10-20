(() => {
  const cache = new Map();
  const pending = new Set();

  const colors = [
    'var(--accent-primary)',
    'var(--accent-ocean)',
    '#94A3B8'
  ];

  const escape = value => escapeHtml(String(value ?? ''));

  const valid = value =>
    value !== null &&
    value !== undefined &&
    Number.isFinite(Number(value));

  const pct = value =>
    valid(value)
      ? `${Number(value).toFixed(1)}%`
      : 'No data';

  const panel = (title, body) => `
    <div class="pbi-chart-visual">
      <div class="pbi-chart-header">
        <div class="pbi-chart-title">${escape(title)}</div>
      </div>
      ${body}
    </div>
  `;

  function services(rows) {
    const grouped = new Map();

    for (const row of rows) {
      if (!grouped.has(row.service_code)) {
        grouped.set(row.service_code, []);
      }

      grouped.get(row.service_code).push(row);
    }

    const legend = `
      <p style="font-size:.8rem;color:var(--text-muted)">
        Used · Aware, not used · Never heard of
      </p>
    `;

    const body = [...grouped.values()].map(group => {
      const states = [2, 1, 3].map(code =>
        group.find(row => row.state_code === code)
      );

      const complete = states.every(
        row => row && valid(row.value_pct)
      );

      const breakdown = complete ? `
        <div style="
          display:flex;
          height:28px;
          border-radius:4px;
          overflow:hidden;
          background:var(--bg-primary)
        ">
          ${states.map((row, i) => `
            <div
              title="${escape(row.state_label)}: ${pct(row.value_pct)}"
              style="
                width:${Math.max(
                  0,
                  Math.min(100, Number(row.value_pct))
                )}%;
                background:${colors[i]};
                display:flex;
                align-items:center;
                justify-content:center;
                color:#071C15;
                font-size:.75rem
              "
            >
              ${Number(row.value_pct) >= 9 ? pct(row.value_pct) : ''}
            </div>
          `).join('')}
        </div>
      ` : `
        <p style="color:var(--text-muted)">
          No complete breakdown available.
        </p>
      `;

      const stateNames = [
        'Used',
        'Aware, not used',
        'Never heard of'
      ];

      return `
        <div style="margin:1rem 0">
          <div style="margin-bottom:.4rem">
            ${escape(group[0].service_label)}
          </div>

          ${breakdown}

          <div style="
            font-size:.75rem;
            margin-top:.3rem;
            color:var(--text-muted)
          ">
            ${states.map((row, i) =>
              `${stateNames[i]}: ${pct(row?.value_pct)}`
            ).join(' · ')}
          </div>
        </div>
      `;
    }).join('');

    return legend + (body || '<p>No data available.</p>');
  }

  function bar(value, color) {
    if (!valid(value)) {
      return '<span style="color:var(--text-muted)">No data</span>';
    }

    const width = Math.max(
      0,
      Math.min(100, Number(value))
    );

    return `
      <div style="display:flex;align-items:center;gap:.5rem">
        <div style="
          flex:1;
          background:var(--bg-primary);
          height:12px;
          border-radius:3px
        ">
          <div style="
            width:${width}%;
            height:100%;
            background:${color};
            border-radius:3px
          "></div>
        </div>

        <span style="min-width:48px;text-align:right">
          ${pct(value)}
        </span>
      </div>
    `;
  }

  function benchmarks(rows, country) {
    return rows.map(row => `
      <div style="margin:1rem 0">
        <div style="margin-bottom:.4rem">
          ${escape(row.metric_label)}
        </div>

        <div style="font-size:.75rem;margin-bottom:.25rem">
          ${escape(country)}
        </div>

        ${bar(row.value_pct, colors[0])}

        <div style="font-size:.75rem;margin:.4rem 0 .25rem">
          Country median (n = ${escape(row.available_country_count)})
        </div>

        ${bar(row.median_pct, colors[1])}
      </div>
    `).join('') || '<p>No data available.</p>';
  }

  function render() {
    const current = cache.get(pbiSelectedCountry);

    const button = `
      <button type="button" onclick="refreshExternalOverview()">
        Refresh data
      </button>
    `;

    if (!current?.result) {
      return panel(
        'External Overview',
        `
          <p>${
            current?.error
              ? 'External data API is unavailable. Please retry.'
              : 'Loading external data…'
          }</p>
          ${button}
        `
      );
    }

    const result = current.result;
    const data = result.data;

    const country = data.countries.find(
      row => row.country_code === result.country_code
    )?.country_name || result.country_code;

    const prepared = new Date(result.data_as_of).toLocaleString(
      'en-GB',
      { timeZone: 'Asia/Ho_Chi_Minh' }
    );

    return `
      <div style="
        color:var(--text-muted);
        font-size:.8rem;
        margin-bottom:1rem
      ">
        EUROSTUDENT 8 · All students ·
        Prepared: ${escape(prepared)} (Vietnam time)
        · ${button}

        ${
          current.error
            ? '<p>Refresh failed. Showing previously loaded data.</p>'
            : ''
        }
      </div>

      <div class="pbi-cards-grid">
        ${data.cards.map(card => `
          <div class="pbi-card-visual">
            <div class="pbi-card-callout">
              ${pct(card.value_pct)}
            </div>
            <div class="pbi-card-label">
              ${escape(card.card_label)}
            </div>
          </div>
        `).join('')}
      </div>

      <div class="pbi-charts-grid" style="margin-top:1rem">
        ${panel(
          'Awareness and Use of Counselling Services',
          services(data.services)
        )}

        ${panel(
          'Selected Country vs Country Median',
          benchmarks(data.benchmarks, country)
        )}
      </div>

      <p style="
        font-size:.8rem;
        color:var(--text-muted);
        margin-top:1rem
      ">
        Percentages refer to survey respondents in each country.
        The median gives each available country equal weight.

        <a
          href="https://database.eurostudent.eu/drm/"
          target="_blank"
          rel="noopener noreferrer"
        >Source: EUROSTUDENT 8</a>
      </p>
    `;
  }

  async function load(country) {
    if (pending.has(country)) return;

    pending.add(country);

    const controller = new AbortController();

    const timer = setTimeout(
      () => controller.abort(),
      15000
    );

    try {
      const base = typeof API_BASE !== 'undefined'
        ? API_BASE
        : 'http://localhost:8000/api/v1';

      const response = await fetch(
        `${base}/dashboard/external-overview?country=${
          encodeURIComponent(country)
        }`,
        {
          cache: 'no-store',
          signal: controller.signal
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      if (
        result.country_code !== country ||
        !result.data?.cards ||
        !result.data?.countries
      ) {
        throw new Error('Invalid external overview response');
      }

      cache.set(country, {
        result,
        error: null
      });

      AISC_DASHBOARD_DATA.overviewCountries = result.data.countries;
    } catch (error) {
      cache.set(country, {
        ...cache.get(country),
        error: String(error)
      });

      console.error('External Overview:', error);
    } finally {
      clearTimeout(timer);
      pending.delete(country);

      if (
        pbiCurrentPage === 1 &&
        pbiSelectedCountry === country
      ) {
        renderPowerBIDashboard();
      }
    }
  }

  pbiSelectedCountry = 'DK';

  renderOverviewPage = render;

  selectPbiCountry = country => {
    pbiSelectedCountry = country;
    renderPowerBIDashboard();
    load(country);
  };

  window.refreshExternalOverview = () =>
    load(pbiSelectedCountry);

  document.addEventListener(
    'DOMContentLoaded',
    () => load(pbiSelectedCountry)
  );
})();