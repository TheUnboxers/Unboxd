import requests
import itertools
import time
import sys
import os
import bs4
import pandas as pd

if os.getcwd().endswith("helpers"):
    from paths import Path
else:
    from .paths import Path


SCRAPED_COLUMNS = ["original_title", "release_year", "user_rating"]
type ScrapedRating = tuple[str, int, float | None]


def scrape_ratings(username: str, print_status: bool = False) -> list[ScrapedRating]:
    """Returns the scraped Letterboxd ratings of `username`"""
    if print_status:
        print("starting scraping ratings")
    scraped_ratings: list[ScrapedRating] = []
    page_url = "https://letterboxd.com/{}/films/page/{}/"

    for page_number in itertools.count(start=1, step=1):
        if print_status:
            print(f"scraping page {page_number}...")
        try:
            response = requests.get(page_url.format(username, page_number))
            time.sleep(2)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            if print_status: print(f"failed to get {page_url} because {e}")
            """
            A retry mechanism is worth implementing, but the scraper currently 
            needs to stop here. Otherwise, the scraper keeps requesting 
            for pages that do not exist, and it does not terminate.
            """
            break
        html = response.text

        # Using lxml over builtin html.parser for speed
        soup = bs4.BeautifulSoup(markup=html, features="lxml")

        films = soup.find_all(name="li", class_="griditem")
        if len(films) == 0:
            break
        
        for film in films:
            poster = film.find(name="div", attrs={"data-component-class": "LazyPoster"})
            # should not happen
            if poster is None:
                continue
            original_title_and_release_year = poster.get(
                key="data-item-full-display-name"
            )
            # should not happen, but there is also no point in scraping an unknown film
            if not isinstance(original_title_and_release_year, str):
                continue
            example_suffix = " (2099)"
            split_index = len(original_title_and_release_year) - len(example_suffix)
            original_title = original_title_and_release_year[:split_index]

            # remove whitespace and parentheses from release year suffix and parse as int
            release_year = int(original_title_and_release_year[split_index + 2 : -1])

            user_rating_element = film.find(name="span", attrs={"class": "rating"})
            if user_rating_element is None:
                user_rating = None
            else:
                user_rating_symbols = user_rating_element.get_text()
                user_rating = user_rating_symbols.count(
                    "★"
                ) + 0.5 * user_rating_symbols.count("½")

            scraped_ratings.append((original_title, release_year, user_rating))

        page_numbers = soup.find_all(name="li", class_="paginate-page")
        if len(page_numbers) == 0:
            break
        last_page_number = int(page_numbers.pop().get_text())
        if page_number == last_page_number:
            break
    if print_status:
        print("finished scraping")
    return scraped_ratings


def scrape_pfp_url(username: str) -> str:
    """Returns the scraped Letterboxd profile picture url `username`"""
    page_url = f"https://letterboxd.com/{username}/"
    try:
        response = requests.get(page_url)
        response.raise_for_status()
    except requests.exceptions.RequestException:
        return ""
    html = response.text
    soup = bs4.BeautifulSoup(markup=html, features="html.parser")
    try:
        pfp_grandparent = soup.find(name="div", class_="profile-avatar")
        pfp_element = pfp_grandparent.find(name="img")
        return pfp_element.get("src")
    except AttributeError:
        return ""
    except Exception:
        return ""


def main():
    username = sys.argv[1]
    if "ratings" in sys.argv:
        data = scrape_ratings(username, print_status=True)
        os.makedirs(Path.RATINGS_FOLDER, exist_ok=True)
        df = pd.DataFrame(data, columns=SCRAPED_COLUMNS)
        df.to_csv(os.path.join(Path.RATINGS_FOLDER, f"{username}.csv"), index=False)
    if "pfp" in sys.argv:
        print("pfp url:", scrape_pfp_url(username))


if __name__ == "__main__":
    main()
    
