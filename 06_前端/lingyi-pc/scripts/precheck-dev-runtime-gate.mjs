#!/usr/bin/env node

const DEV_HEADERS = {
  "X-LY-Dev-User": "local.dev",
  "X-LY-Dev-Roles": "System Manager"
};

const CHECKS = [
  { name: "backend_auth_me", url: "http://127.0.0.1:8000/api/auth/me" },
  { name: "backend_reports_catalog", url: "http://127.0.0.1:8000/api/reports/catalog" },
  { name: "frontend_auth_me", url: "http://127.0.0.1:5174/api/auth/me" },
  { name: "frontend_reports_catalog", url: "http://127.0.0.1:5174/api/reports/catalog" }
];

function assertLocalUrl(url) {
  const parsed = new URL(url);
  if (parsed.hostname !== "127.0.0.1") {
    throw new Error(`仅允许本地地址，发现非本地 URL: ${url}`);
  }
}

async function probe(check) {
  assertLocalUrl(check.url);
  const startedAt = Date.now();
  try {
    const response = await fetch(check.url, {
      method: "GET",
      headers: DEV_HEADERS
    });
    const durationMs = Date.now() - startedAt;
    const text = await response.text();
    return {
      name: check.name,
      url: check.url,
      ok: response.status === 200,
      status: response.status,
      statusText: response.statusText,
      durationMs,
      responsePreview: text.slice(0, 200)
    };
  } catch (error) {
    return {
      name: check.name,
      url: check.url,
      ok: false,
      status: null,
      statusText: "REQUEST_FAILED",
      durationMs: Date.now() - startedAt,
      error: String(error)
    };
  }
}

const checks = await Promise.all(CHECKS.map(probe));
const failed = checks.filter((item) => !item.ok);
const summary = {
  script: "precheck-dev-runtime-gate.mjs",
  localOnly: true,
  method: "GET",
  devHeadersUsed: DEV_HEADERS,
  totalChecks: checks.length,
  passedChecks: checks.length - failed.length,
  failedChecks: failed.length,
  checks
};

console.log(JSON.stringify(summary, null, 2));

if (failed.length > 0) {
  process.exit(1);
}
