const STORAGE_KEY = "echochamber.research.access.v1";
let memoryKey;
export function dataKey(create = false) {
  try {
    const saved = localStorage.getItem(STORAGE_KEY);
    if (/^[a-f0-9]{64}$/.test(saved || "")) return saved;
  } catch {
    /* Private browsing may disallow persistent storage. */
  }
  if (memoryKey) return memoryKey;
  if (!create) return null;
  memoryKey = Array.from(crypto.getRandomValues(new Uint8Array(32)), (n) =>
    n.toString(16).padStart(2, "0"),
  ).join("");
  try {
    localStorage.setItem(STORAGE_KEY, memoryKey);
  } catch {
    /* Keep this session usable. */
  }
  return memoryKey;
}
export function dataHeaders(create = false) {
  const key = dataKey(create);
  return key ? { "X-Dataset-Key": key } : {};
}
export async function researchApi(path, options = {}) {
  const response = await fetch(`/api${path}`, {
    ...options,
    headers: {
      "Content-Type": "application/json",
      ...dataHeaders(true),
      ...options.headers,
    },
  });
  if (response.status === 204) return null;
  const result = await response.json().catch(() => ({}));
  if (!response.ok) {
    const error = new Error(
      typeof result.detail === "string"
        ? result.detail
        : "요청에 실패했습니다. 입력값과 서버 연결을 확인해 주세요.",
    );
    error.retryAfter = Number(response.headers.get("Retry-After")) || 0;
    throw error;
  }
  return result;
}
export async function analyzeDataset(id, signal, onData) {
  const response = await fetch(`/api/datasets/${id}/analyze`, {
    method: "POST",
    headers: dataHeaders(true),
    signal,
  });
  if (!response.ok) {
    const result = await response.json().catch(() => ({}));
    throw new Error(
      typeof result.detail === "string"
        ? result.detail
        : "분석을 시작하지 못했습니다.",
    );
  }
  const reader = response.body.getReader(),
    decoder = new TextDecoder();
  let buffer = "",
    complete = false;
  try {
    while (true) {
      const { done, value } = await reader.read();
      buffer += decoder.decode(value, { stream: !done });
      let boundary;
      while ((boundary = buffer.indexOf("\n\n")) >= 0) {
        const frame = buffer.slice(0, boundary);
        buffer = buffer.slice(boundary + 2);
        const kind = frame.match(/^event: (.+)$/m)?.[1],
          body = frame.match(/^data: (.+)$/m)?.[1];
        if (!body) continue;
        const result = JSON.parse(body);
        if (kind === "error") throw new Error(result.detail);
        if (["start", "row", "complete"].includes(kind)) onData(result);
        if (kind === "complete") complete = true;
      }
      if (done) break;
    }
    if (!complete)
      throw new Error(
        "연결이 종료됐습니다. 저장된 결과를 불러온 뒤 이어서 분석해 주세요.",
      );
  } finally {
    await reader.cancel().catch(() => {});
  }
}
