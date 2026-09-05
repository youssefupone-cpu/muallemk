import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import rehypeSanitize, { defaultSchema } from "rehype-sanitize";

import type { Components } from "react-markdown";

/** مخطط sanitize يسمح بعناصر KaTeX دون XSS. */
const sanitizeSchema = {
  ...defaultSchema,
  attributes: {
    ...defaultSchema.attributes,
    div: [...(defaultSchema.attributes?.div || []), "className", "class"],
    span: [...(defaultSchema.attributes?.span || []), "className", "class", "style"],
    code: [...(defaultSchema.attributes?.code || []), "className", "class"],
  },
};

/**
 * MathRenderer — react-markdown + KaTeX + sanitize (P3-115/P4-242).
 * CSS لـ KaTeX يُستورد مرة واحدة من index.css.
 */
export const MathRenderer = ({ content, isUser: _isUser }: { content: string; isUser?: boolean }) => (
  <ReactMarkdown
    remarkPlugins={[remarkMath]}
    rehypePlugins={[rehypeKatex, [rehypeSanitize, sanitizeSchema]]}
    components={
      {
        // تخصيص بسيط للـ RTL حول المعادلات
        code: ({ className, children, ...props }) => (
          <code className={className} dir="ltr" {...props}>
            {children}
          </code>
        ),
      } as Components
    }
  >
    {content}
  </ReactMarkdown>
);
