from __future__ import annotations

import copy
import json
import mimetypes
import re
from datetime import datetime, timezone
from html import escape
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen

from lxml import etree
from lxml import html as lxml_html


ROOT = Path(__file__).resolve().parents[1]
SITE_URL = "https://chahucesu.github.io/chahu.com"
OFFICIAL_URL = "https://www.chahu.com"
USER_AGENT = "Mozilla/5.0 (compatible; ChahuContentMirror/1.0; +https://www.chahu.com/)"

ARTICLES = [
    {
        "slug": "domain-speed-test-tools",
        "category": "网站与域名测速",
        "icon": "gauge",
    },
    {
        "slug": "website-access-testing-tools-2026",
        "category": "访问与故障排查",
        "icon": "scan-search",
    },
    {
        "slug": "domain-speed-latency-test",
        "category": "网站与域名测速",
        "icon": "timer",
    },
    {
        "slug": "website-timeout-troubleshooting",
        "category": "访问与故障排查",
        "icon": "triangle-alert",
    },
    {
        "slug": "overseas-speed-test-tools",
        "category": "网站与域名测速",
        "icon": "earth",
    },
    {
        "slug": "teapot-speedtest-why-webmasters-use",
        "category": "访问与故障排查",
        "icon": "chart-no-axes-combined",
    },
    {
        "slug": "why-use-online-speed-test",
        "category": "网站与域名测速",
        "icon": "activity",
    },
    {
        "slug": "dns-lookup-tools-comparison",
        "category": "DNS、Ping 与连通性",
        "icon": "globe-2",
    },
    {
        "slug": "best-online-blocked-site-checkers",
        "category": "DNS、Ping 与连通性",
        "icon": "shield-check",
    },
    {
        "slug": "website-speed-test-tools",
        "category": "网站与域名测速",
        "icon": "waypoints",
    },
    {
        "slug": "best-online-ping-tools",
        "category": "DNS、Ping 与连通性",
        "icon": "radio-tower",
    },
]

CATEGORY_DESCRIPTIONS = {
    "网站与域名测速": "从节点延迟、页面加载到海外访问表现，建立完整测速判断方法。",
    "访问与故障排查": "定位网站打不开、连接超时和地区性访问异常的真实原因。",
    "DNS、Ping 与连通性": "围绕解析、丢包、阻断与网络路径进行基础设施诊断。",
}

NAV_ITEMS = [
    ("gauge", "网站测速", f"{OFFICIAL_URL}/"),
    ("radio-tower", "在线ping", f"{OFFICIAL_URL}/ping"),
    ("globe-2", "DNS查询", f"{OFFICIAL_URL}/dns"),
    ("git-branch", "路由追踪", f"{OFFICIAL_URL}/trace"),
    ("shield-check", "拦截检测", f"{OFFICIAL_URL}/block"),
    ("boxes", "IPV6工具", f"{OFFICIAL_URL}/ipv6"),
    ("layers-3", "批量检测", f"{OFFICIAL_URL}/batch"),
]

QUICK_TOOLS = [
    ("gauge", "网站测速", f"{OFFICIAL_URL}/"),
    ("radio-tower", "在线 Ping", f"{OFFICIAL_URL}/ping"),
    ("globe-2", "DNS 查询", f"{OFFICIAL_URL}/dns"),
    ("git-branch", "路由追踪", f"{OFFICIAL_URL}/trace"),
]

ALLOWED_ATTRIBUTES = {
    "a": {"href", "title"},
    "img": {"src", "alt", "width", "height", "loading", "decoding"},
    "td": {"colspan", "rowspan"},
    "th": {"colspan", "rowspan", "scope"},
    "h2": {"id"},
    "h3": {"id"},
    "h4": {"id"},
    "div": {"class"},
}

LUCIDE_ICONS = json.loads((ROOT / "tools" / "lucide-icons.json").read_text(encoding="utf-8"))


