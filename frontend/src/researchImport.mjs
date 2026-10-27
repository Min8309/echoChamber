import { redactText } from "./csv.mjs";

// Read only the first 30 JSON array/JSONL objects; never parse a whole corpus.
export async function previewResearchFile(file, provider) {
  const reader = file.stream().getReader(),
    decoder = new TextDecoder("utf-8", { fatal: true });
  const records = [];
  let depth = 0,
    quoted = false,
    escaped = false,
    current = "",
    started = false;
  try {
    while (records.length < 30) {
      const { done, value } = await reader.read();
      const chunk = decoder.decode(value, { stream: !done });
      for (const char of chunk) {
        if (!started) {
          if (char === "{") {
            started = true;
            depth = 1;
            current = "{";
          } else if (!/[\s\uFEFF\[,]/.test(char) && char !== "]")
            throw new Error("JSON 배열 또는 JSONL 파일을 선택해 주세요.");
          continue;
        }
        current += char;
        if (current.length > 250000)
          throw new Error(
            "한 레코드가 너무 큽니다. 필요한 댓글만 추출한 파일을 사용해 주세요.",
          );
        if (quoted) {
          if (escaped) escaped = false;
          else if (char === "\\") escaped = true;
          else if (char === '"') quoted = false;
        } else if (char === '"') quoted = true;
        else if (char === "{") depth++;
        else if (char === "}") {
          depth--;
          if (depth === 0) {
            records.push(JSON.parse(current));
            current = "";
            started = false;
            if (records.length === 30) break;
          }
        }
      }
      if (done) {
        if (started) throw new Error("닫히지 않은 JSON 레코드가 있습니다.");
        break;
      }
    }
  } finally {
    await reader.cancel().catch(() => {});
  }
  if (!records.length) throw new Error("댓글 레코드를 찾지 못했습니다.");
  const rows = records.map((record, index) => {
    const raw =
      provider === "kold" ? record.comment : (record.text ?? record.Text);
    if (typeof raw !== "string" || !raw.trim() || raw.length > 3000)
      throw new Error(
        `${index + 1}번째 레코드의 text/comment를 확인해 주세요. 문장은 3,000자 이하입니다.`,
      );
    const reference_labels = {};
    for (const key of ["label", "target_label", "OFF", "TGT", "GRP"])
      if (record[key] != null)
        reference_labels[key] = (
          typeof record[key] === "string"
            ? record[key]
            : JSON.stringify(record[key])
        ).slice(0, 300);
    // No annotator IDs, raw_labels, original row IDs or rationale offsets survive.
    return {
      local_id: `research-${index + 1}`,
      text: redactText(raw),
      author: "",
      thread: null,
      reply_to_id: null,
      rating: null,
      date: null,
      reference_labels,
      selected: true,
    };
  });
  return {
    rows,
    total: rows.length,
    file_provider: provider,
    origin: null,
    collection_token: null,
  };
}
