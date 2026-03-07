/* FISC-QAv2 Review UI */

const API = "/api";

// --- Utility ---

async function api(path, opts = {}) {
  const res = await fetch(API + path, opts);
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }));
    throw new Error(err.detail || res.statusText);
  }
  return res;
}

function $(sel) { return document.querySelector(sel); }
function $$(sel) { return document.querySelectorAll(sel); }

function badge(value, prefix) {
  const cls = prefix ? `badge-${value}` : `badge-${value}`;
  return `<span class="badge ${cls}">${value}</span>`;
}

function confidenceBadge(c) { return badge(c); }
function reviewBadge(s) { return badge(s); }

function toast(msg) {
  let el = $("#toast");
  if (!el) {
    el = document.createElement("div");
    el.id = "toast";
    el.className = "toast";
    document.body.appendChild(el);
  }
  el.textContent = msg;
  el.classList.add("show");
  setTimeout(() => el.classList.remove("show"), 2500);
}

function formatDate(iso) {
  if (!iso) return "-";
  const d = new Date(iso);
  return d.toLocaleString("ja-JP");
}

// --- Router ---

const routes = {
  home: renderHome,
  run: renderRun,
  answer: renderAnswer,
  notes: renderNotes,
  pipeline: renderPipeline,
};

let state = { view: "home", runId: null, questionNo: null };

function navigate(view, params = {}) {
  state = { view, ...params };
  const h = `#${view}` + (params.runId ? `/${params.runId}` : "") +
            (params.questionNo ? `/${params.questionNo}` : "") +
            (params.jobId ? `/${params.jobId}` : "");
  history.pushState(state, "", h);
  render();
}

function render() {
  const fn = routes[state.view] || renderHome;
  fn();
}

window.addEventListener("popstate", (e) => {
  if (e.state) {
    state = e.state;
    render();
  }
});

// Parse hash on load
function parseHash() {
  const h = location.hash.slice(1);
  if (!h) return { view: "home" };
  const parts = h.split("/");
  if (parts[0] === "run" && parts[1]) {
    return { view: "run", runId: parseInt(parts[1]) };
  }
  if (parts[0] === "answer" && parts[1] && parts[2]) {
    return { view: "answer", runId: parseInt(parts[1]), questionNo: parseInt(parts[2]) };
  }
  if (parts[0] === "notes" && parts[1]) {
    return { view: "notes", runId: parseInt(parts[1]) };
  }
  if (parts[0] === "pipeline" && parts[1]) {
    return { view: "pipeline", jobId: parts[1] };
  }
  return { view: "home" };
}

// --- Views ---

async function renderHome() {
  const app = $("#app");

  // Load config for default values
  let cfg = { kb_dir: "kb", model: "claude-sonnet-4-20250514", token_budget: 80000 };
  try {
    const cfgRes = await api("/config");
    cfg = await cfgRes.json();
  } catch (_) {}

  app.innerHTML = `
    <div class="container">
      <div class="card">
        <h2>新規パイプライン実行</h2>
        <p style="font-size:0.85rem;color:var(--text-muted);margin-bottom:1rem">
          質問票をアップロードしてパイプラインを実行します。完了後、自動でレビュー画面に遷移します。
        </p>
        <div class="pipeline-form">
          <div class="pipeline-drop" id="pipeline-drop">
            <p>質問票 Excel をドラッグ&ドロップ、またはクリックして選択</p>
            <p style="font-size:0.8rem;color:var(--text-muted);margin-top:0.5rem">.xlsx</p>
            <input type="file" id="pipeline-file" accept=".xlsx">
          </div>
          <div id="pipeline-file-name" class="pipeline-file-name" style="display:none"></div>
          <details class="pipeline-details">
            <summary>詳細設定</summary>
            <div class="pipeline-settings">
              <label>KB ディレクトリ
                <input type="text" id="pipeline-kb-dir" value="${cfg.kb_dir}">
              </label>
              <label>モデル
                <input type="text" id="pipeline-model" value="${cfg.model}">
              </label>
              <label>トークンバジェット
                <input type="number" id="pipeline-budget" value="${cfg.token_budget}">
              </label>
            </div>
          </details>
          <button class="btn btn-primary" id="pipeline-start" disabled>パイプライン実行</button>
        </div>
      </div>
      <div class="card">
        <h2>結果インポート</h2>
        <div class="import-area" id="import-area">
          <p>パイプライン出力ファイルをドラッグ&ドロップ、またはクリックして選択</p>
          <p style="font-size:0.8rem;color:var(--text-muted);margin-top:0.5rem">.xlsx または .json</p>
          <input type="file" id="file-input" accept=".xlsx,.json">
        </div>
      </div>
      <div class="card">
        <h2>実行履歴</h2>
        <div id="runs-list">読み込み中...</div>
      </div>
    </div>`;

  setupPipelineForm();
  setupImport();
  loadRuns();
}