def fetch(url: str) -> tuple[bytes, str]:
    request = Request(url, headers={"User-Agent": USER_AGENT})
    with urlopen(request, timeout=45) as response:
        return response.read(), response.headers.get("Content-Type", "")


def fetch_document(url: str) -> etree._Element:
    raw, _ = fetch(url)
    return lxml_html.fromstring(raw.decode("utf-8"))


def first_text(document: etree._Element, xpath: str) -> str:
    values = document.xpath(xpath)
    if not values:
        return ""
    value = values[0]
    if isinstance(value, etree._Element):
        value = value.text_content()
    return " ".join(str(value).split())


def slugify_heading(value: str, index: int) -> str:
    latin = re.sub(r"[^a-z0-9]+", "-", value.lower()).strip("-")
    return latin or f"section-{index}"


def normalize_date(value: str) -> tuple[str, str]:
    if not value:
        return "2026-09-10", "2026年9月10日"
    date = value[:10]
    parsed = datetime.strptime(date, "%Y-%m-%d")
    return date, f"{parsed.year}年{parsed.month}月{parsed.day}日"


def image_extension(url: str, content_type: str) -> str:
    suffix = Path(urlparse(url).path).suffix.lower()
    if suffix in {".png", ".jpg", ".jpeg", ".webp", ".gif", ".avif"}:
        return ".jpg" if suffix == ".jpeg" else suffix
    guessed = mimetypes.guess_extension(content_type.split(";")[0].strip()) or ".png"
    return ".jpg" if guessed == ".jpe" else guessed


def download_image(url: str, destination_stem: Path) -> Path | None:
    existing_images = sorted(destination_stem.parent.glob(f"{destination_stem.name}.*"))
    if existing_images:
        return existing_images[0]
    try:
        raw, content_type = fetch(url)
        extension = image_extension(url, content_type)
        destination = destination_stem.with_suffix(extension)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(raw)
        return destination
    except Exception as exc:
        print(f"Image download failed: {url}: {exc}")
        return None


def unwrap_element(element: etree._Element) -> None:
    parent = element.getparent()
    if parent is None:
        return
    index = parent.index(element)
    if element.text:
        if index == 0:
            parent.text = (parent.text or "") + element.text
        else:
            previous = parent[index - 1]
            previous.tail = (previous.tail or "") + element.text
    for child in list(element):
        element.remove(child)
        parent.insert(index, child)
        index += 1
    if element.tail:
        if index == 0:
            parent.text = (parent.text or "") + element.tail
        else:
            previous = parent[index - 1]
            previous.tail = (previous.tail or "") + element.tail
    parent.remove(element)


