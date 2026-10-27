// CSV parsing and redaction happen before any research upload request.
export function parseCSV(input) {
  const text = input.replace(/^\uFEFF/, "");
  const rows = [];
  let row = [],
    cell = "",
    quoted = false,
    closed = false;
  function finishCell() {
    row.push(cell);
    cell = "";
    closed = false;
    if (row.length > 32) throw new Error("CSV 열은 32개 이하로 준비해 주세요.");
  }
  function finishRow() {
    finishCell();
    if (row.some((value) => value.trim())) rows.push(row);
    row = [];
    if (rows.length > 501)
      throw new Error("CSV는 최대 500행으로 준비해 주세요.");
  }
  for (let i = 0; i < text.length; i++) {
    const char = text[i];
    if (quoted) {
      if (char === '"') {
        if (text[i + 1] === '"') {
          cell += '"';
          i++;
        } else {
          quoted = false;
          closed = true;
        }
      } else cell += char;
    } else if (char === '"' && !cell && !closed) quoted = true;
    else if (char === ",") finishCell();
    else if (char === "\n" || char === "\r") {
      if (char === "\r" && text[i + 1] === "\n") i++;
      finishRow();
    } else if (closed && !/\s/.test(char))
      throw new Error("CSV 따옴표 형식을 확인해 주세요.");
    else if (!closed) cell += char;
  }
  if (quoted) throw new Error("CSV의 닫히지 않은 따옴표를 확인해 주세요.");
  if (cell || row.length || closed) finishRow();
  if (rows.length < 2)
    throw new Error("헤더와 데이터가 포함된 CSV를 선택해 주세요.");
  const headers = rows.shift().map((value) => value.trim().toLowerCase());
  if (new Set(headers).size !== headers.length)
    throw new Error("중복된 CSV 헤더를 확인해 주세요.");
  return rows.map((values, index) => {
    if (values.length !== headers.length)
      throw new Error(`${index + 2}행의 열 개수가 헤더와 다릅니다.`);
    return Object.fromEntries(headers.map((key, i) => [key, values[i].trim()]));
  });
}
export function redactText(text) {
  return text
    .replace(/[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}/g, "[이메일]")
    .replace(
      /(?<!\d)(?:\+82[- .]?)?0?1[016789][- .]?\d{3,4}[- .]?\d{4}(?!\d)/g,
      "[전화번호]",
    )
    .replace(/(?<!\d)0[2-6][1-5]?[- .]\d{3,4}[- .]\d{4}(?!\d)/g, "[전화번호]")
    .replace(/https?:\/\/[^\s<>]+|www\.[^\s<>]+/gi, "[링크]")
    .replace(/(?<!\w)@[A-Za-z0-9_.-]+/g, "[계정]")
    .trim();
}
const pick = (row, keys) =>
  keys
    .map((key) => row[key])
    .find((value) => value !== undefined && value !== "") || "";
export function previewCSV(text) {
  const raw = parseCSV(text),
    authors = new Map(),
    threads = new Map(),
    ids = new Map();
  const selected = raw.slice(0, 30);
  const rawIds = selected.map(
    (row, index) =>
      pick(row, ["message_id", "comment_id", "review_id", "id"]) ||
      `line-${index}`,
  );
  if (new Set(rawIds).size !== rawIds.length)
    throw new Error("중복된 메시지 ID가 있습니다.");
  rawIds.forEach((id, index) => ids.set(id, `row-${index + 1}`));
  const rows = selected.map((row, index) => {
    const content = pick(row, [
      "text",
      "content",
      "comment",
      "review",
      "내용",
      "댓글",
      "리뷰",
    ]);
    if (!content.trim())
      throw new Error(
        `${index + 2}행의 내용이 비어 있습니다. text 또는 내용 열을 확인해 주세요.`,
      );
    if (content.length > 3000)
      throw new Error(`${index + 2}행은 3,000자 이하로 줄여 주세요.`);
    const author = pick(row, [
      "author_id",
      "author",
      "nickname",
      "reviewer",
      "작성자",
    ]);
    const thread = pick(row, ["thread_id", "article_id", "product_id"]);
    if (author && !authors.has(author))
      authors.set(author, `작성자 ${authors.size + 1}`);
    if (thread && !threads.has(thread))
      threads.set(thread, `묶음 ${threads.size + 1}`);
    const ratingText = pick(row, ["rating", "score", "별점", "평점"]),
      rating = ratingText ? Number(ratingText) : null;
    if (
      rating !== null &&
      (!Number.isFinite(rating) || rating < 0 || rating > 5)
    )
      throw new Error(`${index + 2}행의 별점은 0~5 숫자여야 합니다.`);
    const created = pick(row, ["created_at", "date", "작성일"]),
      date = /^\d{4}-\d{2}-\d{2}/.test(created) ? created.slice(0, 10) : null;
    const reference_labels = {};
    for (const [column, name] of [["label","label"],["target_label","target_label"],["off","OFF"],["tgt","TGT"],["grp","GRP"]]) if(row[column]) reference_labels[name] = row[column].slice(0,300);
    return {
      local_id: ids.get(rawIds[index]),
      reference_labels,
      text: redactText(content),
      author: authors.get(author) || "",
      thread: threads.get(thread) || null,
      reply_to_id: ids.get(pick(row, ["reply_to_id", "parent_id"])) || null,
      rating,
      date,
      selected: true,
    };
  });
  return { rows, total: raw.length };
}

export function previewTexts(input) {
  const lines = input
    .split(/\r?\n/)
    .map((line) => line.trim())
    .filter(Boolean);
  if (!lines.length) throw new Error("분석할 댓글·리뷰를 입력해 주세요.");
  if (lines.length > 30)
    throw new Error(
      "직접 입력은 최대 30건입니다. 한 줄에 한 건씩 입력해 주세요.",
    );
  const csv =
    "text\n" +
    lines.map((line) => '"' + line.replace(/"/g, '""') + '"').join("\n");
  return previewCSV(csv);
}