function setupPipelineForm() {
  const drop = $("#pipeline-drop");
  const fileInput = $("#pipeline-file");
  const startBtn = $("#pipeline-start");
  const fileNameEl = $("#pipeline-file-name");
  let selectedFile = null;

  drop.addEventListener("click", () => fileInput.click());
  drop.addEventListener("dragover", (e) => { e.preventDefault(); drop.classList.add("drag-over"); });
  drop.addEventListener("dragleave", () => drop.classList.remove("drag-over"));
  drop.addEventListener("drop", (e) => {
    e.preventDefault();
    drop.classList.remove("drag-over");
    if (e.dataTransfer.files.length) selectFile(e.dataTransfer.files[0]);
  });
  fileInput.addEventListener("change", () => {
    if (fileInput.files.length) selectFile(fileInput.files[0]);
  });

  function selectFile(file) {
    if (!file.name.endsWith(".xlsx")) {
      toast("Excel (.xlsx) ファイルを選択してください");
      return;
    }
    selectedFile = file;
    fileNameEl.textContent = file.name;
    fileNameEl.style.display = "block";
    drop.style.display = "none";
    startBtn.disabled = false;
  }

  startBtn.addEventListener("click", async () => {
    if (!selectedFile) return;
    startBtn.disabled = true;
    startBtn.textContent = "開始中...";

    // Update config if changed
    const kbDir = $("#pipeline-kb-dir").value;
    const model = $("#pipeline-model").value;
    const budget = parseInt($("#pipeline-budget").value);
    try {
      await api("/config", {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ kb_dir: kbDir, model: model, token_budget: budget }),
      });
    } catch (_) {}

    const form = new FormData();
    form.append("file", selectedFile);
    try {
      const res = await api("/pipeline/start", { method: "POST", body: form });
      const data = await res.json();
      navigate("pipeline", { jobId: data.job_id });
    } catch (e) {
      toast("パイプライン開始失敗: " + e.message);
      startBtn.disabled = false;
      startBtn.textContent = "パイプライン実行";
    }
  });
}

function setupImport() {
  const area = $("#import-area");
  const input = $("#file-input");
  area.addEventListener("click", () => input.click());
  area.addEventListener("dragover", (e) => { e.preventDefault(); area.classList.add("drag-over"); });
  area.addEventListener("dragleave", () => area.classList.remove("drag-over"));
  area.addEventListener("drop", (e) => {
    e.preventDefault();
    area.classList.remove("drag-over");
    if (e.dataTransfer.files.length) uploadFile(e.dataTransfer.files[0]);
  });
  input.addEventListener("change", () => {
    if (input.files.length) uploadFile(input.files[0]);
  });
}

async function uploadFile(file) {
  const form = new FormData();
  form.append("file", file);
  try {
    const res = await api("/runs/import", { method: "POST", body: form });
    const data = await res.json();
    toast(data.message);
    navigate("run", { runId: data.run_id });
  } catch (e) {
    toast("インポート失敗: " + e.message);
  }
}

