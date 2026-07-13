#!/usr/bin/env python3
"""Generate a blog post thumbnail with Cloudflare Workers AI and wire it into the post's front matter.

Usage: python3 scripts/generate_thumbnail.py content/posts/<slug>.md
Requires CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN in the environment.
"""
import json
import os
import re
import sys
import urllib.request

MODEL = "@cf/stabilityai/stable-diffusion-xl-base-1.0"
IMAGES_DIR = "static/images/posts"


def read_front_matter(text):
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    if not match:
        raise ValueError("front matter not found")
    return match.group(1)


def get_field(front_matter, key):
    match = re.search(rf'^{key}:\s*"?([^"\n]+)"?\s*$', front_matter, re.MULTILINE)
    return match.group(1).strip() if match else None


def build_prompt(title, description):
    return (
        "Clean modern flat-illustration thumbnail for a Korean finance/legal "
        "information blog post, 16:9 landscape composition. No text, no letters, "
        "no numbers, no watermarks. "
        f"Topic: {title}. Context: {description}. "
        "Style: minimal flat design, soft muted color palette, simple geometric "
        "shapes and icons related to the topic (documents, buildings, coins, "
        "calendar), plenty of whitespace, professional and trustworthy tone, "
        "no photorealism."
    )


def generate_image(prompt, account_id, api_token):
    url = f"https://api.cloudflare.com/client/v4/accounts/{account_id}/ai/run/{MODEL}"
    body = json.dumps({"prompt": prompt}).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=120) as resp:
        content_type = resp.headers.get("Content-Type", "")
        raw = resp.read()

    if content_type.startswith("image/"):
        return raw

    # Some Workers AI responses come back as JSON with a base64 "result".
    payload = json.loads(raw)
    if not payload.get("success", False):
        raise RuntimeError(f"Workers AI error: {json.dumps(payload)[:500]}")
    result = payload["result"]
    if isinstance(result, dict) and "image" in result:
        import base64
        return base64.b64decode(result["image"])
    raise RuntimeError(f"unexpected response shape: {json.dumps(payload)[:500]}")


def insert_thumbnail_field(text, front_matter, thumbnail_path):
    if get_field(front_matter, "thumbnail"):
        return re.sub(
            r'^thumbnail:\s*"?[^"\n]+"?\s*$',
            f'thumbnail: "{thumbnail_path}"',
            text,
            count=1,
            flags=re.MULTILINE,
        )
    return re.sub(r"^---\n", f'---\nthumbnail: "{thumbnail_path}"\n', text, count=1)


def main():
    if len(sys.argv) != 2:
        print("usage: generate_thumbnail.py <path-to-post.md>", file=sys.stderr)
        sys.exit(1)

    post_path = sys.argv[1]
    account_id = os.environ.get("CLOUDFLARE_ACCOUNT_ID")
    api_token = os.environ.get("CLOUDFLARE_API_TOKEN")
    if not account_id or not api_token:
        print("CLOUDFLARE_ACCOUNT_ID and CLOUDFLARE_API_TOKEN must be set", file=sys.stderr)
        sys.exit(1)

    with open(post_path, encoding="utf-8") as f:
        text = f.read()

    front_matter = read_front_matter(text)
    title = get_field(front_matter, "title") or ""
    description = get_field(front_matter, "description") or ""

    slug = os.path.splitext(os.path.basename(post_path))[0]
    prompt = build_prompt(title, description)
    print(f"Generating thumbnail for: {title}")
    image_bytes = generate_image(prompt, account_id, api_token)

    os.makedirs(IMAGES_DIR, exist_ok=True)
    image_path = os.path.join(IMAGES_DIR, f"{slug}.png")
    with open(image_path, "wb") as f:
        f.write(image_bytes)

    thumbnail_url = f"/images/posts/{slug}.png"
    updated_text = insert_thumbnail_field(text, front_matter, thumbnail_url)
    with open(post_path, "w", encoding="utf-8") as f:
        f.write(updated_text)

    print(f"Saved {image_path}, front matter updated with thumbnail: {thumbnail_url}")


if __name__ == "__main__":
    main()
