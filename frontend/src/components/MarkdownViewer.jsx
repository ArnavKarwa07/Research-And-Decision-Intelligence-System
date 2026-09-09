import React, { useEffect, useState, useId } from 'react';
import ReactMarkdown from 'react-markdown';
import remarkGfm from 'remark-gfm';
import mermaid from 'mermaid';

// Initialize mermaid with dark theme
mermaid.initialize({
  startOnLoad: false,
  theme: 'dark',
  securityLevel: 'loose',
  fontFamily: 'Inter, system-ui, sans-serif',
  themeVariables: {
    darkMode: true,
    background: '#19120a',
    primaryColor: '#38bdf8',
    primaryTextColor: '#f0e0d1',
    primaryBorderColor: '#0284c7',
    lineColor: '#a08e7a',
    secondaryColor: '#f59e0b',
    tertiaryColor: '#10b981',
  },
});

function MermaidBlock({ chart }) {
  const [svg, setSvg] = useState('');
  const [hasError, setHasError] = useState(false);
  const rawId = useId();

  useEffect(() => {
    let isMounted = true;
    const renderDiagram = async () => {
      if (!chart || !chart.trim()) {
        if (isMounted) {
          setHasError(true);
        }
        return;
      }

      const cleanId = `mermaid-diag-${rawId.replace(/[^a-zA-Z0-9]/g, '')}-${Math.random().toString(36).substring(2, 7)}`;
      
      try {
        setHasError(false);
        const { svg: svgOutput } = await mermaid.render(cleanId, chart.trim());
        if (isMounted) {
          setSvg(svgOutput);
        }
      } catch (err) {
        console.warn('Mermaid rendering failed:', err);
        const tempEl = document.getElementById(cleanId);
        if (tempEl) {
          tempEl.remove();
        }
        const tempElD = document.getElementById('d' + cleanId);
        if (tempElD) {
          tempElD.remove();
        }
        if (isMounted) {
          setHasError(true);
        }
      }
    };

    renderDiagram();

    return () => {
      isMounted = false;
    };
  }, [chart, rawId]);

  if (hasError) {
    return (
      <div className="my-3 p-3 rounded-lg border border-amber-500/40 bg-amber-950/20 text-xs">
        <div className="font-mono text-[11px] font-bold text-amber-400 mb-1.5 flex items-center gap-1.5">
          <span className="material-symbols-outlined text-sm">warning</span>
          <span>Mermaid Diagram (Raw Code)</span>
        </div>
        <pre className="p-3 overflow-x-auto text-[11px] font-mono text-on-surface bg-surface-container-high/80 rounded border border-outline-variant/40 leading-relaxed">
          <code>{chart}</code>
        </pre>
      </div>
    );
  }

  if (!svg) {
    return (
      <div className="my-3 p-4 rounded-xl bg-surface-container/60 border border-outline-variant/40 text-xs text-on-surface-variant font-mono animate-pulse flex items-center gap-2">
        <span className="w-2 h-2 rounded-full bg-primary animate-ping" />
        <span>Rendering diagram...</span>
      </div>
    );
  }

  return (
    <div
      className="mermaid-container my-4 p-4 rounded-xl bg-surface-container/80 border border-outline-variant/60 overflow-x-auto flex justify-center items-center shadow-inner"
      dangerouslySetInnerHTML={{ __html: svg }}
    />
  );
}

const CodeBlockContext = React.createContext(false);