async function loadRuns() {
  const el = $("#runs-list");
  try {
    const res = await api("/runs");
    const runs = await res.json();
    if (!runs.length) {
      el.innerHTML = "<p style='color:var(--text-muted)'>まだ実行結果がありません</p>";
      return;
    }
    el.innerHTML = runs.map(r => {
      const total = r.total_questions || 1;
      const aPct = ((r.approved_count / total) * 100).toFixed(0);
      const rPct = ((r.rejected_count / total) * 100).toFixed(0);
      const pPct = (100 - aPct - rPct).toFixed(0);
      return `
        <div class="run-item" data-id="${r.id}">
          <div>
            <strong>${r.name}</strong>
            <div class="run-meta">${formatDate(r.imported_at)} / ${r.total_questions}問</div>
            <div class="progress-bar" style="width:200px;margin-top:0.3rem">
              <div class="segment approved" style="width:${aPct}%"></div>
              <div class="segment rejected" style="width:${rPct}%"></div>
              <div class="segment pending" style="width:${pPct}%"></div>
            </div>
          </div>
          <div>
            <span class="badge badge-approved">${r.approved_count}</span>
            <span class="badge badge-pending">${r.pending_count}</span>
          </div>
        </div>`;
    }).join("");
    el.querySelectorAll(".run-item").forEach(item => {
      item.addEventListener("click", () => navigate("run", { runId: parseInt(item.dataset.id) }));
    });
  } catch (e) {
    el.innerHTML = `<p style="color:var(--danger)">読み込みエラー: ${e.message}</p>`;
  }
}

async function renderPipeline() {
  const { jobId } = state;
  const app = $("#app");
  app.innerHTML = `
    <div class="container">
      <a class="back-link" onclick="navigate('home')">&larr; ホームに戻る</a>
      <div class="card">
        <h2>パイプライン実行中</h2>
        <div class="pipeline-progress" id="pipeline-progress">
          <div class="pipeline-spinner"></div>
          <p>接続中...</p>
        </div>
        <div id="pipeline-log" class="pipeline-log"></div>
      </div>
    </div>`;

  const logEl = $("#pipeline-log");
  const progressEl = $("#pipeline-progress");

  // Try SSE first, fall back to polling
  try {
    const evtSource = new EventSource(`${API}/pipeline/${jobId}/progress`);

    evtSource.addEventListener("progress", (e) => {
      const line = document.createElement("div");
      line.className = "pipeline-log-line";
      line.textContent = e.data;
      logEl.appendChild(line);
      logEl.scrollTop = logEl.scrollHeight;
      progressEl.innerHTML = `<div class="pipeline-spinner"></div><p>${e.data}</p>`;
    });

    evtSource.addEventListener("done", (e) => {
      evtSource.close();
      const runId = parseInt(e.data);
      progressEl.innerHTML = `<p style="color:var(--success);font-weight:600">完了しました</p>`;
      const line = document.createElement("div");
      line.className = "pipeline-log-line done";
      line.textContent = "パイプライン完了";
      logEl.appendChild(line);
      setTimeout(() => navigate("run", { runId }), 1500);
    });

    evtSource.addEventListener("error", (e) => {
      if (e.data) {
        evtSource.close();
        progressEl.innerHTML = `<p style="color:var(--danger);font-weight:600">エラー: ${e.data}</p>`;
        const line = document.createElement("div");
        line.className = "pipeline-log-line error";
        line.textContent = "エラー: " + e.data;
        logEl.appendChild(line);
      }
    });

    evtSource.onerror = () => {
      // SSE connection error — fall back to polling
      evtSource.close();
      pollJobStatus(jobId, logEl, progressEl);
    };
  } catch (_) {
    pollJobStatus(jobId, logEl, progressEl);
  }
}

async function pollJobStatus(jobId, logEl, progressEl) {
  let lastLen = 0;
  const poll = async () => {
    try {
      const res = await api(`/pipeline/${jobId}/status`);
      const job = await res.json();

      // Render new log lines
      for (let i = lastLen; i < job.progress.length; i++) {
        const line = document.createElement("div");
        line.className = "pipeline-log-line";
        line.textContent = job.progress[i];
        logEl.appendChild(line);
      }
      lastLen = job.progress.length;
      logEl.scrollTop = logEl.scrollHeight;

      if (job.status === "done") {
        progressEl.innerHTML = `<p style="color:var(--success);font-weight:600">完了しました</p>`;
        setTimeout(() => navigate("run", { runId: job.result_run_id }), 1500);
        return;
      }
      if (job.status === "error") {
        progressEl.innerHTML = `<p style="color:var(--danger);font-weight:600">エラー: ${job.error}</p>`;
        return;
      }

      if (job.progress.length > 0) {
        progressEl.innerHTML = `<div class="pipeline-spinner"></div><p>${job.progress[job.progress.length - 1]}</p>`;
      }

      setTimeout(poll, 1000);
    } catch (e) {
      progressEl.innerHTML = `<p style="color:var(--danger)">通信エラー: ${e.message}</p>`;
    }
  };
  poll();
}