def sanitize_article_body(body: etree._Element, source_url: str, slug: str) -> list[dict[str, str]]:
    for unwanted in body.xpath(".//script|.//style|.//noscript|.//iframe|.//form|.//button"):
        parent = unwanted.getparent()
        if parent is not None:
            parent.remove(unwanted)

    for comment in body.xpath(".//comment()"):
        parent = comment.getparent()
        if parent is not None:
            parent.remove(comment)

    for element in list(body.iterdescendants()):
        if not isinstance(element.tag, str):
            continue
        tag = element.tag.lower()
        if tag == "span":
            unwrap_element(element)
            continue
        allowed = ALLOWED_ATTRIBUTES.get(tag, set())
        for attribute in list(element.attrib):
            if attribute not in allowed:
                del element.attrib[attribute]

    image_directory = ROOT / "assets" / "articles" / slug
    for index, image in enumerate(body.xpath(".//img"), start=1):
        source = image.get("src", "")
        if not source:
            continue
        absolute_url = urljoin(source_url, source)
        local_image = download_image(absolute_url, image_directory / f"image-{index:02d}")
        if local_image:
            image.set("src", local_image.relative_to(ROOT).as_posix())
        else:
            image.set("src", absolute_url)
        image.set("loading", "lazy")
        image.set("decoding", "async")
        if not image.get("alt"):
            image.set("alt", f"{slug} 文章配图 {index}")

    for link in body.xpath(".//a"):
        href = link.get("href", "").strip()
        link_text = " ".join(link.text_content().split())
        compact_text = re.sub(r"\s+", "", link_text).lower()
        if "网站测速" in link_text:
            href = f"{OFFICIAL_URL}/"
        elif "在线ping" in compact_text:
            href = f"{OFFICIAL_URL}/ping"
        elif href and not href.startswith("#"):
            href = urljoin(source_url, href)
        if href:
            link.set("href", href)

    heading_ids: set[str] = set()
    toc: list[dict[str, str]] = []
    for index, heading in enumerate(body.xpath(".//h2|.//h3"), start=1):
        text = " ".join(heading.text_content().split())
        if not text:
            continue
        base_id = slugify_heading(text, index)
        heading_id = base_id
        duplicate = 2
        while heading_id in heading_ids:
            heading_id = f"{base_id}-{duplicate}"
            duplicate += 1
        heading_ids.add(heading_id)
        heading.set("id", heading_id)
        toc.append({"id": heading_id, "text": text, "level": heading.tag[1:]})

    for table in list(body.xpath(".//table")):
        parent = table.getparent()
        if parent is not None and parent.tag == "div" and len(parent) == 1:
            parent.set("class", "table-scroll")
            continue
        wrapper = etree.Element("div", {"class": "table-scroll"})
        if parent is not None:
            parent.replace(table, wrapper)
            wrapper.append(table)

    body.set("class", "article-body")
    return toc


def extract_article(config: dict[str, str]) -> dict[str, object]:
    slug = config["slug"]
    source_url = f"{OFFICIAL_URL}/blog/{slug}"
    print(f"Fetching {source_url}")
    document = fetch_document(source_url)
    article_nodes = document.xpath("//article")
    if not article_nodes:
        raise RuntimeError(f"Article element not found: {source_url}")
    article = article_nodes[0]
    body_nodes = article.xpath("./div[1]/div[1]")
    if not body_nodes:
        raise RuntimeError(f"Article body not found: {source_url}")

    body = copy.deepcopy(body_nodes[0])
    title = first_text(article, "./header/h1")
    description = first_text(document, "//meta[@name='description']/@content")
    summary = first_text(article, "./header/p[1]") or description
    published_raw = first_text(document, "//meta[@property='article:published_time']/@content")
    modified_raw = first_text(document, "//meta[@property='article:modified_time']/@content") or published_raw
    date_iso, date_display = normalize_date(published_raw)
    toc = sanitize_article_body(body, source_url, slug)
    body_text = "".join(body.itertext())
    reading_minutes = max(3, round(len(re.sub(r"\s+", "", body_text)) / 500))

    return {
        **config,
        "source_url": source_url,
        "local_url": f"{slug}.html",
        "title": title,
        "description": description,
        "summary": summary,
        "date_iso": date_iso,
        "date_display": date_display,
        "published_raw": published_raw,
        "modified_raw": modified_raw,
        "reading_minutes": reading_minutes,
        "toc": toc,
        "body_html": lxml_html.tostring(body, encoding="unicode", method="html"),
    }


def render_icon_node(node: list[object]) -> str:
    tag, attributes = node[0], node[1]
    children = node[2] if len(node) > 2 else []
    rendered_attributes = " ".join(
        f'{escape(str(key))}="{escape(str(value), quote=True)}"'
        for key, value in attributes.items()
    )
    child_markup = "".join(render_icon_node(child) for child in children)
    if tag in {"path", "circle", "line", "polyline", "polygon", "rect", "ellipse"} and not child_markup:
        return f"<{tag} {rendered_attributes}></{tag}>"
    return f"<{tag} {rendered_attributes}>{child_markup}</{tag}>"