const customComponents = {
  pre({ node, children, ...props }) {
    return (
      <CodeBlockContext.Provider value={true}>
        <pre className="my-3 overflow-x-auto rounded-lg bg-surface-container-lowest p-4 border border-outline-variant/30 text-on-surface" {...props}>
          {children}
        </pre>
      </CodeBlockContext.Provider>
    );
  },
  code({ node, className, children, ...props }) {
    const isBlock = React.useContext(CodeBlockContext);
    const isInline = !isBlock;
    const match = /language-(\w+)/.exec(className || '');
    const lang = match ? match[1] : '';
    const codeString = String(children).replace(/\n$/, '');

    // Restrict string prefix diagram detection to code blocks only (isBlock)
    if (lang === 'mermaid' || (isBlock && (codeString.startsWith('gantt') || codeString.startsWith('sequenceDiagram') || codeString.startsWith('graph ') || codeString.startsWith('flowchart ')))) {
      return <MermaidBlock chart={codeString} />;
    }

    if (isInline) {
      return (
        <code className="bg-surface-container-high text-tertiary px-1.5 py-0.5 rounded font-mono text-[11px] border border-outline-variant/40" {...props}>
          {children}
        </code>
      );
    }
    return (
      <code className={className} {...props}>
        {children}
      </code>
    );
  },
  table({ children }) {
    return (
      <div className="overflow-x-auto my-4 rounded-lg border border-outline-variant/60 shadow-sm">
        <table className="min-w-full divide-y divide-outline-variant/60 text-xs text-left text-on-surface">
          {children}
        </table>
      </div>
    );
  },
  thead({ children }) {
    return (
      <thead className="bg-surface-container-high text-primary font-mono text-[11px] uppercase tracking-wider font-bold">
        {children}
      </thead>
    );
  },
  tbody({ children }) {
    return (
      <tbody className="divide-y divide-outline-variant/40 bg-surface-container-low/60">
        {children}
      </tbody>
    );
  },
  tr({ children }) {
    return (
      <tr className="hover:bg-surface-container/50 transition-colors">
        {children}
      </tr>
    );
  },
  th({ children }) {
    return (
      <th className="px-3.5 py-2.5 font-bold border-b border-outline-variant/60 text-primary">
        {children}
      </th>
    );
  },
  td({ children }) {
    return (
      <td className="px-3.5 py-2 border-b border-outline-variant/40 text-on-surface-variant leading-relaxed">
        {children}
      </td>
    );
  },
  h1({ children }) {
    return (
      <h1 className="text-xl font-bold text-primary font-headline-md mt-5 mb-2.5 pb-1.5 border-b border-outline-variant/40">
        {children}
      </h1>
    );
  },
  h2({ children }) {
    return (
      <h2 className="text-lg font-bold text-primary font-headline-md mt-4 mb-2 pb-1 border-b border-outline-variant/30">
        {children}
      </h2>
    );
  },
  h3({ children }) {
    return (
      <h3 className="text-base font-bold text-on-surface font-headline-md mt-3.5 mb-1.5">
        {children}
      </h3>
    );
  },
  h4({ children }) {
    return (
      <h4 className="text-sm font-bold text-on-surface font-headline-md mt-3 mb-1">
        {children}
      </h4>
    );
  },
  h5({ children }) {
    return (
      <h5 className="text-xs font-bold text-on-surface uppercase tracking-wider mt-2.5 mb-1">
        {children}
      </h5>
    );
  },
  h6({ children }) {
    return (
      <h6 className="text-xs font-bold text-outline uppercase tracking-wider mt-2 mb-1">
        {children}
      </h6>
    );
  },
  p({ children }) {
    return <div className="text-sm leading-relaxed text-on-surface my-3">{children}</div>;
  },
  ul({ children }) {
    return (
      <ul className="list-disc list-inside text-sm text-on-surface-variant my-3 space-y-1.5 pl-2">
        {children}
      </ul>
    );
  },
  ol({ children }) {
    return (
      <ol className="list-decimal list-inside text-sm text-on-surface-variant my-3 space-y-1.5 pl-2">
        {children}
      </ol>
    );
  },
  li({ children }) {
    return <li className="leading-relaxed text-sm text-on-surface-variant">{children}</li>;
  },
  blockquote({ children }) {
    return (
      <blockquote className="border-l-4 border-primary/70 pl-3.5 py-2 my-3 bg-surface-container/40 italic text-on-surface-variant text-sm rounded-r-md">
        {children}
      </blockquote>
    );
  },
  a({ node, href, children, ...props }) {
    const rawHref = typeof href === 'string' ? href.trim() : '';
    const isSafe = /^(https?:|mailto:|file:|\/|#)/i.test(rawHref);
    const safeHref = isSafe ? rawHref : '#';
    const isExternal = safeHref.toLowerCase().startsWith('http');
    return (
      <a
        href={safeHref}
        target={isExternal ? "_blank" : undefined}
        rel={isExternal ? "noopener noreferrer" : undefined}
        className="text-primary hover:underline transition-colors"
        {...props}
      >
        {children}
      </a>
    );
  },
  hr() {
    return <hr className="my-4 border-outline-variant/60" />;
  },
  strong({ children }) {
    return <strong className="font-bold text-on-surface">{children}</strong>;
  },
};

export default function MarkdownViewer({ content = '' }) {
  if (typeof content !== 'string' || !content.trim()) return null;

  // Unescape double-escaped newlines (\n -> real newlines) so markdown headings/lists format properly
  const normalizedContent = content.replace(/\\n/g, '\n');

  return (
    <div className="markdown-content text-sm text-on-surface leading-relaxed space-y-3">
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={customComponents}>
        {normalizedContent}
      </ReactMarkdown>
    </div>
  );
}
