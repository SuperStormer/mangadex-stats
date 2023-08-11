import itertools
import os
import statistics
from collections import Counter, defaultdict

from md_api import MangadexAPI

def chunk(it, size):
	it = iter(it)
	return iter(lambda: tuple(itertools.islice(it, size)), ())

def print_rating_summary(ratings):
	if not ratings:
		print("n/a")
		return
	counter = Counter(ratings)
	for rating, count in sorted(counter.items(), reverse=True):
		print(f"{rating}: {count}")
	mean = statistics.mean(ratings)
	stdev = statistics.pstdev(ratings)
	print(f"Mean: {mean:.3} Stdev: {stdev:.3}")

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
	
	statuses_data = client.get("/manga/status")["statuses"]
	
	manga_lists = defaultdict(list)
	for key, value in statuses_data.items():
		manga_lists[value].append(key)
	
	all_ratings = []
	for list_name, manga in manga_lists.items():
		print(f"{list_name}:")
		# split up the list to prevent 414 errors
		ratings = []
		for sub_list in chunk(manga, 100):
			ratings_data = client.get("/rating",
				params=[("manga[]", value) for value in sub_list])["ratings"]
			if isinstance(ratings_data, list):  # no ratings found
				continue
			else:
				ratings.extend([rating["rating"] for rating in ratings_data.values()])
		
		print_rating_summary(ratings)
		print()
		
		all_ratings.extend(ratings)
	
	print(f"All")
	print_rating_summary(all_ratings)

if __name__ == "__main__":
	main()