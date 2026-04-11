"""BBC Good Food spider.

Run via: scrapy runspider worker/spiders/bbcgoodfood.py
"""
import logging
import os

import scrapy
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

custom_settings = {
    "DOWNLOAD_DELAY": 2,
    "AUTOTHROTTLE_ENABLED": True,
    "ROBOTSTXT_OBEY": True,
    "USER_AGENT": "Cookit/1.0 (educational project; contact: admin@example.com)",
    "LOG_LEVEL": "INFO",
}


class BBCGoodFoodSpider(scrapy.Spider):
    name = "bbcgoodfood"
    allowed_domains = ["bbcgoodfood.com"]
    start_urls = ["https://www.bbcgoodfood.com/recipes"]
    custom_settings = custom_settings

    def parse(self, response):
        for link in response.css("a[href*='/recipes/']::attr(href)").getall():
            if "/recipes/" in link and link.count("/") >= 2:
                yield response.follow(link, self.parse_recipe)

        next_page = response.css("a[rel='next']::attr(href)").get()
        if next_page:
            yield response.follow(next_page, self.parse)

    def parse_recipe(self, response):
        soup = BeautifulSoup(response.text, "html.parser")

        title_tag = soup.find("h1")
        title = title_tag.get_text(strip=True) if title_tag else ""
        if not title:
            return

        ingredients = []
        for li in soup.select(".ingredients-list li, [class*='ingredient']"):
            text = li.get_text(strip=True)
            if text:
                ingredients.append({"name": text, "quantity": None, "unit": None})

        steps = []
        for idx, li in enumerate(soup.select(".method__list li, [class*='method'] li"), start=1):
            text = li.get_text(strip=True)
            if text:
                steps.append({"step_number": idx, "instruction": text})

        if not ingredients or not steps:
            return

        cuisine_tag = soup.select_one("[class*='cuisine']")
        cuisine = cuisine_tag.get_text(strip=True) if cuisine_tag else None

        tags = [tag.get_text(strip=True) for tag in soup.select("[class*='tag']")]

        yield {
            "title": title,
            "source_url": response.url,
            "ingredients": ingredients,
            "steps": steps,
            "cuisine": cuisine,
            "tags": tags[:10],
        }