async function renderRun() {
  const { runId } = state;
  const app = $("#app");
  app.innerHTML = `<div class="container"><p>読み込み中...</p></div>`;

  try {
    const [runRes, statsRes, answersRes] = await Promise.all([
      api(`/runs/${runId}`),
      api(`/runs/${runId}/stats`),
      api(`/runs/${runId}/answers`),
    ]);
    const [run, stats, answers] = await Promise.all([
      runRes.json(), statsRes.json(), answersRes.json(),
    ]);

    const total = stats.total || 1;
    app.innerHTML = `
      <div class="container">
        <a class="back-link" onclick="navigate('home')">&larr; 実行履歴に戻る</a>
        <h2 style="margin-bottom:1rem">${run.name}</h2>

        <div class="stats-grid">
          <div class="stat-card">
            <div class="value">${stats.total}</div>
            <div class="label">全質問</div>
          </div>
          <div class="stat-card">
            <div class="value" style="color:var(--success)">${stats.approved}</div>
            <div class="label">承認済み</div>
          </div>
          <div class="stat-card">
            <div class="value" style="color:var(--warning)">${stats.needs_revision}</div>
            <div class="label">要修正</div>
          </div>
          <div class="stat-card">
            <div class="value" style="color:var(--danger)">${stats.rejected}</div>
            <div class="label">却下</div>
          </div>
          <div class="stat-card">
            <div class="value">${stats.pending}</div>
            <div class="label">未レビュー</div>
          </div>
          <div class="stat-card">
            <div class="value">${stats.review_notes_count}</div>
            <div class="label">
              <a style="color:var(--primary);cursor:pointer" onclick="navigate('notes',{runId:${runId}})">
                レビュー指摘
              </a>
            </div>
          </div>
        </div>

        <div class="progress-bar" style="margin-bottom:1.5rem">
          <div class="segment approved" style="width:${(stats.approved/total*100)}%"></div>
          <div class="segment rejected" style="width:${(stats.rejected/total*100)}%"></div>
          <div class="segment needs_revision" style="width:${(stats.needs_revision/total*100)}%"></div>
          <div class="segment pending" style="width:${(stats.pending/total*100)}%"></div>
        </div>

        <div class="card">
          <div class="toolbar">
            <select id="filter-review">
              <option value="">全レビューステータス</option>
              <option value="pending">未レビュー</option>
              <option value="approved">承認済み</option>
              <option value="needs_revision">要修正</option>
              <option value="rejected">却下</option>
            </select>
            <select id="filter-confidence">
              <option value="">全確信度</option>
              <option value="high">high</option>
              <option value="medium">medium</option>
              <option value="low">low</option>
              <option value="past_answer">past_answer</option>
            </select>
            <div style="flex:1"></div>
            <div class="btn-group">
              <button class="btn btn-success btn-sm" id="bulk-approve">全件承認</button>
              <button class="btn btn-outline btn-sm" id="btn-export">Excel出力</button>
            </div>
          </div>
          <table>
            <thead>
              <tr>
                <th>No.</th>
                <th>大分類</th>
                <th>質問（抜粋）</th>
                <th>確信度</th>
                <th>ステータス</th>
                <th>レビュー</th>
              </tr>
            </thead>
            <tbody id="answers-body"></tbody>
          </table>
        </div>
      </div>`;

    const tbody = $("#answers-body");
    function renderRows(list) {
      tbody.innerHTML = list.map(a => `
        <tr data-qno="${a.question_no}">
          <td>${a.question_no}</td>
          <td>${a.major}</td>
          <td title="${a.question}">${a.question.slice(0, 40)}${a.question.length > 40 ? "..." : ""}</td>
          <td>${confidenceBadge(a.confidence)}</td>
          <td>${a.status}</td>
          <td>${reviewBadge(a.review_status)}</td>
        </tr>`).join("");
      tbody.querySelectorAll("tr").forEach(tr => {
        tr.addEventListener("click", () => {
          navigate("answer", { runId, questionNo: parseInt(tr.dataset.qno) });
        });
      });
    }

    renderRows(answers);

    // Filters
    function applyFilters() {
      const rv = $("#filter-review").value;
      const cf = $("#filter-confidence").value;
      const filtered = answers.filter(a =>
        (!rv || a.review_status === rv) && (!cf || a.confidence === cf)
      );
      renderRows(filtered);
    }
    $("#filter-review").addEventListener("change", applyFilters);
    $("#filter-confidence").addEventListener("change", applyFilters);

    // Bulk approve
    $("#bulk-approve").addEventListener("click", async () => {
      if (!confirm("未承認の全回答を承認しますか？")) return;
      const unapprovedNos = answers.filter(a => a.review_status !== "approved").map(a => a.question_no);
      if (!unapprovedNos.length) { toast("未承認の回答はありません"); return; }
      await api(`/runs/${runId}/bulk-review`, {
        method: "PUT",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ status: "approved", question_nos: unapprovedNos }),
      });
      toast(`${unapprovedNos.length}件を承認しました`);
      renderRun();
    });

    // Export
    $("#btn-export").addEventListener("click", () => {
      window.open(`${API}/runs/${runId}/export`);
    });
  } catch (e) {
    app.innerHTML = `<div class="container"><p style="color:var(--danger)">エラー: ${e.message}</p></div>`;
  }
}

