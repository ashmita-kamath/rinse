/**
 * Rinse JavaScript client (no dependencies, works in browsers and Node 18+).
 *
 *   import { Rinse } from "./rinse.js";
 *   const api = new Rinse("http://127.0.0.1:8000");
 *   const { rows } = await api.rows("schools", { district_name: "Mysuru" });
 */
export class RinseError extends Error {
  constructor(status, detail) {
    super(`${status}: ${detail}`);
    this.status = status;
    this.detail = detail;
  }
}

export class Rinse {
  constructor(baseUrl = "") {
    this.baseUrl = baseUrl.replace(/\/$/, "");
  }

  url(path, params = {}) {
    const query = new URLSearchParams();
    for (const [key, value] of Object.entries(params)) {
      if (value !== undefined && value !== null && value !== "") query.append(key, value);
    }
    const qs = query.toString();
    return `${this.baseUrl}${path}${qs ? "?" + qs : ""}`;
  }

  async get(path, params) {
    const res = await fetch(this.url(path, params));
    const body = await res.json().catch(() => ({}));
    if (!res.ok) throw new RinseError(res.status, body.detail || res.statusText);
    return body;
  }

  datasets() {
    return this.get("/datasets");
  }

  dataset(name) {
    return this.get(`/datasets/${encodeURIComponent(name)}`);
  }

  versions(name) {
    return this.get(`/datasets/${encodeURIComponent(name)}/versions`);
  }

  /** Returns { dataset, version, total, limit, offset, rows }. Extra keys are filters. */
  rows(name, { limit = 100, offset = 0, version, ...filters } = {}) {
    return this.get(`/datasets/${encodeURIComponent(name)}/rows`, { limit, offset, version, ...filters });
  }

  async allRows(name, { version, ...filters } = {}) {
    const out = [];
    for (let offset = 0; ; offset += 1000) {
      const page = await this.rows(name, { limit: 1000, offset, version, ...filters });
      out.push(...page.rows);
      if (page.rows.length < 1000) return out;
    }
  }

  exportUrl(name, version) {
    return this.url(`/datasets/${encodeURIComponent(name)}/export.csv`, { version });
  }
}
