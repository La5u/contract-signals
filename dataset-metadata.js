'use strict';

// Pure formatting: no DOM, network, filesystem or current-clock fallback.
(function () {
  function validDate(value) {
    if (typeof value !== 'string') return false;
    const match = /^(\d{4})-(\d{2})-(\d{2})(?:T(\d{2}):(\d{2}):(\d{2})(?:\.\d+)?(Z|[+-]\d{2}:\d{2}))?$/.exec(value);
    if (!match) return false;
    const [, y, m, d, h, min, sec, zone] = match;
    const year = Number(y), month = Number(m), day = Number(d);
    const leap = year % 4 === 0 && (year % 100 !== 0 || year % 400 === 0);
    const days = [31, leap ? 29 : 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
    return month >= 1 && month <= 12 && day >= 1 && day <= days[month - 1]
      && (!h || (Number(h) < 24 && Number(min) < 60 && Number(sec) < 60
        && (zone === 'Z' || (Number(zone.slice(1, 3)) < 24 && Number(zone.slice(4)) < 60))))
      && Number.isFinite(Date.parse(value));
  }
  function validPeriod(period, coverage = false) {
    return period != null && validDate(period.start) && validDate(period.end)
      && Date.parse(period.start) <= Date.parse(period.end)
      && (!coverage || (typeof period.endExclusive === 'boolean'
        && (!period.endExclusive || Date.parse(period.start) < Date.parse(period.end))
        && typeof period.basis === 'string' && period.basis.trim().length > 0));
  }
  // Invalid fields are rejected independently; an absent publisher date never
  // discards a valid snapshot or coverage period.
  function validate(entry) {
    const e = entry && typeof entry === 'object' ? entry : {};
    return {
      snapshot: validPeriod(e.snapshot) ? { ...e.snapshot } : null,
      coverage: validPeriod(e.coverage, true) ? { ...e.coverage } : null,
      source_updated: validDate(e.source_updated) ? e.source_updated : null,
      notes: Array.isArray(e.notes) ? e.notes.filter(n => typeof n === 'string') : []
    };
  }
  function dateText(date) {
    return date.includes('T') ? date.replace(/(?:Z|\+00:00)$/, ' UTC') : date;
  }
  function periodText(period, coverage = false) {
    if (!period) return 'Unknown';
    const range = period.start === period.end ? dateText(period.start)
      : `${dateText(period.start)} → ${dateText(period.end)}`;
    return coverage ? `${range} (${period.endExclusive ? 'end exclusive' : 'end inclusive'}; ${period.basis})` : range;
  }
  function formatEntries(key, map = {}) {
    const all = key === 'all';
    const e = validate(!all && key !== 'local' && map && Object.hasOwn(map, key) ? map[key] : null);
    return {
      fields: [
        { label: 'Snapshot collected', value: all ? 'Dates vary by dataset' : periodText(e.snapshot) },
        { label: 'Coverage period', value: all ? 'Dates and coverage basis vary by dataset' : periodText(e.coverage, true) },
        { label: 'Source last updated', value: all ? 'Dates vary by dataset; unknown unless recorded' : e.source_updated ? dateText(e.source_updated) : 'Unknown' }
      ],
      notes: all ? ['No single collection or coverage date applies. Consult each dataset separately.'] : e.notes
    };
  }
  const api = { validDate, validate, formatEntries };
  globalThis.DatasetMetadata = api;
  if (typeof module !== 'undefined' && module.exports) module.exports = api;
})();