async function renderAnswer() {
  const { runId, questionNo } = state;
  const app = $("#app");
  app.innerHTML = `<div class="container"><p>読み込み中...</p></div>`;

  try {
    const [res, allRes] = await Promise.all([
      api(`/runs/${runId}/answers/${questionNo}`),
      api(`/runs/${runId}/answers`),
    ]);
    const [a, allAnswers] = await Promise.all([res.json(), allRes.json()]);
    const notes = a.review_notes || [];
    const qNos = allAnswers.map(x => x.question_no).sort((a, b) => a - b);
    const curIdx = qNos.indexOf(questionNo);
    const prevNo = curIdx > 0 ? qNos[curIdx - 1] : null;
    const nextNo = curIdx < qNos.length - 1 ? qNos[curIdx + 1] : null;

    app.innerHTML = `
      <div class="container">
        <a class="back-link" onclick="navigate('run',{runId:${runId}})">&larr; 回答一覧に戻る</a>

        <div class="card">
          <div style="display:flex;justify-content:space-between;align-items:flex-start;flex-wrap:wrap;gap:0.5rem">
            <h2>Q${a.question_no}: ${a.major} &gt; ${a.minor}</h2>
            <div>${confidenceBadge(a.confidence)} ${reviewBadge(a.review_status)}</div>
          </div>
        </div>

        <div class="detail-grid">
          <div class="card">
            <h3>質問</h3>
            <div class="answer-text">${a.question}</div>
          </div>
          <div class="card">
            <h3>回答</h3>
            <div class="answer-text">${a.answer || "<em>（回答なし）</em>"}</div>
          </div>
        </div>

        <div class="detail-grid">
          <div class="card">
            <div class="detail-label">対応状況</div>
            <div class="detail-value">${a.status || "-"}</div>
            <div class="detail-label">根拠ソース</div>
            <div class="detail-value">${a.source_references.length ? a.source_references.join(", ") : "-"}</div>
            <div class="detail-label">備考フラグ</div>
            <div class="detail-value">${a.flag || "-"}</div>
            ${a.key_excerpt ? `<div class="detail-label">重要抜粋</div><div class="detail-value answer-text" style="font-size:0.85rem">${a.key_excerpt}</div>` : ""}
          </div>
          <div class="card">
            <h3>レビュー指摘 (${notes.length}件)</h3>
            ${notes.length ? notes.map(n => `
              <div style="margin-bottom:0.75rem;padding:0.5rem;background:#f8f9fa;border-radius:6px">
                <div>
                  <span class="severity-dot ${n.severity}"></span>
                  <strong>${n.issue_type}</strong>
                  <span class="badge badge-${n.severity}" style="margin-left:0.25rem">${n.severity}</span>
                </div>
                <div style="margin-top:0.25rem;font-size:0.85rem">${n.description}</div>
                ${n.suggestion ? `<div style="margin-top:0.25rem;font-size:0.8rem;color:var(--text-muted)">提案: ${n.suggestion}</div>` : ""}
              </div>`).join("") : "<p style='color:var(--text-muted)'>指摘なし</p>"}
          </div>
        </div>

        <div class="card">
          <h3>レビュー判定</h3>
          <textarea id="review-comment" placeholder="コメント（任意）">${a.review_comment || ""}</textarea>
          <div class="btn-group" style="margin-top:0.75rem">
            <button class="btn btn-success" data-status="approved">承認</button>
            <button class="btn btn-warning" data-status="needs_revision">要修正</button>
            <button class="btn btn-danger" data-status="rejected">却下</button>
            <button class="btn btn-outline" data-status="pending">保留に戻す</button>
          </div>
          ${a.reviewed_at ? `<div style="margin-top:0.5rem;font-size:0.8rem;color:var(--text-muted)">最終レビュー: ${formatDate(a.reviewed_at)}</div>` : ""}
        </div>

        <div style="display:flex;justify-content:space-between;margin-bottom:2rem">
          ${prevNo !== null ? `<button class="btn btn-outline" id="prev-q">&larr; 前の質問</button>` : `<div></div>`}
          ${nextNo !== null ? `<button class="btn btn-outline" id="next-q">次の質問 &rarr;</button>` : `<div></div>`}
        </div>
      </div>`;

    // Review buttons
    $$(".btn-group [data-status]").forEach(btn => {
      btn.addEventListener("click", async () => {
        const comment = $("#review-comment").value;
        await api(`/runs/${runId}/answers/${questionNo}/review`, {
          method: "PUT",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ status: btn.dataset.status, comment }),
        });
        toast(`Q${questionNo}: ${btn.dataset.status}`);
        renderAnswer();
      });
    });

    // Navigation
    const prevBtn = $("#prev-q");
    const nextBtn = $("#next-q");
    if (prevBtn) prevBtn.addEventListener("click", () => navigate("answer", { runId, questionNo: prevNo }));
    if (nextBtn) nextBtn.addEventListener("click", () => navigate("answer", { runId, questionNo: nextNo }));
  } catch (e) {
    app.innerHTML = `<div class="container"><p style="color:var(--danger)">エラー: ${e.message}</p></div>`;
  }
}