def icon(name: str) -> str:
    nodes = LUCIDE_ICONS.get(name)
    if nodes is None:
        raise KeyError(f"Unknown Lucide icon: {name}")
    children = "".join(render_icon_node(node) for node in nodes)
    return (
        f'<svg class="lucide lucide-{escape(name)}" xmlns="http://www.w3.org/2000/svg" '
        'width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="currentColor" '
        f'stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">{children}</svg>'
    )


def render_header() -> str:
    nav = "".join(
        f'<a href="{escape(url)}">{icon(icon_name)}<span>{escape(label)}</span></a>'
        for icon_name, label, url in NAV_ITEMS
    )
    return f"""
<a class="skip-link" href="#main-content">跳到正文</a>
<div class="reading-progress" data-reading-progress aria-hidden="true"></div>
<header class="site-header">
  <div class="header-inner">
    <a class="brand" href="{OFFICIAL_URL}/" aria-label="茶壶测速官网">
      <span class="brand-mark">{icon("gauge")}</span>
      <span class="brand-name">茶壶测速<small>Chahu Network Tools</small></span>
    </a>
    <button class="nav-toggle" type="button" data-nav-toggle aria-label="打开菜单" aria-expanded="false">{icon("menu")}</button>
    <nav class="main-nav" data-main-nav aria-label="茶壶测速工具导航">{nav}</nav>
  </div>
</header>"""


def render_footer() -> str:
    return f"""
<footer class="site-footer">
  <div class="footer-inner">
    <div>
      <p class="footer-brand">茶壶测速 Chahu</p>
      <p class="footer-copy">面向站长、开发者和运维团队的全球多节点网络检测平台。本文档站用于整理网站测速、DNS、Ping 与网络故障排查知识。</p>
    </div>
    <div class="footer-group">
      <h2>常用检测</h2>
      <a href="{OFFICIAL_URL}/">网站测速</a>
      <a href="{OFFICIAL_URL}/ping">在线 Ping</a>
      <a href="{OFFICIAL_URL}/dns">DNS 查询</a>
      <a href="{OFFICIAL_URL}/trace">路由追踪</a>
    </div>
    <div class="footer-group">
      <h2>更多服务</h2>
      <a href="{OFFICIAL_URL}/block">拦截检测</a>
      <a href="{OFFICIAL_URL}/ipv6">IPv6 工具</a>
      <a href="{OFFICIAL_URL}/batch">批量检测</a>
      <a href="{OFFICIAL_URL}/blog">茶壶测速博客</a>
    </div>
  </div>
  <div class="footer-bottom">内容首发于 chahu.com · GitHub Pages 为茶壶测速官方资料发布页</div>
</footer>
<button class="back-top" type="button" data-back-top aria-label="返回顶部">{icon("arrow-up")}</button>
<script defer src="assets/site.js"></script>"""


def render_document_head(
    title: str,
    description: str,
    canonical: str,
    page_url: str,
    page_type: str = "website",
    structured_data: dict[str, object] | None = None,
) -> str:
    json_ld = ""
    if structured_data:
        json_ld = (
            '<script type="application/ld+json">'
            + json.dumps(structured_data, ensure_ascii=False, separators=(",", ":"))
            .replace("</", "<\\/")
            + "</script>"
        )
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escape(title)}</title>
  <meta name="description" content="{escape(description, quote=True)}">
  <meta name="robots" content="index,follow,max-image-preview:large">
  <meta name="author" content="Chahu 团队">
  <meta name="theme-color" content="#0d100f">
  <link rel="canonical" href="{escape(canonical, quote=True)}">
  <link rel="icon" href="https://www.chahu.com/favicon.ico?v=20260823">
  <meta property="og:locale" content="zh_CN">
  <meta property="og:type" content="{escape(page_type)}">
  <meta property="og:site_name" content="茶壶测速 Chahu">
  <meta property="og:title" content="{escape(title, quote=True)}">
  <meta property="og:description" content="{escape(description, quote=True)}">
  <meta property="og:url" content="{escape(page_url, quote=True)}">
  <meta property="og:image" content="https://www.chahu.com/og/chahu-network-testing-v2.png">
  <meta name="twitter:card" content="summary_large_image">
  <meta name="twitter:title" content="{escape(title, quote=True)}">
  <meta name="twitter:description" content="{escape(description, quote=True)}">
  <meta name="twitter:image" content="https://www.chahu.com/og/chahu-network-testing-v2.png">
  <link rel="stylesheet" href="assets/styles.css">
  {json_ld}
