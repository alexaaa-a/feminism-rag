import { esc } from "./ui.js";

const HEADING = /^(#{1,4})\s+(.*)$/;
const BULLET = /^[-*•]\s+(.*)$/;
const NUMBERED = /^(\d{1,2})[.)]\s+(.*)$/;

export function renderMarkdown(text, decorate = (value) => value) {
  const lines = String(text ?? "").replace(/\r\n?/g, "\n").split("\n");
  const blocks = [];
  let paragraph = [];
  let list = null;

  const dress = (line) => decorate(inline(line));

  function closeParagraph() {
    if (!paragraph.length) return;
    blocks.push(`<p>${paragraph.map(dress).join("<br>")}</p>`);
    paragraph = [];
  }

  function closeList() {
    if (!list) return;
    const items = list.items.map((item) => `<li>${dress(item)}</li>`).join("");
    blocks.push(`<${list.tag}>${items}</${list.tag}>`);
    list = null;
  }

  function openList(tag, item) {
    closeParagraph();
    if (!list || list.tag !== tag) {
      closeList();
      list = { tag, items: [] };
    }
    list.items.push(item);
  }

  for (const raw of lines) {
    const line = raw.trim();

    if (!line) {
      closeParagraph();
      closeList();
      continue;
    }

    const heading = line.match(HEADING);
    if (heading) {
      closeParagraph();
      closeList();
      blocks.push(`<p class="answer-heading">${dress(heading[2])}</p>`);
      continue;
    }

    const bullet = line.match(BULLET);
    if (bullet) {
      openList("ul", bullet[1]);
      continue;
    }

    const numbered = line.match(NUMBERED);
    if (numbered) {
      openList("ol", numbered[2]);
      continue;
    }

    if (list) {
      list.items[list.items.length - 1] += ` ${line}`;
      continue;
    }

    paragraph.push(line);
  }

  closeParagraph();
  closeList();
  return blocks.join("");
}

function inline(line) {
  let html = esc(line);
  html = html.replace(/`([^`]+)`/g, "<code>$1</code>");
  html = html.replace(/\*\*([^*]+)\*\*/g, "<strong>$1</strong>");
  html = html.replace(/__([^_]+)__/g, "<strong>$1</strong>");
  html = html.replace(/(^|[\s(«"])\*([^*]+)\*/g, "$1<em>$2</em>");
  html = html.replace(/(^|[\s(«"])_([^_]+)_/g, "$1<em>$2</em>");
  html = html.replace(
    /\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g,
    '<a href="$2" target="_blank" rel="noopener">$1</a>'
  );
  return html;
}
