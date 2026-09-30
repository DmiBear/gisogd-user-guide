"""Keep figures inside list items valid after Markdown rendering."""

import re


_FIGURE_PARAGRAPH = re.compile(
    r'<p>\s*(<figure\b[^>]*>.*?</figure>)\s*</p>', re.DOTALL
)


def on_page_content(html, **kwargs):
    # Python-Markdown wraps indented HTML figures in paragraphs. A figure is a
    # block element: unwrap it so browsers do not insert empty paragraphs and
    # keep the illustration attached to its parent list item.
    def unwrap(match):
        figure = match.group(1)
        return re.sub(r'(<figure\b[^>]*?)\s+markdown="[^"]*"', r'\1', figure, count=1)

    return _FIGURE_PARAGRAPH.sub(unwrap, html)
