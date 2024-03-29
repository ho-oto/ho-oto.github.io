import html
import json
import logging
import os
import re
import subprocess
import urllib.parse
from pathlib import Path
from unicodedata import east_asian_width
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup
from pygments import highlight
from pygments.lexers import get_lexer_by_name
from pygments.formatters import HtmlFormatter
from pygments.util import ClassNotFound

logging.basicConfig(level=logging.INFO)


def embed_tag_exceptional(url: str):
    if re.compile(r"https://gist\.github\.com/.+").match(url):
        return f'<script src="{url}.js"></script>'
    return None


def endpoint_by_providers(url: str):
    with open("providers.json", "r") as f:
        providers = json.loads(f.read())
    for provider in providers:
        for endpoint in provider["endpoints"]:
            if "schemes" not in endpoint:
                continue
            for scheme in endpoint["schemes"]:
                if re.compile(r".+".join(map(re.escape, scheme.split("*")))).match(url):
                    return endpoint["url"].replace(r"{format}", "json")
    return None


def endpoint_by_discovery(url: str):
    logging.info(f"EMBED: try to use oembed discovery mechanism for {url}")
    try:
        with urlopen(url) as rsp:
            bs = BeautifulSoup(rsp.read(), "html.parser")
            for tag in bs.select("link"):
                if tag.attrs.get("type", "") == "application/json+oembed":
                    logging.info("EMBED: ↳success")
                    return tag.attrs["href"]
    except:
        logging.info("EMBED: ↳failed")
        return None


def get_embed_tag(url: str):
    if tag := embed_tag_exceptional(url):
        return tag
    if endpoint := endpoint_by_providers(url) or endpoint_by_discovery(url):
        try:
            logging.info(f"EMBED: try to use oembed endpoint {url}")
            endpoint = urllib.parse.urlparse(endpoint)
            endpoint = urllib.parse.urlunparse(
                (
                    endpoint.scheme,
                    endpoint.netloc,
                    endpoint.path,
                    None,
                    urllib.parse.urlencode(
                        {"url": url, "format": "json", "maxwidth": "680"}
                    ),
                    None,
                )
            )
            with urlopen(Request(endpoint)) as rsp:
                tag = str(json.loads(rsp.read())["html"])
                logging.info("EMBED: ↳success")
                return tag
        except:
            logging.info("EMBED: ↳failed")
            None


def convert_embed(bs: BeautifulSoup):
    for tag in bs.select(".embed, .video"):
        if embed_tag := get_embed_tag(tag.attrs["href"]):
            tag.replace_with(BeautifulSoup(embed_tag, "html.parser"))
    return bs


def convert_code_block(bs: BeautifulSoup):
    for tag in bs.select("pre > code"):
        if tag.parent is None:
            continue
        lang = tag.parent.attrs.get("class", ["text"])
        if lang == ["plain", "text"]:
            lang = ["text"]
        try:
            lexer = get_lexer_by_name("-".join(lang), stripall=True)
        except ClassNotFound:
            lexer = get_lexer_by_name("text")
        code = html.unescape(tag.get_text())
        formatter = HtmlFormatter(cssclass="dracula")
        tag.replace_with(
            BeautifulSoup(highlight(code, lexer, formatter), "html.parser")
        )
    return bs


def convert_internal_link(bs: BeautifulSoup, base_dir, posts):
    links = {}
    for post in posts:
        props: dict = post["properties"]
        links[post["id"]] = (
            "".join(map(lambda x: x["text"]["content"], props["title"]["title"])),
            props["dir"]["select"]["name"],
        )
    for tag in bs.select("span.link_to_page"):
        id = tag.attrs.get("id")
        if title_dir := links.get(id):
            title, trg_dir = title_dir
            a = bs.new_tag("a", href=f"../{base_dir}/{trg_dir}/{id}/")
            a.append(title)
            tag.replace_with(a)
        else:
            tag.extract()
    for tag in bs.select("span.unsupported"):
        tag.extract()
    return bs


