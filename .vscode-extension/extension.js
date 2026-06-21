const vscode = require("vscode");

/** @param {vscode.ExtensionContext} context */
function activate(context) {
  const output = vscode.window.createOutputChannel("Verdict");

  const apiUrl = () =>
    vscode.workspace.getConfiguration("verdict").get("apiUrl", "http://localhost:8000");

  const planPath = () =>
    vscode.workspace.getConfiguration("verdict").get("planPath", "plan.md");

  function log(msg) {
    output.appendLine(`[${new Date().toLocaleTimeString()}] ${msg}`);
  }

  async function ensureServer() {
    try {
      const resp = await fetch(`${apiUrl()}/health`);
      const data = await resp.json();
      if (data.status !== "ok") throw new Error("Server not healthy");
      return true;
    } catch (e) {
      const action = await vscode.window.showErrorMessage(
        `Verdict server not running at ${apiUrl()}`,
        "Start Server",
        "Docker Compose"
      );
      if (action === "Start Server") {
        const terminal = vscode.window.createTerminal("Verdict Server");
        terminal.sendText(`cd "${vscode.workspace.rootPath}" && python -m verdict_mcp.api_server`);
        terminal.show();
      } else if (action === "Docker Compose") {
        const terminal = vscode.window.createTerminal("Verdict Docker");
        terminal.sendText(`cd "${vscode.workspace.rootPath}" && docker-compose up verdict-mcp`);
        terminal.show();
      }
      return false;
    }
  }

  async function initPlan() {
    const plan = planPath();
    const resp = await fetch(`${apiUrl()}/plan/init`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ plan_file_path: plan }),
    });
    return resp.json();
  }

  function getRelativePath(filePath) {
    const ws = vscode.workspace.rootPath;
    if (!ws) return filePath;
    return filePath.startsWith(ws) ? filePath.slice(ws.length + 1).replace(/\\/g, "/") : filePath;
  }

  async function runAudit() {
    const editor = vscode.window.activeTextEditor;
    if (!editor) return vscode.window.showWarningMessage("No file open");

    if (!(await ensureServer())) return;

    const filePath = getRelativePath(editor.document.uri.fsPath);
    await vscode.window.withProgress(
      { location: vscode.ProgressLocation.Notification, title: "Verdict: Auditing..." },
      async () => {
        try {
          await initPlan();
          const resp = await fetch(`${apiUrl()}/audit`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ task_id: "TASK_001", file_paths: [filePath] }),
          });
          const result = await resp.json();

          if (result.success) {
            vscode.window.showInformationMessage("✅ Verdict audit passed!");
          } else {
            const errors = result.file_results?.flatMap((f) => f.errors) || [];
            const msg = `❌ Audit failed: ${errors.length} errors`;
            const view = await vscode.window.showErrorMessage(msg, "View Details");
            if (view) {
              log("=== AUDIT REPORT ===");
              log(JSON.stringify(result, null, 2));
              output.show();
            }
          }
        } catch (e) {
          vscode.window.showErrorMessage(`Verdict error: ${e.message}`);
        }
      }
    );
  }

  async function runPipeline() {
    if (!(await ensureServer())) return;

    const editor = vscode.window.activeTextEditor;
    const currentFile = editor ? getRelativePath(editor.document.uri.fsPath) : null;

    const sourceFiles = await vscode.window.showInputBox({
      prompt: "Source files (comma-separated)",
      value: currentFile || "",
    });
    if (!sourceFiles) return;

    const testFile = await vscode.window.showInputBox({
      prompt: "Test file path",
      value: "tests/test_" + sourceFiles.split(",")[0].trim(),
    });
    if (!testFile) return;

    const targetFile = await vscode.window.showInputBox({
      prompt: "Target file for coverage",
      value: sourceFiles.split(",")[0].trim(),
    });
    if (!targetFile) return;

    const uiFile = await vscode.window.showInputBox({
      prompt: "UI file (optional, press Enter to skip)",
      value: "",
    });

    await vscode.window.withProgress(
      {
        location: vscode.ProgressLocation.Notification,
        title: "Verdict: Running full pipeline...",
      },
      async () => {
        try {
          await initPlan();
          const body = {
            task_id: "TASK_001",
            source_files: sourceFiles.split(",").map((s) => s.trim()),
            test_file: testFile,
            target_file: targetFile,
          };
          if (uiFile) body.ui_file = uiFile;

          const resp = await fetch(`${apiUrl()}/pipeline/run`, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(body),
          });
          const result = await resp.json();

          log("=== PIPELINE RESULT ===");
          log(JSON.stringify(result, null, 2));

          if (result.overall_success) {
            vscode.window.showInformationMessage("✅ Verdict pipeline passed!");
          } else {
            const failed = result.steps?.filter((s) => !s.success) || [];
            const msg = `❌ Pipeline failed: ${failed.map((s) => s.name).join(", ")}`;
            const view = await vscode.window.showErrorMessage(msg, "View Report");
            if (view) output.show();
          }
        } catch (e) {
          vscode.window.showErrorMessage(`Verdict error: ${e.message}`);
        }
      }
    );
  }

  function showReport() {
    output.show();
  }

  async function initProject() {
    const name = await vscode.window.showInputBox({
      prompt: "Project name",
      placeHolder: "my-verdict-project",
    });
    if (!name) return;

    const terminal = vscode.window.createTerminal("Verdict Init");
    terminal.sendText(`verdict init "${name}"`);
    terminal.show();
  }

  context.subscriptions.push(
    vscode.commands.registerCommand("verdict.runAudit", runAudit),
    vscode.commands.registerCommand("verdict.runPipeline", runPipeline),
    vscode.commands.registerCommand("verdict.showReport", showReport),
    vscode.commands.registerCommand("verdict.initProject", initProject),

    vscode.workspace.onDidSaveTextDocument(async (doc) => {
      const auto = vscode.workspace.getConfiguration("verdict").get("autoAuditOnSave", false);
      if (auto && doc.languageId === "python") {
        await runAudit();
      }
    })
  );

  log("Verdict extension activated");
}

function deactivate() {}

module.exports = { activate, deactivate };
