#!/usr/bin/env node
import fs from "node:fs/promises";
import path from "node:path";
import http from "node:http";
import https from "node:https";
import { pathToFileURL } from "node:url";

function nowCn() {
  const dt = new Date();
  const pad = (v) => String(v).padStart(2, "0");
  const tzMin = -dt.getTimezoneOffset();
  const sign = tzMin >= 0 ? "+" : "-";
  const abs = Math.abs(tzMin);
  const tzh = pad(Math.floor(abs / 60));
  const tzm = pad(abs % 60);
  return `${dt.getFullYear()}-${pad(dt.getMonth() + 1)}-${pad(dt.getDate())}T${pad(
    dt.getHours(),
  )}:${pad(dt.getMinutes())}:${pad(dt.getSeconds())}${sign}${tzh}:${tzm}`;
}

function parseArgs(argv) {
  const args = {};
  for (let i = 2; i < argv.length; i += 1) {
    const key = argv[i];
    const val = argv[i + 1];
    if (key.startsWith("--") && typeof val !== "undefined") {
      args[key.slice(2)] = val;
      i += 1;
    }
  }
  return args;
}

function normalizeText(text, maxLen = 400) {
  const compact = String(text || "")
    .replace(/\s+/g, " ")
    .trim();
  if (compact.length <= maxLen) {
    return compact;
  }
  return `${compact.slice(0, maxLen - 3)}...`;
}

function toTsvValue(value) {
  if (value === null || typeof value === "undefined") {
    return "null";
  }
  if (typeof value === "boolean") {
    return value ? "true" : "false";
  }
  if (Array.isArray(value)) {
    return value.length ? value.join(";") : "[]";
  }
  return String(value).replace(/\t/g, " ");
}

function writeTsv(filePath, headers, rows) {
  const lines = [headers.join("\t")];
  for (const row of rows) {
    lines.push(headers.map((h) => toTsvValue(row[h])).join("\t"));
  }
  return fs.writeFile(filePath, `${lines.join("\n")}\n`, "utf-8");
}

function isHttpUrl(raw) {
  return typeof raw === "string" && (raw.startsWith("http://") || raw.startsWith("https://"));
}

function parseUrl(raw) {
  try {
    return new URL(raw);
  } catch {
    return null;
  }
}

async function probeServer(urlString) {
  const u = new URL(urlString);
  const agent = u.protocol === "https:" ? https : http;
  return new Promise((resolve) => {
    const req = agent.request(
      {
        method: "GET",
        hostname: u.hostname,
        port: u.port,
        path: u.pathname || "/",
        timeout: 3500,
      },
      (res) => {
        const ok = (res.statusCode || 0) >= 200 && (res.statusCode || 0) < 500;
        res.resume();
        resolve({ ok, statusCode: res.statusCode || 0, error: "" });
      },
    );
    req.on("timeout", () => {
      req.destroy(new Error("timeout"));
    });
    req.on("error", (err) => {
      resolve({ ok: false, statusCode: 0, error: String(err.message || err) });
    });
    req.end();
  });
}

function classifyRequest(entry, allowedHosts) {
  const method = (entry.method || "").toUpperCase();
  const urlObj = parseUrl(entry.url);
  const host = urlObj ? urlObj.hostname : "";
  const pathname = urlObj ? urlObj.pathname : "";
  const isApi = pathname.startsWith("/api/");
  const isWrite = method !== "GET";
  const isHostAllowed = allowedHosts.includes(host);
  const isProductionLike =
    !isHostAllowed &&
    (/erpnext|frappe|prod|production/i.test(entry.url) || pathname.startsWith("/api/"));
  return {
    ...entry,
    method,
    host,
    pathname,
    is_api: isApi,
    is_write_method: isWrite,
    is_production_like: isProductionLike,
  };
}

function detectIdentity({ target, finalUrl, routeState, title, bodyText, blockedTokens }) {
  const token = (target.route_token || target.path || "").toLowerCase();
  const final = String(finalUrl || "").toLowerCase();
  const route = String(routeState || "").toLowerCase();
  const titleText = String(title || "").toLowerCase();
  const body = String(bodyText || "").toLowerCase();

  const blockedToken = blockedTokens.find((x) => final.includes(x.toLowerCase()) || route.includes(x.toLowerCase()));
  const pathMatch = token && (final.includes(token) || route.includes(token));
  const keywordMatch =
    Array.isArray(target.identity_keywords) &&
    target.identity_keywords.some((k) => {
      const kw = String(k).toLowerCase();
      return titleText.includes(kw) || body.includes(kw);
    });
  const isTargetPage = Boolean(pathMatch) && !blockedToken;

  let basis = "";
  if (blockedToken) {
    basis = `blocked_token:${blockedToken}`;
  } else if (pathMatch && keywordMatch) {
    basis = "path+keyword";
  } else if (pathMatch) {
    basis = "path_only";
  } else if (keywordMatch) {
    basis = "keyword_only";
  } else {
    basis = "none";
  }

  return {
    is_target_page: isTargetPage,
    identity_basis: basis,
    blocked_token: blockedToken || null,
    path_match: Boolean(pathMatch),
    keyword_match: Boolean(keywordMatch),
  };
}