def generate_toc(bs: BeautifulSoup):
    ids: set[str] = set()
    toc = []
    for tag in bs.select("h2, h3"):
        text = tag.get_text()
        id = text if (text and (text not in ids)) else str()
        if not id:
            suffix = 0
            while True:
                id = f"{text}_{suffix}"
                if id not in ids:
                    break
                suffix += 1
        ids.add(id)
        tag["id"] = id
        elm = {"text": text, "id": id, "children": []}
        if tag.name == "h2":
            toc.append(elm)
        else:
            if not toc:
                toc.append(
                    {
                        "text": None,
                        "id": None,
                        "children": [elm],
                    }
                )
            else:
                toc[-1]["children"].append(elm)
    if len(toc) == 1 and toc[0]["text"] is None:
        toc = toc[0]["children"]

    toc_bs = BeautifulSoup()
    nav = toc_bs.new_tag("nav")
    nav.attrs["class"] = "toc"
    toc_bs.append(nav)
    for item in toc:
        if item["text"]:
            ul = toc_bs.new_tag("ul")
            nav.append(ul)
            li = toc_bs.new_tag("li")
            ul.append(li)
            a = toc_bs.new_tag("a", href="#" + item["id"])
            li.append(a)
            a.append(item["text"])
            if item["children"]:
                ul_children = toc_bs.new_tag("ul")
                li.append(ul_children)
                for child in item["children"]:
                    li = toc_bs.new_tag("li")
                    ul_children.append(li)
                    a = toc_bs.new_tag("a", href="#" + child["id"])
                    li.append(a)
                    a.append(child["text"])

    return bs, toc_bs


def download_notion_internal(bs: BeautifulSoup, target_dir: Path):
    for tag in bs.select(".internal"):
        file_url = tag.attrs["href"]
        file_id, file_name = urllib.parse.urlparse(file_url).path.split("/")[-2:]
        with urlopen(file_url) as file:
            dest = target_dir / file_id
            dest.mkdir(parents=True, exist_ok=True)
            with open(dest / file_name, "wb") as f:
                f.write(file.read())
        new_tag = BeautifulSoup().new_tag("a", href=f"{file_id}/{file_name}")
        new_tag.string = file_name
        new_tag.attrs["class"] = list(filter(lambda c: c != "internal", tag["class"]))
        tag.replace_with(new_tag)
        logging.info(f"FILE: notion internal file {file_id} is downloaded")
    return bs


def get_posts(db: str, secret: str):
    url = f"https://api.notion.com/v1/databases/{db}/query"
    headers = {
        "Authorization": f"Bearer {secret}",
        "Notion-Version": "2022-06-28",
        "Content-Type": "application/json",
    }
    start_cursor = None
    posts = []
    while True:
        req_body = {}
        req_body["filter"] = {
            "and": [
                {"property": "status", "status": {"equals": "Published"}},
                {"property": "title", "rich_text": {"is_not_empty": True}},
                {"property": "publish", "date": {"is_not_empty": True}},
                {"property": "dir", "select": {"is_not_empty": True}},
            ]
        }
        if start_cursor:
            req_body["start_cursor"] = start_cursor
        with urlopen(Request(url, json.dumps(req_body).encode(), headers)) as res:
            body = json.loads(res.read())
            posts.extend(body["results"])
        if body["has_more"]:
            start_cursor = body["next_cursor"]
        else:
            break
    logging.info(f"total {len(posts)} posts were found")
    return posts


