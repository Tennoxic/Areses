const OPERATOR_PREFIXES = [
  "f:",
  "c:",
  "author:",
  "intitle:",
  "intext:",
  "inurl:",
  "date:",
  "pubdate:",
  "mdate:",
  "userdate:",
];

export function extractHighlightTerms(query) {
  if (!query) return [];
  const tokens = query.match(/"[^"]+"|\/[^/]+\/|\S+/g) || [];
  const terms = [];
  for (const raw of tokens) {
    const token = raw.replace(/^"|"$/g, "");
    if (token.startsWith("/") && token.endsWith("/")) continue;
    if (OPERATOR_PREFIXES.some((prefix) => token.toLowerCase().startsWith(prefix))) continue;
    if (["AND", "OR", "NOT"].includes(token)) continue;
    if (token.length < 2) continue;
    terms.push(token);
  }
  return terms;
}

function escapeRegExp(value) {
  return value.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
}

export function highlightText(text, terms) {
  if (!terms || terms.length === 0 || !text) return text;
  const pattern = new RegExp(`(${terms.map(escapeRegExp).join("|")})`, "gi");
  const parts = text.split(pattern);
  return parts.map((part, index) =>
    terms.some((term) => term.toLowerCase() === part.toLowerCase()) ? (
      <mark key={index}>{part}</mark>
    ) : (
      part
    )
  );
}
