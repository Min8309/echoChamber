import { test } from "node:test";
import assert from "node:assert/strict";
import { parseCSV, previewCSV, redactText } from "../frontend/src/csv.mjs";

test("CSV parses BOM, Korean quoted commas/newlines, and escaped quotes", () => {
  const rows = parseCSV(
    '\uFEFFtext,author_id\r\n"좋아요, 정말\n다음에도 ""방문""",person\r\n',
  );
  assert.equal(rows[0].text, '좋아요, 정말\n다음에도 "방문"');
});
test("preview removes raw identifiers and contact data before upload", () => {
  const result = previewCSV(
    "message_id,thread_id,author_id,reply_to_id,text,rating\na,private-group,private-author,,test@example.test 010-1234-5678 https://example.test,4\nb,private-group,private-author,a,좋나요?,5",
  );
  const serialized = JSON.stringify(result);
  for (const raw of [
    "private-group",
    "private-author",
    "test@example.test",
    "010-1234-5678",
    "https://example.test",
  ])
    assert.ok(!serialized.includes(raw));
  assert.equal(result.rows[0].author, result.rows[1].author);
  assert.equal(result.rows[1].reply_to_id, result.rows[0].local_id);
});
test("preview limits to 30 and rejects malformed/empty/mismatched data", () => {
  const result = previewCSV(
    "text\n" + Array.from({ length: 40 }, (_, i) => `문장${i}`).join("\n"),
  );
  assert.equal(result.rows.length, 30);
  assert.equal(result.total, 40);
  assert.throws(() => parseCSV('text\n"broken'), /따옴표/);
  assert.throws(() => parseCSV("text,id\ncontent"), /열 개수/);
  assert.throws(() => previewCSV("wrong\nhello"), /내용/);
  assert.throws(() => previewCSV("text,rating\nhello,10"), /별점/);
});
test("redaction handles common account and landline patterns", () => {
  assert.equal(
    redactText("문의 @test_user 02-1234-5678"),
    "문의 [계정] [전화번호]",
  );
});

test("direct text input uses the same pre-upload redaction and count bounds", async () => {
  const { previewTexts } = await import("../frontend/src/csv.mjs");
  const result = previewTexts("좋아요 test@example.test\n둘째 리뷰");
  assert.equal(result.rows.length, 2);
  assert.ok(result.rows[0].text.includes("[이메일]"));
  assert.throws(
    () => previewTexts(Array.from({ length: 31 }, () => "review").join("\n")),
    /30건/,
  );
});
