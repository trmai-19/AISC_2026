(() => {
  const state = {};
  let busy = false;

  const pages = ['community', 'needs', 'product-usage'];

  const colors = [
    'var(--accent-primary)',
    'var(--accent-ocean)',
    '#F59E0B',
    '#8B5CF6'
  ];

  const labels = {
    JP: 'Japan',
    KR: 'South Korea',
    AU: 'Australia',

    DU_HOC: 'Study',
    LAO_DONG: 'Work',
    DINH_CU: 'Settlement',
    UNKNOWN: 'Unknown',

    PREPARING: 'Before departure',
    RECENT_ARRIVED: 'Recently arrived',
    LIVING_STUDYING: 'Living / studying abroad',
    RETURNED: 'Returned home',

    tham_gia_cong_dong: 'Community participation',
    thu_tuc_hanh_chinh: 'Administrative procedures',
    giao_tiep: 'Communication',
    hoc_tap_cong_viec: 'Study and work',
    cuoc_song_hang_ngay: 'Daily life',
    nha_o: 'Housing',
    tai_chinh: 'Finance',

    doi_song: 'Daily life',
    phap_ly: 'Legal procedures',
    y_te: 'Healthcare',
    cong_viec: 'Work',
    hoc_tap: 'Study',
    giao_thong: 'Transport'
  };

  const esc = value => escapeHtml(String(value ?? ''));

  const label = value => labels[value] ?? value ?? 'Unknown';

  const valid = value =>
    value !== null &&
    value !== undefined &&
    Number.isFinite(Number(value));

  const fmt = value =>
    valid(value)
      ? Number(value).toLocaleString('en-US')
      : 'No data';

  const empty = () => `
    <p style="color:var(--text-muted);padding:1rem">
      No data available.
    </p>
  `;

  const chart = (title, body) => `
    <div class="pbi-chart-visual">
      <div class="pbi-chart-header">
        <div class="pbi-chart-title">${esc(title)}</div>
      </div>
      ${body}
    </div>
  `;

  const grid = (...items) => `
    <div class="pbi-charts-grid" style="margin-top:1rem">
      ${items.join('')}
    </div>
  `;

  function cards(k, usage = false) {
    const items = usage ? [
      ['Identified Questioners', k.identified_questioners, false],
      ['User Messages', k.user_messages, false],
      ['Anonymous User Messages', k.anonymous_messages, false],
      ['Returning Questioners', k.returning_questioners, false]
    ] : [
      ['Contributions', k.contribution_count, false],
      ['Participants', k.participant_count, false],
      ['High Use Intention', k.high_use_intention_pct, true],
      ['Low Preparation', k.low_preparation_pct, true]
    ];

    return `
      <div class="pbi-cards-grid">
        ${items.map(([title, value, pct]) => `
          <div class="pbi-card-visual">
            <div class="pbi-card-with-donut">
              <div>
                <div class="pbi-card-callout">
                  ${esc(fmt(value))}${pct && valid(value) ? '%' : ''}
                </div>
                <div class="pbi-card-label">${esc(title)}</div>
              </div>
              ${
                pct && valid(value)
                  ? renderSvgMiniDonut(Number(value))
                  : ''
              }
            </div>
          </div>
        `).join('')}
      </div>
    `;
  }

  function bars(items, percent = false) {
    if (!items.length) return empty();

    const max = percent
      ? 100
      : Math.max(1, ...items.map(x => Number(x.value) || 0));

    return `
      <div class="pbi-bars-container">
        ${items.map(item => {
          const width = valid(item.value)
            ? Math.max(
                0,
                Math.min(100, Number(item.value) / max * 100)
              )
            : 0;

          return `
            <div class="pbi-bar-row">
              <div class="pbi-bar-label">${esc(item.name)}</div>
              <div class="pbi-bar-track-wrap">
                <div class="pbi-bar-track">
                  <div
                    class="pbi-bar-fill"
                    style="width:${width}%;background:var(--accent-primary)"
                  ></div>
                </div>
                <div class="pbi-bar-val">
                  ${esc(fmt(item.value))}${
                    percent && valid(item.value) ? '%' : ''
                  }
                </div>
              </div>
            </div>
          `;
        }).join('')}
      </div>
    `;
  }

  function columns(rows, labelKey, valueKey) {
    if (
      !rows.length ||
      !rows.some(row => Number(row[valueKey]) > 0)
    ) {
      return empty();
    }

    const items = rows.map(row => ({
      label: String(row[labelKey]),
      count: Number(row[valueKey]),
      displayVal: `${fmt(row[valueKey])}${
        valid(row.pct) ? ` (${fmt(row.pct)}%)` : ''
      }`
    }));

    return renderVerticalColumnChart(
      items,
      'count',
      'label',
      null
    );
  }

  function table(headers, rows) {
    if (!rows.length) return empty();

    return `
      <div class="pbi-table-wrap">
        <table class="pbi-table">
          <thead>
            <tr>
              ${headers.map(x => `<th>${esc(x)}</th>`).join('')}
            </tr>
          </thead>
          <tbody>
            ${rows.map(row => `
              <tr>
                ${row.map(x => `<td>${esc(x)}</td>`).join('')}
              </tr>
            `).join('')}
          </tbody>
        </table>
      </div>
    `;
  }

  function overview(d) {
    const purposes = d.purposes.map((p, i) => ({
      label: label(p.purpose),
      count: p.count,
      pct: p.pct,
      color: colors[i % colors.length]
    }));

    const total = purposes.reduce(
      (sum, p) => sum + Number(p.count),
      0
    );

    return cards(d.kpis) + grid(
      chart(
        'Use Intention (1–5)',
        columns(d.useIntention, 'score', 'count')
      ),
      chart(
        'Low Preparation by Stage',
        bars(d.stages.map(s => ({
          name: `${label(s.stage)} (valid responses: ${
            fmt(s.valid_preparation_count)
          })`,
          value: s.low_prep_pct
        })), true)
      )
    ) + grid(
      chart(
        'Purpose of Moving Abroad',
        total
          ? renderSvgDonutChart(
              purposes,
              'Participants',
              fmt(total)
            )
          : empty()
      ),
      chart(
        'Participants by Country',
        bars(d.countries.map(c => ({
          name: label(c.country_code),
          value: c.participant_count
        })))
      )
    );
  }

  function needs(d) {
    const matrix = new Map();

    for (const row of d.challengesByCountry) {
      if (!matrix.has(row.challenge_code)) {
        matrix.set(row.challenge_code, {});
      }

      matrix.get(row.challenge_code)[row.country_code] = row.pct;
    }

    const pct = value =>
      valid(value) ? `${fmt(value)}%` : 'No data';

    return cards(d.kpis) + grid(
      chart(
        'High Use Intention by Preparation Group',
        bars(d.preparationUse.map(p => ({
          name: `${p.preparation_group} (n = ${
            fmt(p.paired_response_count)
          })`,
          value: p.high_use_intention_pct
        })), true)
      ),
      chart(
        'Reported Challenges',
        bars(d.challenges.map(c => ({
          name: label(c.challenge_code),
          value: c.pct
        })), true)
      )
    ) + grid(
      chart(
        'Challenges by Country (%)',
        table(
          ['Challenge', 'Japan', 'South Korea', 'Australia'],
          [...matrix].map(([code, values]) => [
            label(code),
            pct(values.JP),
            pct(values.KR),
            pct(values.AU)
          ])
        )
      ),
      chart(
        'Approved Community Experiences — Latest 10',
        table(
          ['Country', 'Domain', 'Title'],
          d.experiences.slice(0, 10).map(e => [
            label(e.country_code),
            label(e.domain_id),
            e.title
          ])
        )
      )
    ) + `
      <p style="color:var(--text-muted);font-size:.8rem;margin-top:1rem">
        Challenge percentages use all contributions as the denominator.
        Multiple selections are allowed.
      </p>
    `;
  }

  function usage(d) {
    let trend = empty();

    if (d.messageTrend.length === 1) {
      trend = bars(d.messageTrend.map(p => ({
        name: p.month,
        value: p.messages
      })));
    } else if (d.messageTrend.length > 1) {
      trend = renderSvgAreaTrendChart(d.messageTrend);
    }

    return cards(d.kpis, true) + grid(
      chart('User Messages by Month', trend),
      chart(
        'Questioners by Active Days',
        columns(d.activeDays, 'day_group', 'count')
      )
    ) + `
      <div style="margin-top:1rem">
        ${chart(
          'Evidence Card Usage — Top 20',
          bars(d.botCardUsage.map(c => ({
            name: c.name,
            value: c.count
          })))
        )}
      </div>
    `;
  }

  const renderers = {
    community: overview,
    needs,
    'product-usage': usage
  };

  function renderPage(page) {
    const current = state[page];

    const refreshButton = `
      <button type="button" onclick="refreshAiscDashboards()">
        Refresh data
      </button>
    `;

    if (!current?.result) {
      return `
        <div class="pbi-chart-visual">
          <p>${
            current?.error
              ? 'Dashboard API is unavailable. Please retry.'
              : 'Loading dashboard data…'
          }</p>
          ${refreshButton}
        </div>
      `;
    }

    const result = current.result;

    const time = new Date(result.data_as_of).toLocaleString(
      'en-GB',
      { timeZone: 'Asia/Ho_Chi_Minh' }
    );

    return `
      <div style="margin-bottom:1rem;color:var(--text-muted);font-size:.8rem">
        Data as of: ${esc(time)} (Vietnam time)
        · ${refreshButton}
        ${
          current.error
            ? '<p>Refresh failed. Showing previously loaded data.</p>'
            : ''
        }
      </div>
      ${renderers[page](result.data)}
    `;
  }

  async function fetchPage(page) {
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
        `${base}/dashboard/${page}`,
        {
          cache: 'no-store',
          signal: controller.signal
        }
      );

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
      }

      const result = await response.json();

      if (!result.run_id || !result.data?.kpis) {
        throw new Error('Invalid dashboard response');
      }

      state[page] = {
        result,
        error: null
      };
    } catch (error) {
      state[page] = {
        ...state[page],
        error: String(error)
      };

      console.error(`Dashboard ${page}:`, error);
    } finally {
      clearTimeout(timer);
    }
  }

  async function refresh() {
    if (busy) return;

    busy = true;

    try {
      await Promise.all(pages.map(fetchPage));

      if (pbiCurrentPage >= 3 && pbiCurrentPage <= 5) {
        renderPowerBIDashboard();
      }
    } finally {
      busy = false;
    }
  }

  renderAiscOverviewPage = () => renderPage('community');
  renderAiscNeedsPage = () => renderPage('needs');
  renderAiscProductPage = () => renderPage('product-usage');

  window.refreshAiscDashboards = refresh;

  document.addEventListener('DOMContentLoaded', refresh);

  setInterval(() => {
    if (
      !document.hidden &&
      pbiCurrentPage >= 3 &&
      pbiCurrentPage <= 5
    ) {
      refresh();
    }
  }, 60000);
})();