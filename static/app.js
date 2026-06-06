const form = document.querySelector("#uploadForm");
const input = document.querySelector("#pdfInput");
const fileName = document.querySelector("#fileName");
const submitButton = document.querySelector("#submitButton");
const statusPanel = document.querySelector("#statusPanel");
const loginPanel = document.querySelector("#loginPanel");
const loginButton = document.querySelector("#loginButton");
const statusTitle = document.querySelector("#statusTitle");
const statusMessage = document.querySelector("#statusMessage");
const progressText = document.querySelector("#progressText");
const progressBar = document.querySelector("#progressBar");
const downloadLink = document.querySelector("#downloadLink");

let pendingPoll = null;

input.addEventListener("change", () => {
  fileName.textContent = input.files[0]?.name || "拖拽 PDF 到这里，或点击上传";
});

form.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (!input.files[0]) {
    showStatus("请选择 PDF 文件", "请先上传 20 页以内、20MB 以内的 PDF。", 0, true);
    return;
  }

  submitButton.disabled = true;
  loginPanel.classList.add("hidden");
  downloadLink.classList.add("hidden");
  showStatus("正在上传文件", "正在提交 PDF。", 8, false);

  const body = new FormData(form);
  try {
    const response = await fetch("/api/jobs", { method: "POST", body });
    const data = await response.json();
    if (!response.ok) {
      submitButton.disabled = false;
      if (data.error === "login_required") {
        loginPanel.classList.remove("hidden");
      }
      showStatus("无法开始翻译", data.message || "请稍后再试。", 0, true);
      return;
    }

    pollJob(data.id);
  } catch (error) {
    submitButton.disabled = false;
    showStatus("网络异常", "提交失败，请刷新页面后重试。", 0, true);
  }
});

loginButton.addEventListener("click", async () => {
  loginButton.disabled = true;
  try {
    const response = await fetch("/api/login", { method: "POST" });
    if (response.ok) {
      loginPanel.classList.add("hidden");
      showStatus("已登录", "可以继续提交新的 PDF。", 0, false);
    } else {
      showStatus("登录失败", "请稍后再试。", 0, true);
    }
  } finally {
    loginButton.disabled = false;
  }
});

async function pollJob(jobId) {
  clearTimeout(pendingPoll);
  try {
    const response = await fetch(`/api/jobs/${jobId}`);
    const data = await response.json();
    if (!response.ok) {
      submitButton.disabled = false;
      showStatus("任务不存在", data.message || "请重新提交。", 0, true);
      return;
    }

    renderJob(data);
    if (data.status === "completed" || data.status === "failed") {
      submitButton.disabled = false;
      return;
    }
    pendingPoll = setTimeout(() => pollJob(jobId), 1800);
  } catch (error) {
    pendingPoll = setTimeout(() => pollJob(jobId), 3000);
  }
}

function renderJob(job) {
  const titleByStatus = {
    validating: "正在分析 PDF",
    translating: "正在翻译文本",
    generating: "正在生成译文 PDF",
    completed: "翻译完成",
    failed: "翻译失败"
  };
  showStatus(titleByStatus[job.status] || "正在处理", job.message, job.progress, job.status === "failed");
  if (job.status === "completed" && job.download_url) {
    downloadLink.href = job.download_url;
    downloadLink.classList.remove("hidden");
  }
}

function showStatus(title, message, progress, isError) {
  statusPanel.classList.remove("hidden");
  statusTitle.textContent = title;
  statusMessage.textContent = message;
  statusMessage.classList.toggle("error", Boolean(isError));
  const value = Math.max(0, Math.min(100, Number(progress) || 0));
  progressText.textContent = `${value}%`;
  progressBar.style.width = `${value}%`;
}