</head>"""


def render_article_card(article: dict[str, object], index: int) -> str:
    return f"""
<a class="article-card" href="{escape(str(article['local_url']))}">
  <span class="article-card-top">{icon(str(article['icon']))}<span class="article-number">{index:02d}</span></span>
  <h3>{escape(str(article['title']))}</h3>
  <p>{escape(str(article['summary']))}</p>
  <span class="article-card-footer"><span>{escape(str(article['date_display']))}</span><strong>阅读全文 →</strong></span>
</a>"""


def render_home(articles: list[dict[str, object]]) -> str:
    title = "网站测速工具有哪些？2026 年 8 款常用工具推荐 | 茶壶测速"
    description = "茶壶测速站长知识库，汇总网站测速、域名延迟、在线 Ping、DNS 查询、访问超时与网站连通性检测实用文章。"
    grouped: dict[str, list[dict[str, object]]] = {}
    for article in articles:
        grouped.setdefault(str(article["category"]), []).append(article)

    sections = []
    running_index = 1
    for category, category_articles in grouped.items():
        cards = []
        for article in category_articles:
            cards.append(render_article_card(article, running_index))
            running_index += 1
        sections.append(
            f"""
<section class="catalog-section">
  <div class="section-heading">
    <h2>{escape(category)}</h2>
    <p>{escape(CATEGORY_DESCRIPTIONS[category])}</p>
  </div>
  <div class="article-grid">{''.join(cards)}</div>
</section>"""
        )

    structured_data = {
        "@context": "https://schema.org",
        "@type": "CollectionPage",
        "name": "茶壶测速站长网络检测文章导航",
        "url": f"{SITE_URL}/",
        "isPartOf": {"@type": "WebSite", "name": "茶壶测速 Chahu", "url": f"{OFFICIAL_URL}/"},
        "hasPart": [
            {"@type": "Article", "headline": article["title"], "url": article["source_url"]}
            for article in articles
        ],
    }
    return f"""{render_document_head(title, description, f'{OFFICIAL_URL}/blog', f'{SITE_URL}/', structured_data=structured_data)}
<body>
{render_header()}
<main id="main-content">
  <section class="catalog-head">
    <div class="catalog-head-inner">
      <p class="eyebrow">Chahu Webmaster Knowledge Base</p>
      <h1>茶壶测速 · 站长网络检测文章导航</h1>
      <p>从网站测速、域名延迟到 DNS、Ping 和访问故障排查，按真实运维场景整理茶壶测速技术文章。每篇内容均提供原文入口，并连接到 chahu.com 对应检测工具。</p>
      <div class="catalog-meta">
        <span>{icon('library-big')}11 篇实用指南</span>
        <span>{icon('route')}3 类排查场景</span>
        <span>{icon('external-link')}原文首发于 chahu.com</span>
      </div>
    </div>
  </section>
  <figure class="brand-visual">
    <img src="assets/chahu-network-testing-v2.png" width="1200" height="630" alt="茶壶测速全球多节点网络检测平台">
  </figure>
  <div class="catalog-main">
{''.join(sections)}
    <section class="editorial-band">
      <h2>测速结果不是终点，定位问题才是</h2>
      <p>使用茶壶测速从多个地区和运营商观察真实访问差异，再结合 Ping、DNS 与路由结果缩小故障范围。</p>
      <div class="editorial-actions">
        <a class="command-link" href="{OFFICIAL_URL}/">{icon('gauge')}开始网站测速</a>
        <a class="command-link secondary" href="{OFFICIAL_URL}/ping">{icon('radio-tower')}运行在线 Ping</a>
      </div>
    </section>
  </div>