async function loadPlaywright(repoRoot) {
  const normalize = (mod) => (mod && mod.chromium ? mod : mod && mod.default ? mod.default : mod);
  try {
    return normalize(await import("playwright"));
  } catch {
    const p = path.join(repoRoot, "06_前端/lingyi-pc/node_modules/playwright/index.js");
    return normalize(await import(pathToFileURL(p).href));
  }
}

async function run() {
  const args = parseArgs(process.argv);
  const required = [
    "manifest",
    "output-json",
    "output-tsv",
    "output-browser-json",
    "screenshot-dir",
  ];
  for (const key of required) {
    if (!args[key]) {
      throw new Error(`missing_arg:${key}`);
    }
  }

  const manifestPath = path.resolve(args.manifest);
  const outputJsonPath = path.resolve(args["output-json"]);
  const outputTsvPath = path.resolve(args["output-tsv"]);
  const outputBrowserPath = path.resolve(args["output-browser-json"]);
  const screenshotDir = path.resolve(args["screenshot-dir"]);

  const manifest = JSON.parse(await fs.readFile(manifestPath, "utf-8"));
  const repoRoot = path.resolve(manifest.repo_root || "/Users/hh/Desktop/领意服装管理系统");
  const baseUrl = manifest.base_url;
  const allowedHosts = manifest.allowed_hosts || ["127.0.0.1", "localhost"];
  const blockedTokens = manifest.blocked_final_url_tokens || [];
  const viewports = manifest.viewports || [];
  const targetPages = manifest.target_pages || [];
  const timeouts = manifest.timeouts || {};
  const gotoTimeout = Number(timeouts.goto_ms || 30000);
  const settleMs = Number(timeouts.settle_ms || 1200);

  await fs.mkdir(screenshotDir, { recursive: true });

  const serverProbe = await probeServer(`${baseUrl}/fate/`);
  const requests = [];
  const pageRuns = [];
  const consoleErrors = [];
  const networkErrors = [];
  const residualRisks = [];
  let routeSmokePassCount = 0;
  let routeSmokeBlockedCount = 0;
  let screenshotCount = 0;
  let validTargetScreenshotCount = 0;

  let browser = null;
  let playwright = null;

  const blockedByRuntime =
    !serverProbe.ok || !Array.isArray(viewports) || viewports.length === 0 || targetPages.length === 0;

  if (!blockedByRuntime) {
    playwright = await loadPlaywright(repoRoot);
    browser = await playwright.chromium.launch({ headless: true });
    let runIndex = 0;
    for (const target of targetPages) {
      for (const vp of viewports) {
        runIndex += 1;
        const context = await browser.newContext({
          viewport: { width: Number(vp.width), height: Number(vp.height) },
        });
        const page = await context.newPage();

        const runRequests = [];
        const runConsoleErrors = [];
        const runNetworkErrors = [];

        page.on("request", (req) => {
          const u = req.url();
          if (!isHttpUrl(u)) {
            return;
          }
          const item = {
            request_id: `${target.page_id}_${vp.name}_${runRequests.length + 1}`,
            page_id: target.page_id,
            viewport: vp.name,
            method: req.method(),
            url: u,
            resource_type: req.resourceType(),
          };
          runRequests.push(item);
          requests.push(item);
        });

        page.on("console", (msg) => {
          if (msg.type() === "error") {
            const row = {
              page_id: target.page_id,
              viewport: vp.name,
              text: normalizeText(msg.text(), 600),
            };
            runConsoleErrors.push(row);
            consoleErrors.push(row);
          }
        });

        page.on("pageerror", (err) => {
          const row = {
            page_id: target.page_id,
            viewport: vp.name,
            text: normalizeText(err.message || String(err), 600),
          };
          runConsoleErrors.push(row);
          consoleErrors.push(row);
        });

        page.on("requestfailed", (req) => {
          const failure = req.failure();
          const row = {
            page_id: target.page_id,
            viewport: vp.name,
            url: req.url(),
            error_text: failure ? String(failure.errorText || "") : "unknown_failure",
          };
          runNetworkErrors.push(row);
          networkErrors.push(row);
        });

        const targetUrl = `${baseUrl}${target.path}`;
        let finalUrl = "";
        let finalRoute = "";
        let title = "";
        let bodyText = "";
        let status = "PASS";
        let blockedReason = null;
        let navError = null;
        try {
          await page.goto(targetUrl, {
            waitUntil: "domcontentloaded",
            timeout: gotoTimeout,
          });
          await page.waitForTimeout(settleMs);
          finalUrl = page.url();
          const state = await page.evaluate(() => ({
            route: `${location.pathname}${location.search}${location.hash}`,
            title: document.title || "",
            body: (document.body && document.body.innerText) || "",
          }));
          finalRoute = state.route || "";
          title = normalizeText(state.title, 400);
          bodyText = normalizeText(state.body, 1200);
        } catch (err) {
          navError = normalizeText(err.message || String(err), 600);
          status = "BLOCKED";
          blockedReason = `navigation_error:${navError}`;
        }

        const identity = detectIdentity({
          target,
          finalUrl,
          routeState: finalRoute,
          title,
          bodyText,
          blockedTokens,
        });
        if (status !== "BLOCKED" && !identity.is_target_page) {
          status = "BLOCKED";
          blockedReason = identity.blocked_token
            ? `final_url_blocked_token:${identity.blocked_token}`
            : "page_identity_not_determined";
        }

        const screenshotPath = path.join(
          screenshotDir,
          `z008b22_${String(runIndex).padStart(2, "0")}_${target.page_id}_${vp.name}.png`,
        );
        await page.screenshot({ path: screenshotPath, fullPage: true });
        screenshotCount += 1;

        if (identity.is_target_page) {
          validTargetScreenshotCount += 1;
        }

        if (status === "PASS") {
          routeSmokePassCount += 1;
        } else {
          routeSmokeBlockedCount += 1;
          if (blockedReason) {
            residualRisks.push(
              `${target.page_id}/${vp.name}:${blockedReason}`,
            );
          }
        }

        pageRuns.push({
          run_id: `R${String(runIndex).padStart(2, "0")}`,
          page_id: target.page_id,
          page_target: target.path,
          viewport: vp.name,
          target_url: targetUrl,
          final_url: finalUrl || "null",
          final_route: finalRoute || "null",
          page_title: title || "null",
          visible_proof: bodyText || "null",
          is_target_page: identity.is_target_page,
          identity_basis: identity.identity_basis,
          path_match: identity.path_match,
          keyword_match: identity.keyword_match,
          status,
          blocked_reason: blockedReason,
          screenshot_path: screenshotPath,
          request_count: runRequests.length,
          console_error_count: runConsoleErrors.length,
          network_error_count: runNetworkErrors.length,
          navigation_error: navError || "null",
        });

        await context.close();
      }
    }
    await browser.close();
  }

  const classifiedRequests = requests.map((r) => classifyRequest(r, allowedHosts));
  const methodSet = [...new Set(classifiedRequests.map((r) => r.method))].sort();
  const nonGetRequests = classifiedRequests.filter((r) => r.method !== "GET");
  const writeRequests = classifiedRequests.filter((r) => r.is_api && r.is_write_method);
  const forbiddenRequests = classifiedRequests.filter(
    (r) => (r.is_api && r.method !== "GET") || r.is_production_like,
  );

  const runtimeRequestCount = classifiedRequests.length;
  const writeRequestCount = writeRequests.length;
  const unexpectedWriteRequestCount = writeRequests.length;
  const forbiddenRequestCount = forbiddenRequests.length;
  const blockingConsoleErrorCount = consoleErrors.length;
  const networkErrorCount = networkErrors.length;

  let taskStatus = "PASS";
  const globalBlocks = [];
  if (blockedByRuntime) {
    taskStatus = "BLOCK";
    globalBlocks.push(
      `runtime_unavailable:probe_ok=${serverProbe.ok};status=${serverProbe.statusCode};error=${serverProbe.error || "null"}`,
    );
  }
  if (nonGetRequests.length > 0) {
    taskStatus = "BLOCK";
    globalBlocks.push(`non_get_requests=${nonGetRequests.length}`);
  }
  if (writeRequestCount > 0 || unexpectedWriteRequestCount > 0 || forbiddenRequestCount > 0) {
    taskStatus = "BLOCK";
    globalBlocks.push(
      `request_boundary_violation:write=${writeRequestCount},unexpected_write=${unexpectedWriteRequestCount},forbidden=${forbiddenRequestCount}`,
    );
  }
  if (routeSmokeBlockedCount > 0) {
    taskStatus = "BLOCK";
    globalBlocks.push(`route_smoke_blocked=${routeSmokeBlockedCount}`);
  }

  const resultPayload = {
    task_id: manifest.task_id,
    source_head: manifest.source_head,
    selected_candidate_id: manifest.selected_candidate_id,
    generated_at: nowCn(),
    task_status: taskStatus,
    script_path: path.resolve(process.argv[1]),
    manifest_path: manifestPath,
    base_url: baseUrl,
    target_page_count: targetPages.length,
    viewport_count: viewports.length,
    screenshot_count: screenshotCount,
    valid_target_screenshot_count: validTargetScreenshotCount,
    route_smoke_pass_count: routeSmokePassCount,
    route_smoke_blocked_count: routeSmokeBlockedCount,
    runtime_request_count: runtimeRequestCount,
    request_methods: methodSet,
    write_request_count: writeRequestCount,
    unexpected_write_request_count: unexpectedWriteRequestCount,
    forbidden_request_count: forbiddenRequestCount,
    blocking_console_error_count: blockingConsoleErrorCount,
    network_error_count: networkErrorCount,
    server_probe: serverProbe,
    residual_risks: [...new Set([...residualRisks, ...globalBlocks])],
    runtime_flags: {
      production_account_used: false,
      remote_lifecycle_action_executed: false,
      runtime_request_allowed: true,
      write_request_count: writeRequestCount,
    },
    page_results: pageRuns,
  };

  const tsvRows = pageRuns.map((row) => ({
    run_id: row.run_id,
    page_id: row.page_id,
    viewport: row.viewport,
    status: row.status,
    is_target_page: row.is_target_page,
    identity_basis: row.identity_basis,
    target_url: row.target_url,
    final_url: row.final_url,
    blocked_reason: row.blocked_reason || "null",
    request_count: row.request_count,
    console_error_count: row.console_error_count,
    network_error_count: row.network_error_count,
    screenshot_path: row.screenshot_path,
  }));

  const browserPayload = {
    task_id: manifest.task_id,
    source_head: manifest.source_head,
    selected_candidate_id: manifest.selected_candidate_id,
    generated_at: nowCn(),
    task_status: taskStatus,
    base_url: baseUrl,
    request_log_count: classifiedRequests.length,
    request_methods: methodSet,
    write_request_count: writeRequestCount,
    unexpected_write_request_count: unexpectedWriteRequestCount,
    forbidden_request_count: forbiddenRequestCount,
    blocking_console_error_count: blockingConsoleErrorCount,
    network_error_count: networkErrorCount,
    route_smoke_pass_count: routeSmokePassCount,
    route_smoke_blocked_count: routeSmokeBlockedCount,
    screenshot_count: screenshotCount,
    valid_target_screenshot_count: validTargetScreenshotCount,
    residual_risks: [...new Set([...residualRisks, ...globalBlocks])],
    request_log: classifiedRequests,
    page_results: pageRuns,
    console_errors: consoleErrors,
    network_errors: networkErrors,
  };

  await fs.writeFile(outputJsonPath, `${JSON.stringify(resultPayload, null, 2)}\n`, "utf-8");
  await writeTsv(
    outputTsvPath,
    [
      "run_id",
      "page_id",
      "viewport",
      "status",
      "is_target_page",
      "identity_basis",
      "target_url",
      "final_url",
      "blocked_reason",
      "request_count",
      "console_error_count",
      "network_error_count",
      "screenshot_path",
    ],
    tsvRows,
  );
  await fs.writeFile(outputBrowserPath, `${JSON.stringify(browserPayload, null, 2)}\n`, "utf-8");
}

run().catch(async (err) => {
  const args = parseArgs(process.argv);
  if (args["output-json"]) {
    const payload = {
      task_id: "TASK-Z008B-22-IMPL",
      generated_at: nowCn(),
      task_status: "BLOCK",
      error: String(err && err.stack ? err.stack : err),
      runtime_request_count: 0,
      write_request_count: 0,
      production_account_used: false,
      remote_lifecycle_action_executed: false,
    };
    await fs.writeFile(path.resolve(args["output-json"]), `${JSON.stringify(payload, null, 2)}\n`, "utf-8");
  }
  throw err;
});
