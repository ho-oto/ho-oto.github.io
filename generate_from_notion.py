import json
import logging
import os
import re
import subprocess
import urllib.parse
from pathlib import Path
from urllib.request import Request, urlopen

from bs4 import BeautifulSoup

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
        logging.info(f"FILE: notion internal file {id} is downloaded")
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
            ["pandoc", "--katex", "--from", "json", "--to", "html"],
            input=ast,
            capture_output=True,
        ).stdout
        bs = BeautifulSoup(html, "html.parser")

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
            "math": math,
            "toc": toc,
            "date": date,
            "lastmod": lastmod,
            "notion_last_edited": notion_last_edited,
        }

        post_dir.mkdir(parents=True, exist_ok=True)
        bs = convert_embed(bs)
        bs = download_notion_internal(bs, post_dir)
        with open(post_index, "w") as index:
            index.write(f"{json.dumps(front_matter, indent=2)}\n{bs.decode()}")


if __name__ == "__main__":
    CONTENTS_DIR = "content"
    SECRET = os.environ["NOTION_API_SECRET"]
    DB_ID = os.environ["NOTION_DB_UUID"]
    AUTHOR = os.environ["NOTION_AUTHOR"]
    posts = get_posts(DB_ID, SECRET)
    generate(posts, CONTENTS_DIR, AUTHOR, SECRET)
