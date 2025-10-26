// ABOUTME: Component for rendering markdown-formatted messages with syntax highlighting
// ABOUTME: Supports GitHub Flavored Markdown including code blocks, tables, and lists

import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import rehypeHighlight from 'rehype-highlight';
import type { Components } from 'react-markdown';
import 'highlight.js/styles/github-dark.css';

interface MarkdownMessageProps {
  content: string;
}

export function MarkdownMessage({ content }: MarkdownMessageProps) {
  const components: Components = {
    // Inline code styling
    code({ className, children, ...props }) {
      const isInline = !className;

      return isInline ? (
        <code className="bg-gray-200 px-1.5 py-0.5 rounded text-sm font-mono text-gray-800" {...props}>
          {children}
        </code>
      ) : (
        <code className={className} {...props}>
          {children}
        </code>
      );
    },
    // Code block wrapper
    pre({ children }) {
      return <pre className="rounded-md my-2 overflow-x-auto">{children}</pre>;
    },
    // Paragraphs
    p({ children }) {
      return <p className="mb-3 last:mb-0">{children}</p>;
    },
    // Links
    a({ href, children }) {
      return (
        <a
          href={href}
          target="_blank"
          rel="noopener noreferrer"
          className="text-blue-600 hover:text-blue-800 underline"
        >
          {children}
        </a>
      );
    },
    // Headings
    h1({ children }) {
      return <h1 className="text-2xl font-bold mb-3 mt-4 first:mt-0">{children}</h1>;
    },
    h2({ children }) {
      return <h2 className="text-xl font-bold mb-2 mt-3 first:mt-0">{children}</h2>;
    },
    h3({ children }) {
      return <h3 className="text-lg font-semibold mb-2 mt-3 first:mt-0">{children}</h3>;
    },
    h4({ children }) {
      return <h4 className="text-base font-semibold mb-2 mt-2 first:mt-0">{children}</h4>;
    },
    // Lists
    ul({ children }) {
      return <ul className="list-disc list-inside mb-3 space-y-1">{children}</ul>;
    },
    ol({ children }) {
      return <ol className="list-decimal list-inside mb-3 space-y-1">{children}</ol>;
    },
    li({ children }) {
      return <li className="ml-2">{children}</li>;
    },
    // Blockquotes
    blockquote({ children }) {
      return (
        <blockquote className="border-l-4 border-gray-300 pl-4 py-2 my-3 italic bg-gray-50">
          {children}
        </blockquote>
      );
    },
    // Tables
    table({ children }) {
      return (
        <div className="overflow-x-auto my-3">
          <table className="min-w-full border-collapse border border-gray-300">
            {children}
          </table>
        </div>
      );
    },
    thead({ children }) {
      return <thead className="bg-gray-100">{children}</thead>;
    },
    tbody({ children }) {
      return <tbody>{children}</tbody>;
    },
    tr({ children }) {
      return <tr className="border-b border-gray-300">{children}</tr>;
    },
    th({ children }) {
      return (
        <th className="px-4 py-2 text-left font-semibold border border-gray-300">
          {children}
        </th>
      );
    },
    td({ children }) {
      return <td className="px-4 py-2 border border-gray-300">{children}</td>;
    },
    // Horizontal rules
    hr() {
      return <hr className="my-4 border-t border-gray-300" />;
    },
    // Strong and emphasis
    strong({ children }) {
      return <strong className="font-bold">{children}</strong>;
    },
    em({ children }) {
      return <em className="italic">{children}</em>;
    },
  };

  return (
    <div className="prose prose-sm max-w-none">
      <ReactMarkdown
        remarkPlugins={[remarkGfm]}
        rehypePlugins={[rehypeHighlight]}
        components={components}
      >
        {content}
      </ReactMarkdown>
    </div>
  );
}