async function renderNotes() {
  const { runId } = state;
  const app = $("#app");
  app.innerHTML = `<div class="container"><p>読み込み中...</p></div>`;

  try {
    const res = await api(`/runs/${runId}/review-notes`);
    const notes = await res.json();

    app.innerHTML = `
      <div class="container">
        <a class="back-link" onclick="navigate('run',{runId:${runId}})">&larr; ダッシュボードに戻る</a>
        <div class="card">
          <h2>レビュー指摘一覧 (${notes.length}件)</h2>
          ${notes.length ? `<table>
            <thead>
              <tr>
                <th>Q No.</th>
                <th>種別</th>
                <th>重大度</th>
                <th>説明</th>
                <th>提案</th>
              </tr>
            </thead>
            <tbody>
              ${notes.map(n => `
                <tr data-qno="${n.question_no}">
                  <td>${n.question_no}</td>
                  <td>${n.issue_type}</td>
                  <td><span class="severity-dot ${n.severity}"></span>${n.severity}</td>
                  <td>${n.description}</td>
                  <td>${n.suggestion || "-"}</td>
                </tr>`).join("")}
            </tbody>
          </table>` : "<p style='color:var(--text-muted)'>指摘なし</p>"}
        </div>
      </div>`;

    $$("tr[data-qno]").forEach(tr => {
      tr.addEventListener("click", () => {
        navigate("answer", { runId, questionNo: parseInt(tr.dataset.qno) });
      });
    });
  } catch (e) {
    app.innerHTML = `<div class="container"><p style="color:var(--danger)">エラー: ${e.message}</p></div>`;
  }
}

// --- Init ---
document.addEventListener("DOMContentLoaded", () => {
  state = parseHash();
  render();
});