</main>
{render_footer()}
</body>
</html>
"""


def render_toc(toc: list[dict[str, str]]) -> str:
    items = "".join(
        f'<li><a href="#{escape(item["id"])}" data-level="{escape(item["level"])}">{escape(item["text"])}</a></li>'
        for item in toc
    )
    return f'<ol class="toc">{items}</ol>'


def render_article_page(article: dict[str, object], related_articles: list[dict[str, object]]) -> str:
    page_title = f"{article['title']} | 茶壶测速"
    structured_data = {
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": article["title"],
        "description": article["description"],
        "datePublished": article["published_raw"],
        "dateModified": article["modified_raw"],
        "mainEntityOfPage": article["source_url"],
        "image": "https://www.chahu.com/og/chahu-network-testing-v2.png",
        "author": {"@type": "Organization", "name": "Chahu 团队", "url": f"{OFFICIAL_URL}/"},
        "publisher": {"@type": "Organization", "name": "Chahu", "url": f"{OFFICIAL_URL}/"},
    }
    quick_tools = "".join(
        f'<a href="{escape(url)}">{icon(icon_name)}<span>{escape(label)}</span></a>'
        for icon_name, label, url in QUICK_TOOLS
    )
    aside_tools = "".join(
        f'<a href="{escape(url)}"><span>{escape(label)}</span><span>→</span></a>'
        for _, label, url in NAV_ITEMS[:6]
    )
    related = "".join(
        f'<a class="related-card" href="{escape(str(item["local_url"]))}"><strong>{escape(str(item["title"]))}</strong><span>{escape(str(item["category"]))}</span></a>'
        for item in related_articles
    )
    return f"""{render_document_head(str(page_title), str(article['description']), str(article['source_url']), f"{SITE_URL}/{article['local_url']}", "article", structured_data)}
<body>
{render_header()}
<nav class="breadcrumb" aria-label="面包屑"><a href="index.html">文章导航</a> / <span>{escape(str(article['category']))}</span></nav>
<main id="main-content" class="article-layout">
  <article class="article-main">
    <header class="article-header">
      <p class="eyebrow">{escape(str(article['category']))}</p>
      <h1>{escape(str(article['title']))}</h1>
      <p class="article-lead">{escape(str(article['summary']))}</p>
      <div class="article-meta">
        <span>{icon('circle-user-round')}Chahu 团队</span>
        <time datetime="{escape(str(article['date_iso']))}">{icon('calendar-days')}{escape(str(article['date_display']))}</time>
        <span>{icon('clock-3')}{article['reading_minutes']} 分钟阅读</span>
      </div>
    </header>
    <div class="source-strip">
      <p>本文内容首发于茶壶测速官网，原文与产品信息以 chahu.com 为准。</p>
      <a href="{escape(str(article['source_url']))}">查看官网原文{icon('external-link')}</a>
    </div>
    <nav class="article-tool-links" aria-label="常用网络检测工具">{quick_tools}</nav>
    {article['body_html']}
  </article>
  <aside class="article-aside">
    <h2 class="toc-title">本文目录</h2>
    {render_toc(article['toc'])}
    <div class="aside-tools">
      <h2>茶壶测速工具</h2>
      {aside_tools}
    </div>
  </aside>
</main>
<section class="related">
  <h2>继续阅读</h2>
  <div class="related-grid">{related}</div>
