"use client";

import * as React from "react";
import { Check, Copy } from "lucide-react";

interface MarkdownViewProps {
  content: string;
  isStreaming?: boolean;
}

export function MarkdownView({ content, isStreaming = false }: MarkdownViewProps) {
  // Normalize streaming markdown: auto-close dangling triple backticks
  let text = content || "";
  if (isStreaming) {
    const fenceCount = (text.match(/^```/gm) || []).length;
    if (fenceCount % 2 === 1) {
      text += "\n```";
    }
  }

  const elements = React.useMemo(() => {
    return parseMarkdown(text);
  }, [text]);

  return <div className="space-y-3 leading-relaxed text-sm text-foreground/90">{elements}</div>;
}

function CodeBlock({ code, language }: { code: string; language: string }) {
  const [copied, setCopied] = React.useState(false);

  const handleCopy = async () => {
    try {
      await navigator.clipboard.writeText(code);
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    } catch {
      // ignore clipboard error
    }
  };

  return (
    <div className="my-3 overflow-hidden rounded-lg border border-border bg-[#0b0a08] font-mono text-xs shadow-md">
      <div className="flex items-center justify-between border-b border-border/40 bg-[#131110] px-3 py-1.5 text-[11px] text-muted-foreground">
        <span className="font-medium text-moss-400">
          {language || "code"}
        </span>
        <button
          onClick={handleCopy}
          className="flex items-center gap-1 rounded px-2 py-0.5 text-stone-300 hover:bg-stone-800 hover:text-white transition"
          title="Copy code"
        >
          {copied ? (
            <>
              <Check className="size-3 text-moss-400" />
              <span className="text-moss-400">Copied</span>
            </>
          ) : (
            <>
              <Copy className="size-3" />
              <span>Copy</span>
            </>
          )}
        </button>
      </div>
      <pre className="overflow-x-auto p-3 text-stone-200">
        <code>{code}</code>
      </pre>
    </div>
  );
}

function parseMarkdown(text: string): React.ReactNode[] {
  if (!text) return [];

  const lines = text.split("\n");
  const nodes: React.ReactNode[] = [];
  let inCodeBlock = false;
  let codeBlockLang = "";
  let codeBlockLines: string[] = [];
  let listItems: React.ReactNode[] = [];
  let listType: "ul" | "ol" | null = null;

  const flushList = () => {
    if (listItems.length > 0 && listType) {
      if (listType === "ul") {
        nodes.push(
          <ul key={`list-${nodes.length}`} className="list-disc pl-5 space-y-1 my-2">
            {listItems}
          </ul>
        );
      } else {
        nodes.push(
          <ol key={`list-${nodes.length}`} className="list-decimal pl-5 space-y-1 my-2">
            {listItems}
          </ol>
        );
      }
      listItems = [];
      listType = null;
    }
  };

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i];

    // Handle code block start / end
    if (line.trim().startsWith("```")) {
      flushList();
      if (inCodeBlock) {
        // End code block
        nodes.push(
          <CodeBlock
            key={`code-${nodes.length}`}
            code={codeBlockLines.join("\n")}
            language={codeBlockLang}
          />
        );
        inCodeBlock = false;
        codeBlockLines = [];
        codeBlockLang = "";
      } else {
        // Start code block
        inCodeBlock = true;
        codeBlockLang = line.trim().slice(3).trim();
        codeBlockLines = [];
      }
      continue;
    }

    if (inCodeBlock) {
      codeBlockLines.push(line);
      continue;
    }

    // Unordered list
    if (/^\s*[-*+]\s+/.test(line)) {
      if (listType !== "ul") flushList();
      listType = "ul";
      const itemContent = line.replace(/^\s*[-*+]\s+/, "");
      listItems.push(
        <li key={`li-${listItems.length}`}>{renderInlineFormatting(itemContent)}</li>
      );
      continue;
    }

    // Ordered list
    if (/^\s*\d+\.\s+/.test(line)) {
      if (listType !== "ol") flushList();
      listType = "ol";
      const itemContent = line.replace(/^\s*\d+\.\s+/, "");
      listItems.push(
        <li key={`li-${listItems.length}`}>{renderInlineFormatting(itemContent)}</li>
      );
      continue;
    }

    // Flush any pending list
    flushList();

    // Blank line
    if (line.trim() === "") {
      continue;
    }

    // Headings
    if (line.startsWith("### ")) {
      nodes.push(
        <h3 key={`h3-${i}`} className="text-base font-semibold text-foreground pt-2">
          {renderInlineFormatting(line.slice(4))}
        </h3>
      );
      continue;
    }
    if (line.startsWith("## ")) {
      nodes.push(
        <h2 key={`h2-${i}`} className="text-lg font-bold text-foreground border-b border-border/40 pb-1 pt-3">
          {renderInlineFormatting(line.slice(3))}
        </h2>
      );
      continue;
    }
    if (line.startsWith("# ")) {
      nodes.push(
        <h1 key={`h1-${i}`} className="text-xl font-extrabold text-foreground border-b border-border/40 pb-1 pt-3">
          {renderInlineFormatting(line.slice(2))}
        </h1>
      );
      continue;
    }

    // Blockquote
    if (line.startsWith("> ")) {
      nodes.push(
        <blockquote
          key={`quote-${i}`}
          className="border-l-2 border-moss-500 pl-3 my-2 text-muted-foreground italic text-xs"
        >
          {renderInlineFormatting(line.slice(2))}
        </blockquote>
      );
      continue;
    }

    // Paragraph
    nodes.push(
      <p key={`p-${i}`} className="leading-relaxed">
        {renderInlineFormatting(line)}
      </p>
    );
  }

  flushList();

  if (inCodeBlock && codeBlockLines.length > 0) {
    nodes.push(
      <CodeBlock
        key={`code-${nodes.length}`}
        code={codeBlockLines.join("\n")}
        language={codeBlockLang}
      />
    );
  }

  return nodes;
}

function renderInlineFormatting(text: string): React.ReactNode {
  // Regex to split by `code`, **bold**, *italic*
  const parts: React.ReactNode[] = [];
  const regex = /(`[^`]+`|\*\*[^*]+\*\*|\*[^*]+\*|\[[^\]]+\]\([^)]+\))/g;

  let lastIndex = 0;
  let match: RegExpExecArray | null;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    const token = match[0];
    if (token.startsWith("`") && token.endsWith("`")) {
      parts.push(
        <code
          key={`code-${match.index}`}
          className="rounded bg-muted px-1.5 py-0.5 font-mono text-xs font-medium text-moss-400"
        >
          {token.slice(1, -1)}
        </code>
      );
    } else if (token.startsWith("**") && token.endsWith("**")) {
      parts.push(
        <strong key={`bold-${match.index}`} className="font-semibold text-foreground">
          {token.slice(2, -2)}
        </strong>
      );
    } else if (token.startsWith("*") && token.endsWith("*")) {
      parts.push(
        <em key={`italic-${match.index}`} className="italic">
          {token.slice(1, -1)}
        </em>
      );
    } else if (token.startsWith("[") && token.includes("](")) {
      const linkMatch = token.match(/\[([^\]]+)\]\(([^)]+)\)/);
      if (linkMatch) {
        parts.push(
          <a
            key={`link-${match.index}`}
            href={linkMatch[2]}
            target="_blank"
            rel="noreferrer"
            className="text-moss-400 underline underline-offset-2 hover:text-moss-300"
          >
            {linkMatch[1]}
          </a>
        );
      } else {
        parts.push(token);
      }
    }

    lastIndex = match.index + token.length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length > 0 ? parts : text;
}

