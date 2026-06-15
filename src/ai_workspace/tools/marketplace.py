"""
Marketplace search tools for CrewAI agents.

Searches Mercado Livre and OLX for product listings and prices.
Used by deep research agents to price items.
"""

from __future__ import annotations

import json
import re
from typing import Any, Type

import httpx
from bs4 import BeautifulSoup
from pydantic import BaseModel, Field

from crewai.tools import BaseTool


class MarketplaceSearchInput(BaseModel):
    """Input schema for marketplace search tools."""
    query: str = Field(description="Search query — product name or description")
    max_results: int = Field(default=10, description="Maximum number of results to return")
    max_price: float | None = Field(default=None, description="Optional maximum price filter (BRL)")


class MercadoLivreSearchTool(BaseTool):
    """Searches Mercado Livre Brasil for product listings.

    Returns a list of listings with title, price, condition, sold count, and URL.
    Use this to find market prices for products sold in Brazil.
    """

    name: str = "mercado_livre_search"
    description: str = (
        "Searches Mercado Livre Brasil for product listings and prices. "
        "Returns title, price in BRL, condition (new/used), units sold, and seller rating. "
        "Use this to estimate the market value of any product. "
        "For best results, use the exact product name as it appears on the site."
    )
    args_schema: Type[BaseModel] = MarketplaceSearchInput

    def _run(self, query: str, max_results: int = 10, max_price: float | None = None) -> str:
        """Search Mercado Livre Brasil."""
        ml_results = self._search_ml(query, max_results, max_price)

        if not ml_results:
            return f"No results found on Mercado Livre for: {query}"

        # Format output
        output = f"=== MERCADO LIVRE: '{query}' ===\n\n"
        prices = []
        for i, r in enumerate(ml_results[:max_results], 1):
            output += (
                f"{i}. {r['title'][:120]}\n"
                f"   💰 Preço: R$ {r['price']:.2f}"
            )
            if r.get("condition"):
                output += f" | {r['condition']}"
            if r.get("sold"):
                output += f" | {r['sold']} vendidos"
            if r.get("seller_rating"):
                output += f" | Vendedor: {r['seller_rating']}"
            output += f"\n   🔗 {r['url']}\n\n"
            prices.append(r["price"])

        if prices:
            avg = sum(prices) / len(prices)
            output += (
                f"---\n"
                f"📊 Análise: {len(prices)} anúncios encontrados\n"
                f"   Preço médio: R$ {avg:.2f}\n"
                f"   Preço mínimo: R$ {min(prices):.2f}\n"
                f"   Preço máximo: R$ {max(prices):.2f}\n"
            )

        return output

    def _search_ml(self, query: str, limit: int = 10, max_price: float | None = None) -> list[dict]:
        """Scrape Mercado Livre search results."""
        results = []
        try:
            encoded = query.replace(" ", "%20")
            url = (
                f"https://lista.mercadolivre.com.br/{encoded}"
                f"?_ITEM*CONDITION=2230581,2230580"
            )

            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,*/*",
                        "Accept-Language": "pt-BR,pt;q=0.9",
                    },
                )
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # Mercado Livre uses various CSS selectors — try multiple
            items = (
                soup.select("li.ui-search-layout__item") or
                soup.select("div.andes-card") or
                soup.select("div.ui-search-result__wrapper")
            )

            for item in items:
                if len(results) >= limit * 2:
                    break

                # Title
                title_el = (
                    item.select_one("h2.ui-search-item__title") or
                    item.select_one("a.ui-search-item__group__element") or
                    item.select_one("h3")
                )
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                # Price
                price_el = (
                    item.select_one("span.andes-money-amount__fraction") or
                    item.select_one("span.price-tag-fraction") or
                    item.select_one("span.ui-search-price__second-line .andes-money-amount__fraction")
                )
                if not price_el:
                    continue

                try:
                    price_str = price_el.get_text(strip=True).replace(".", "")
                    price = float(price_str)
                except ValueError:
                    continue

                if max_price and price > max_price:
                    continue

                # Link
                link_el = item.select_one("a.ui-search-item__group__element") or item.select_one("a")
                url = link_el.get("href", "") if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://www.mercadolivre.com.br{url}"

                # Condition
                condition = ""
                cond_el = item.select_one("span.ui-search-item__subtitle")
                if cond_el:
                    cond_text = cond_el.get_text(strip=True).lower()
                    if "usado" in cond_text:
                        condition = "Usado"
                    elif "novo" in cond_text or "nuevo" in cond_text:
                        condition = "Novo"
                    elif "reacondicionado" in cond_text:
                        condition = "Recondicionado"

                # Sold count
                sold = ""
                sold_el = item.select_one("span.ui-search-item__installments-and-sold")
                if sold_el:
                    sold_text = sold_el.get_text(strip=True)
                    m = re.search(r"(\d+)\s*vendido", sold_text)
                    if m:
                        sold = m.group(1)

                results.append({
                    "title": title,
                    "price": price,
                    "url": url,
                    "condition": condition,
                    "sold": sold,
                    "seller_rating": "",
                })

            return results[:limit]

        except Exception as e:
            return [{"title": f"Error searching Mercado Livre: {e}", "price": 0, "url": ""}]


class OLXSearchTool(BaseTool):
    """Searches OLX Brasil for used/refurbished product listings.

    Returns a list of listings with title, price, condition, and URL.
    OLX is better for used items, local sales, and bulk lots.
    """

    name: str = "olx_search"
    description: str = (
        "Searches OLX Brasil for product listings and prices. "
        "Returns title, price in BRL, condition, location, and date. "
        "OLX is best for used items, local classifieds, and bulk/atacado lots. "
        "Use this alongside Mercado Livre to get a complete market picture."
    )
    args_schema: Type[BaseModel] = MarketplaceSearchInput

    def _run(self, query: str, max_results: int = 10, max_price: float | None = None) -> str:
        """Search OLX Brasil."""
        olx_results = self._search_olx(query, max_results, max_price)

        if not olx_results:
            return f"No results found on OLX for: {query}"

        output = f"=== OLX: '{query}' ===\n\n"
        prices = []
        for i, r in enumerate(olx_results[:max_results], 1):
            price_display = f"R$ {r['price']:.2f}" if r['price'] else "Preço sob consulta"
            output += (
                f"{i}. {r['title'][:120]}\n"
                f"   💰 {price_display}"
            )
            if r.get("condition"):
                output += f" | {r['condition']}"
            if r.get("location"):
                output += f" | {r['location']}"
            if r.get("date"):
                output += f" | {r['date']}"
            output += f"\n   🔗 {r['url']}\n\n"
            if r["price"] > 0:
                prices.append(r["price"])

        if prices:
            avg = sum(prices) / len(prices)
            output += (
                f"---\n"
                f"📊 Análise: {len(prices)} anúncios com preço\n"
                f"   Preço médio: R$ {avg:.2f}\n"
                f"   Preço mínimo: R$ {min(prices):.2f}\n"
                f"   Preço máximo: R$ {max(prices):.2f}\n"
            )

        return output

    def _search_olx(self, query: str, limit: int = 10, max_price: float | None = None) -> list[dict]:
        """Scrape OLX search results."""
        results = []
        try:
            encoded = query.replace(" ", "%20")
            # OLX search URL
            url = f"https://www.olx.com.br/brasil?q={encoded}&sf=1"

            with httpx.Client(timeout=30.0, follow_redirects=True) as client:
                response = client.get(
                    url,
                    headers={
                        "User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                        "Accept": "text/html,application/xhtml+xml,*/*",
                        "Accept-Language": "pt-BR,pt;q=0.9",
                    },
                )
                response.raise_for_status()

            soup = BeautifulSoup(response.text, "lxml")

            # OLX listing selectors
            items = (
                soup.select("li[data-listitem]") or
                soup.select("div.sc-1fcmfes-0") or
                soup.select("section.olx-ad-card")
            )

            for item in items:
                if len(results) >= limit * 2:
                    break

                # Title
                title_el = (
                    item.select_one("h2") or
                    item.select_one("a[data-lurker-detail='list_id']") or
                    item.select_one("span[data-ds-component='ad-card-title']")
                )
                if not title_el:
                    continue
                title = title_el.get_text(strip=True)

                # Price
                price_el = (
                    item.select_one("span[data-ds-component='ad-card-price']") or
                    item.select_one("p.sc-ifofvx-0") or
                    item.select_one("span.olx-ad-card__price")
                )
                price = 0
                if price_el:
                    try:
                        price_str = price_el.get_text(strip=True)
                        price_str = re.sub(r"[^\d,]", "", price_str)
                        price_str = price_str.replace(",", ".")
                        price = float(price_str)
                    except ValueError:
                        price = 0

                if max_price and price > max_price:
                    continue

                # Link
                link_el = item.select_one("a[data-lurker-detail='list_id']") or item.select_one("a")
                url = link_el.get("href", "") if link_el else ""
                if url and not url.startswith("http"):
                    url = f"https://www.olx.com.br{url}"

                # Location
                location = ""
                loc_el = item.select_one("span.sc-1p5nwzz-0") or item.select_one("p.sc-ks3qj0-1")
                if loc_el:
                    location = loc_el.get_text(strip=True)

                results.append({
                    "title": title,
                    "price": price,
                    "url": url,
                    "condition": "Usado",  # OLX is primarily used items
                    "location": location,
                    "date": "",
                })

            return results[:limit]

        except Exception as e:
            return [{"title": f"Error searching OLX: {e}", "price": 0, "url": ""}]