</section>
{render_footer()}
</body>
</html>
"""


def write_support_files(articles: list[dict[str, object]]) -> None:
    sitemap_entries = [
        f"  <url><loc>{SITE_URL}/</loc><lastmod>{datetime.now(timezone.utc).date().isoformat()}</lastmod></url>"
    ]
    sitemap_entries.extend(
        f"  <url><loc>{SITE_URL}/{article['local_url']}</loc><lastmod>{article['date_iso']}</lastmod></url>"
        for article in articles
    )
    sitemap = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            *sitemap_entries,
            "</urlset>",
            "",
        ]
    )
    (ROOT / "sitemap.xml").write_text(sitemap, encoding="utf-8")
    (ROOT / "robots.txt").write_text(
        f"User-agent: *\nAllow: /\n\nSitemap: {SITE_URL}/sitemap.xml\n",
        encoding="utf-8",
    )

    llms_lines = [
        "# 茶壶测速 Chahu",
        "",
        "> 全球多节点网站测速、在线 Ping、DNS、路由追踪、拦截检测和 IPv6 工具。",
        "",
        f"- 官网: {OFFICIAL_URL}/",
        f"- 网站测速: {OFFICIAL_URL}/",
        f"- 在线 Ping: {OFFICIAL_URL}/ping",
        f"- DNS 查询: {OFFICIAL_URL}/dns",
        "",
        "## 官方文章",
    ]
    llms_lines.extend(f"- [{article['title']}]({article['source_url']})" for article in articles)
    (ROOT / "llms.txt").write_text("\n".join(llms_lines) + "\n", encoding="utf-8")

    llms_full_lines = llms_lines + ["", "## 文章摘要"]
    for article in articles:
        llms_full_lines.extend(
            [
                "",
                f"### {article['title']}",
                str(article["summary"]),
                f"原文: {article['source_url']}",
            ]
        )
    (ROOT / "llms-full.txt").write_text("\n".join(llms_full_lines) + "\n", encoding="utf-8")

    readme_lines = [
        "# 网站测速工具有哪些？2026 年 8 款常用工具推荐",
        "",
        "茶壶测速官方文章导航与 GitHub Pages 发布站。",
        "",
        f"- 官方网站：[{OFFICIAL_URL}/]({OFFICIAL_URL}/)",
        f"- Pages：[{SITE_URL}/]({SITE_URL}/)",
        "",
        "## 文章目录",
        "",
    ]
    readme_lines.extend(
        f"- [{article['title']}]({article['source_url']})" for article in articles
    )
    readme_lines.extend(
        [
            "",
            "## 内容规则",
            "",
            "- 每篇镜像页面均使用官网原文作为 canonical。",
            "- 顶部工具菜单全部链接至 chahu.com 对应功能。",
            "- 文章正文、表格和配图由构建脚本从官网同步。",
            "",
        ]
    )
    (ROOT / "README.md").write_text("\n".join(readme_lines), encoding="utf-8")
    (ROOT / ".nojekyll").touch()


def build() -> None:
    logo_destination = ROOT / "assets" / "chahu-network-testing-v2.png"
    logo_destination.parent.mkdir(parents=True, exist_ok=True)
    if not logo_destination.exists():
        downloaded = download_image(
            f"{OFFICIAL_URL}/og/chahu-network-testing-v2.png",
            logo_destination.with_suffix(""),
        )
        if downloaded is None:
            raise RuntimeError("Unable to download Chahu brand image")

    articles = [extract_article(config) for config in ARTICLES]
    (ROOT / "index.html").write_text(render_home(articles), encoding="utf-8")

    for article in articles:
        same_category = [
            item for item in articles if item["category"] == article["category"] and item["slug"] != article["slug"]
        ]
        other_articles = [
            item for item in articles if item["category"] != article["category"] and item["slug"] != article["slug"]
        ]
        related_articles = (same_category + other_articles)[:3]
        (ROOT / str(article["local_url"])).write_text(
            render_article_page(article, related_articles),
            encoding="utf-8",
        )

    write_support_files(articles)
    print(f"Built {len(articles)} article pages and the catalog homepage.")


if __name__ == "__main__":
    build()