def generate(posts: list[dict], contents_dir: str, author: str, secret: str):
    for existing_dir in Path(contents_dir).iterdir():
        if not existing_dir.is_dir():
            continue
        for existing_post in existing_dir.iterdir():
            if not existing_post.is_dir():
                continue
            existing_id = existing_post.name
            new_post = list(filter(lambda x: x["id"] == existing_id, posts))
            if (
                len(new_post) == 0
                or new_post[0]["properties"]["dir"]["select"]["name"]
                != existing_dir.name
            ):
                logging.info(
                    f"delete removed/moved post {existing_dir.name}/{existing_id}"
                )
                for content in existing_post.iterdir():
                    if content.is_dir():
                        for file in content.iterdir():
                            file.unlink()
                        content.rmdir()
                    else:
                        content.unlink()
                existing_post.rmdir()

    for post in posts:
        id: str = post["id"]
        notion_last_edited: str = post["last_edited_time"]
        props: dict = post["properties"]
        dir: str = props["dir"]["select"]["name"]

        post_dir = Path(contents_dir) / dir / id
        post_index = post_dir / "index.html"
        if post_index.exists():
            with open(post_index, "r") as existing:
                ex_html = existing.read()
            front = re.compile(r"^{.*?^}", re.MULTILINE | re.DOTALL).match(ex_html)
            if front:
                meta = json.loads(front[0])
                if meta.get("notion_last_edited", "") == notion_last_edited:
                    logging.info(f"{dir}/{id} already exists")
                    continue
            logging.info(f"{dir}/{id} is updated")
            for content in post_dir.iterdir():
                if content.is_dir():
                    for file in content.iterdir():
                        file.unlink()
                    content.rmdir()
                else:
                    content.unlink()

        logging.info(f"generate {dir}/{id}")

        ast = subprocess.run(
            ["notion2pandoc", "-i", id, "-s", secret], capture_output=True
        ).stdout
        ast_dict = json.loads(ast)

        html = subprocess.run(
            ["pandoc", "--katex", "--from", "json", "--to", "html", "--no-highlight"],
            input=ast,
            capture_output=True,
        ).stdout
        bs = BeautifulSoup(html, "html.parser")

        summary, summary_length = "", 0
        for char in subprocess.run(
            ["pandoc", "--katex", "--from", "json", "--to", "plain"],
            input=ast,
            capture_output=True,
        ).stdout.decode():
            if char == "\n":
                char = "" if summary.endswith(" / ") else " / "
            summary += char
            summary_length += sum(
                (2 if east_asian_width(c) in "FWA" else 1) for c in char
            )
            if summary_length > 280:
                break

        title = "".join(map(lambda x: x["text"]["content"], props["title"]["title"]))
        tags = list(map(lambda x: x["name"], props["tags"]["multi_select"]))
        math = len(bs.select(".math")) != 0
        toc = ast_dict["meta"]["toc"]["c"]
        date = props["publish"]["date"]["start"]
        lastmod = props["publish"]["date"]["end"] or date

        front_matter = {
            "title": title,
            "tags": tags,
            "author": author,
            "summary": summary,
            "math": math,
            "date": date,
            "lastmod": lastmod,
            "notion_last_edited": notion_last_edited,
        }

        post_dir.mkdir(parents=True, exist_ok=True)
        bs = convert_embed(bs)
        bs = convert_code_block(bs)
        bs = convert_internal_link(bs, "..", posts)
        bs = download_notion_internal(bs, post_dir)
        output_str = json.dumps(front_matter, indent=2, ensure_ascii=False)
        if toc:
            bs, bs_toc = generate_toc(bs)
            output_str += f"\n{bs_toc.decode()}\n{bs.decode()}"
        else:
            output_str += f"\n{bs.decode()}"

        with open(post_index, "w") as index:
            index.write(output_str)


def generate_about_me(
    id: str, posts: list[dict], contents_dir: str, author: str, secret: str
):
    ast = subprocess.run(
        ["notion2pandoc", "-i", id, "-s", secret], capture_output=True
    ).stdout
    ast_dict = json.loads(ast)

    html = subprocess.run(
        ["pandoc", "--katex", "--from", "json", "--to", "html", "--no-highlight"],
        input=ast,
        capture_output=True,
    ).stdout
    bs = BeautifulSoup(html, "html.parser")

    front_matter = {
        "title": ast_dict["meta"]["title"]["c"],
        "author": author,
        "math": len(bs.select(".math")) != 0,
    }

    post_dir = Path(contents_dir) / "about"
    bs = convert_embed(bs)
    bs = convert_code_block(bs)
    bs = convert_internal_link(bs, ".", posts)
    bs = download_notion_internal(bs, post_dir)

    with open(post_dir / "index.html", "w") as index:
        index.write(f"{json.dumps(front_matter, indent=2)}\n{bs.decode()}")


if __name__ == "__main__":
    CONTENTS_DIR = "content"
    SECRET = os.environ["NOTION_API_SECRET"]
    DB_ID = os.environ["NOTION_DB_UUID"]
    AUTHOR = os.environ["NOTION_AUTHOR"]
    ABOUT_ME_ID = os.environ["NOTION_ABOUT_ME_ID"]
    posts = get_posts(DB_ID, SECRET)
    generate(posts, CONTENTS_DIR, AUTHOR, SECRET)
    generate_about_me(ABOUT_ME_ID, posts, CONTENTS_DIR, AUTHOR, SECRET)
