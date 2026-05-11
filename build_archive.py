#!/usr/bin/env python3

import json
import urllib.parse
import urllib.request
from collections import defaultdict

COLLECTION = "aadamjacobs"
ROWS = 100
USER_AGENT = "ArchiveMusicLibrary/2.0"


def fetch_json(url):
    req = urllib.request.Request(
        url,
        headers={"User-Agent": USER_AGENT}
    )
    with urllib.request.urlopen(req, timeout=60) as response:
        return json.loads(response.read().decode("utf-8"))


def search_items():
    """Récupère tous les documents de la collection en parcourant toutes les pages."""
    page = 1
    all_docs = []

    while True:
        query = urllib.parse.quote(f'collection:({COLLECTION})')

        url = (
            "https://archive.org/advancedsearch.php"
            f"?q={query}"
            "&fl[]=identifier"
            "&fl[]=title"
            "&fl[]=creator"
            "&fl[]=date"
            f"&rows={ROWS}"
            f"&page={page}"
            "&output=json"
        )

        data = fetch_json(url)
        docs = data["response"]["docs"]

        if not docs:
            break

        print(f"Page {page}: {len(docs)} éléments")
        all_docs.extend(docs)

        if len(docs) < ROWS:
            break

        page += 1

    return all_docs


def normalize_creator(creator):
    if isinstance(creator, list):
        return creator[0].strip() if creator else None
    if isinstance(creator, str):
        return creator.strip()
    return None


def guess_artist_from_title(title):
    separators = [" - ", " – ", ": ", "_"]
    for sep in separators:
        if sep in title:
            return title.split(sep, 1)[0].strip()
    return title.strip()


def fallback_image(artist):
    encoded = urllib.parse.quote(artist)
    return (
        "https://ui-avatars.com/api/"
        f"?name={encoded}&size=800"
        "&background=1f2937"
        "&color=ffffff"
        "&bold=true"
    )


def fetch_artist_image(artist):
    try:
        query = urllib.parse.quote(artist)
        data = fetch_json(
            f"https://itunes.apple.com/search?term={query}&entity=musicArtist&limit=1"
        )

        if data.get("results"):
            artist_id = data["results"][0].get("artistId")
            if artist_id:
                lookup = fetch_json(
                    f"https://itunes.apple.com/lookup?id={artist_id}&entity=album&limit=5"
                )

                for result in lookup.get("results", []):
                    artwork = result.get("artworkUrl100")
                    if artwork:
                        return artwork.replace("100x100bb", "1200x1200bb")
    except Exception:
        pass

    return fallback_image(artist)


def main():
    docs = search_items()

    grouped = defaultdict(list)
    seen = set()

    for doc in docs:
        identifier = doc.get("identifier")
        if not identifier:
            continue

        title = doc.get("title") or identifier

        creator = normalize_creator(doc.get("creator"))
        artist = creator if creator else guess_artist_from_title(title)

        url = f"https://archive.org/details/{identifier}"

        unique_key = (artist, identifier)
        if unique_key in seen:
            continue
        seen.add(unique_key)

        grouped[artist].append({
            "title": title,
            "url": url,
            "date": doc.get("date", "")
        })

    output = []

    for artist in sorted(grouped.keys(), key=str.lower):
        links = sorted(
            grouped[artist],
            key=lambda x: (x.get("date") or "", x["title"])
        )

        output.append({
            "artist": artist,
            "image": fetch_artist_image(artist),
            "links": [
                {
                    "title": item["title"],
                    "url": item["url"]
                }
                for item in links
            ]
        })

    with open("artists.json", "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)

    print(f"{len(output)} artistes générés.")
    print("Fichier artists.json mis à jour.")


if __name__ == "__main__":
    main()
