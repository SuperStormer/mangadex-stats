import itertools
import json
import os
import statistics
from collections import Counter, defaultdict
from pathlib import Path

from md_api import MangadexAPI
from pydantic import BaseModel

EXPORT_FILE = Path("md_export.json")


class Manga(BaseModel):
	id: str
	title: str | None
	rating: int | None
	last_chapter: int | None
	status: str


def chunk(it, size):
	it = iter(it)
	return iter(lambda: tuple(itertools.islice(it, size)), ())


def login():
	client = MangadexAPI()
	try:
		with open("refresh_token") as f:
			client.load_refresh_token(f.read())
	except FileNotFoundError:
		client.login(os.environ["MD_USER"], os.environ["MD_PWD"])
	with open("refresh_token", "w") as f:
		f.write(client.refresh_token)
	return client


def main():
	client = login()
	if EXPORT_FILE.exists():
		with EXPORT_FILE.open("r") as f:
			entries = json.load(f)
			all_manga = [Manga.model_validate(entry) for entry in entries]
	else:
		all_manga: list[Manga] = []
	statuses_data = client.get("/manga/status")["statuses"]

	manga_lists = defaultdict(list)
	for manga_id, status in statuses_data.items():
		manga_lists[status].append(manga_id)

	for status, manga_ids in manga_lists.items():  # noqa: PLR1702
		print(f"{status}:")
		# split up the list to prevent 414 errors
		for sub_list in chunk(manga_ids, 100):
			ratings_data = client.get(
				"/rating", params=[("manga[]", manga_id) for manga_id in sub_list]
			)["ratings"]

			manga_data = {
				manga["id"]: manga
				for manga in client.get(
					"/manga",
					params=[("ids[]", manga_id) for manga_id in sub_list]
					+ [
						("contentRating[]", "safe"),
						("contentRating[]", "suggestive"),
						("contentRating[]", "erotica"),
						("contentRating[]", "pornographic"),
						("includes[]", "manga"),
						("limit", 100),
					],
				)["data"]
			}

			read_marker_data = client.get(
				"/manga/read",
				params=[("ids[]", manga_id) for manga_id in sub_list]
				+ [("grouped", "true")],
			)["data"]

			for manga_id in sub_list:
				print(manga_id)

				# get title
				titles = manga_data[manga_id]["attributes"]["title"]
				title = (
					titles.get("en")
					or titles.get("ja-ro")
					or titles.get("ja")
					or next(titles.values())
				)

				# get rating
				rating = None
				if isinstance(ratings_data, dict):
					rating_datum = ratings_data.get(manga_id)
					if rating_datum is not None:
						rating = rating_datum["rating"]

				# get last chapter
				read_markers = read_marker_data.get(manga_id) or []
				chapter_feed = {}
				for offset in itertools.count(0, 100):  # pagination
					chapter_feed_data = client.get(
						f"/manga/{manga_id}/feed",
						params=[
							("contentRating[]", "safe"),
							("contentRating[]", "suggestive"),
							("contentRating[]", "erotica"),
							("contentRating[]", "pornographic"),
							("translatedLanguage[]", "en"),
							("offset", offset),
						],
					)
					chapter_feed |= {
						chapter["id"]: chapter for chapter in chapter_feed_data["data"]
					}
					if chapter_feed_data["total"] <= offset + 100:
						break

				read_chapters = []
				for read_marker in read_markers:
					if read_marker in chapter_feed:
						chapter = chapter_feed[read_marker]
						chapter_num = chapter["attributes"]["chapter"]
						if chapter_num is not None:
							try:
								read_chapters.append(int(float(chapter_num)))
							except ValueError:
								pass

				if read_chapters:
					last_chapter = max(read_chapters)
				elif read_markers:  # handle oneshots
					if len(read_markers) == 1:
						last_chapter = 1
					else:
						print(f"{manga_id} has read markers without chapter numbers")
						last_chapter = None
				else:
					last_chapter = None

				manga = Manga(
					id=manga_id,
					title=title,
					rating=rating,
					last_chapter=last_chapter,
					status=status,
				)
				print(manga)
				all_manga.append(manga)
				with EXPORT_FILE.open("w") as f:
					json.dump([manga.model_dump() for manga in all_manga], f)

	with EXPORT_FILE.open("w") as f:
		json.dump([manga.model_dump() for manga in all_manga], f)


if __name__ == "__main__":
	main()
