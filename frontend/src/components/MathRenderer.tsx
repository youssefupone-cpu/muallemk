import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import "katex/dist/katex.min.css";

import type { Components } from "react-markdown";

/**
 * MathRenderer — react-markdown مع KaTeX (P3-115/P4-242).
 * `inlineMath`/`math` ألياسات من remark-math — لا تُعرّف في نوع react-markdown
 * الافتراضي، لذا نُلصق الكائن بـ `as Components`.
 */
export const MathRenderer = ({ content, isUser: _isUser }: { content: string; isUser?: boolean }) => (
  <ReactMarkdown
    remarkPlugins={[remarkMath]}
    rehypePlugins={[rehypeKatex]}
    components={
      {
        // تخصيص كاشف React للمعادلات (مثلاً للـ RTL)
        inlineMath: ({ ...props }) => <span dir="ltr" {...props} />,
        math: ({ ...props }) => (
          <div dir="ltr" className="overflow-x-auto" {...props} />
        ),
      } as Components
    }
  >
    {content}
  </ReactMarkdown>
);
