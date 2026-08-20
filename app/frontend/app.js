const questionInput = document.getElementById("question");
const requestState = document.getElementById("requestState");
const form = document.getElementById("askForm");
const loadingLane = document.getElementById("loadingLane");
const resultsShell = document.getElementById("resultsShell");
const loadingTemplate = document.getElementById("loadingTemplate");
const rotationTimers = new Map();

async function renderMermaidDiagrams(root = document) {
  if (!window.mermaid) {
    return;
  }

  const diagrams = root.querySelectorAll(".mermaid");
  for (const diagram of diagrams) {
    if (diagram.dataset.processed === "true") {
      continue;
    }
    const source = diagram.textContent.trim();
    const id = `mermaid-${Math.random().toString(36).slice(2)}`;
    const { svg } = await window.mermaid.render(id, source);
    diagram.innerHTML = svg;
    diagram.dataset.processed = "true";
  }
}

function clearRotatorTimer(key) {
  if (!rotationTimers.has(key)) {
    return;
  }

  window.clearTimeout(rotationTimers.get(key));
  rotationTimers.delete(key);
}

function scheduleRotator(key, callback, delay) {
  clearRotatorTimer(key);
  const timer = window.setTimeout(callback, delay);
  rotationTimers.set(key, timer);
}

function startFadeRotator(rotator, items, key) {
  let index = items.indexOf(rotator.textContent.trim());
  if (index < 0) index = 0;
  rotator.textContent = items[index];

  const rotate = () => {
    index = (index + 1) % items.length;
    rotator.classList.add("is-transitioning");

    window.setTimeout(() => {
      rotator.textContent = items[index];
      rotator.classList.remove("is-transitioning");
      scheduleRotator(key, rotate, 3600);
    }, 240);
  };

  scheduleRotator(key, rotate, 3600);
}

function startRotators(root = document) {
  const rotators = root.querySelectorAll("[data-rotate-items]");
  rotators.forEach((rotator) => {
    const items = rotator.dataset.rotateItems
      .split("|")
      .map((item) => item.trim())
      .filter(Boolean);

    if (items.length <= 1) {
      return;
    }

    const key = rotator.dataset.rotateItems;
    clearRotatorTimer(key);

    startFadeRotator(rotator, items, key);
  });
}

function setExamplePrompt(event) {
  const target = event.target;
  if (!(target instanceof HTMLButtonElement)) {
    return;
  }
  questionInput.value = target.textContent;
  questionInput.focus();
}

function submitOnShortcut(event) {
  if ((event.ctrlKey || event.metaKey) && event.key === "Enter") {
    form.requestSubmit();
  }
}

document.getElementById("examples").addEventListener("click", setExamplePrompt);
questionInput.addEventListener("keydown", submitOnShortcut);

document.body.addEventListener("htmx:beforeRequest", () => {
  requestState.textContent = "Status: Running";
  form.classList.add("is-loading");
  loadingLane.classList.add("is-visible");
  if (loadingTemplate && resultsShell) {
    resultsShell.innerHTML = loadingTemplate.innerHTML;
  }
});

document.body.addEventListener("htmx:afterRequest", (event) => {
  requestState.textContent = event.detail.successful ? "Status: Complete" : "Status: Failed";
  form.classList.remove("is-loading");
  loadingLane.classList.remove("is-visible");
});

document.body.addEventListener("htmx:afterSwap", async (event) => {
  await renderMermaidDiagrams(event.target);
  startRotators(event.target);
});

renderMermaidDiagrams();
startRotators();
