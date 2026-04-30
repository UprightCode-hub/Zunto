import React from 'react';

const THEME_STYLES = {
  light: {
    root: 'space-y-2 text-[15px] leading-6 text-gray-800 dark:text-gray-100',
    strong: 'font-semibold text-gray-950 dark:text-white',
    code: 'rounded bg-gray-100 px-1 py-0.5 font-mono text-xs text-gray-900 dark:bg-white/10 dark:text-gray-100',
    rule: 'my-2 border-gray-200 dark:border-white/10',
  },
  dark: {
    root: 'space-y-2 text-sm leading-relaxed text-gray-100',
    strong: 'font-semibold text-white',
    code: 'rounded bg-white/10 px-1 py-0.5 font-mono text-xs text-gray-100',
    rule: 'my-2 border-white/10',
  },
};

function renderInlineMarkdown(text, theme) {
  const styles = THEME_STYLES[theme] || THEME_STYLES.light;
  const parts = [];
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`(.+?)`)/g;
  let lastIndex = 0;
  let match;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }

    if (match[2] !== undefined) {
      parts.push(
        <strong key={match.index} className={styles.strong}>
          {match[2]}
        </strong>,
      );
    } else if (match[3] !== undefined) {
      parts.push(
        <em key={match.index} className="italic">
          {match[3]}
        </em>,
      );
    } else if (match[4] !== undefined) {
      parts.push(
        <code key={match.index} className={styles.code}>
          {match[4]}
        </code>,
      );
    }

    lastIndex = match.index + match[0].length;
  }

  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }

  return parts.length ? parts : text;
}

export default function AssistantReply({ text, tone = 'light', className = '' }) {
  if (!text) {
    return null;
  }

  const styles = THEME_STYLES[tone] || THEME_STYLES.light;
  const output = [];
  let listItems = [];
  let listType = null;

  const flushList = () => {
    if (!listItems.length) {
      return;
    }

    const ListTag = listType === 'ol' ? 'ol' : 'ul';
    output.push(
      <ListTag
        key={`list-${output.length}`}
        className={`${listType === 'ol' ? 'list-decimal' : 'list-disc'} my-1 space-y-1 pl-5`}
      >
        {listItems.map((item, index) => (
          <li key={`${item}-${index}`}>
            {renderInlineMarkdown(item, tone)}
          </li>
        ))}
      </ListTag>,
    );
    listItems = [];
    listType = null;
  };

  text.split('\n').forEach((line, index) => {
    const trimmed = line.trim();
    const unorderedMatch = trimmed.match(/^[-*•]\s+(.+)/);
    const orderedMatch = trimmed.match(/^\d+[.)]\s+(.+)/);

    if (unorderedMatch) {
      if (listType === 'ol') {
        flushList();
      }
      listType = 'ul';
      listItems.push(unorderedMatch[1]);
      return;
    }

    if (orderedMatch) {
      if (listType === 'ul') {
        flushList();
      }
      listType = 'ol';
      listItems.push(orderedMatch[1]);
      return;
    }

    flushList();

    if (!trimmed) {
      return;
    }

    if (/^---+$/.test(trimmed)) {
      output.push(<hr key={`rule-${index}`} className={styles.rule} />);
      return;
    }

    output.push(
      <p key={`line-${index}`}>
        {renderInlineMarkdown(line, tone)}
      </p>,
    );
  });

  flushList();

  return (
    <div className={`${styles.root} ${className}`.trim()}>
      {output}
    </div>
  );
}
