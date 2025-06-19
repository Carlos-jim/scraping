import requests
from bs4 import BeautifulSoup
import time
import random
from datetime import datetime, timedelta
import os
from fake_useragent import UserAgent
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

KEYWORDS = ['desarrollador web', 'frontend', 'programador junior', 'programador', 'desarrollador junior']
DAYS_BACK = 7

SELENIUM_PATH = './chromedriver'
CHROME_OPTIONS = Options()
CHROME_OPTIONS.add_argument('--headless')
CHROME_OPTIONS.add_argument('--disable-gpu')
CHROME_OPTIONS.add_argument('--no-sandbox')

ua = UserAgent()

def get_random_headers():
    return {
        'User-Agent': ua.random,
        'Accept-Language': 'es-ES,es;q=0.9',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
        'Referer': 'https://www.google.com/'
    }

def get_current_week_dates():
    end_date = datetime.now()
    start_date = end_date - timedelta(days=DAYS_BACK)
    return start_date, end_date

def parse_date(date_str, site):
    try:
        date_str = date_str.lower().strip()

        if 'hace' in date_str:
            if 'hora' in date_str:
                hours = int(date_str.split()[1])
                return datetime.now() - timedelta(hours=hours)
            elif 'día' in date_str or 'dias' in date_str:
                days = int(date_str.split()[1])
                return datetime.now() - timedelta(days=days)

        if site == 'computrabajo':
            return datetime.strptime(date_str, '%d/%m/%Y')
        elif site == 'unmejorempleo':
            return datetime.strptime(date_str, '%Y-%m-%d')

        return datetime.now()
    except:
        return datetime.now()

def handle_captcha(driver):
    try:
        WebDriverWait(driver, 10).until(
            EC.presence_of_element_located((By.ID, 'recaptcha'))
        )
        print("CAPTCHA detectado, intentando resolver...")
        time.sleep(10)
        driver.refresh()
        return True
    except:
        return False

def scrape_with_selenium(url, max_retries=3):
    driver = None
    for attempt in range(max_retries):
        try:
            options = Options()
            options.add_argument('--headless')
            options.add_argument('--disable-gpu')
            options.add_argument('--no-sandbox')

            service = Service(SELENIUM_PATH)
            driver = webdriver.Chrome(service=service, options=options)
            driver.get(url)

            if handle_captcha(driver):
                continue

            WebDriverWait(driver, 10).until(
                EC.presence_of_element_located((By.TAG_NAME, 'body')))

            return BeautifulSoup(driver.page_source, 'html.parser')

        except Exception as e:
            print(f"Intento {attempt + 1} fallido: {e}")
            time.sleep(random.uniform(2, 5))
        finally:
            if driver:
                driver.quit()
    return None

def scrape_computrabajo(keyword, max_results=50):
    base_url = "https://ve.computrabajo.com"
    urls = []
    start_date, _ = get_current_week_dates()
    search_url = f"{base_url}/trabajo-de-{keyword.replace(' ', '-')}"

    try:
        session = requests.Session()

        response = session.get(search_url, headers=get_random_headers())
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        job_cards = soup.find_all('article', {'class': 'box_offer'})

        for card in job_cards[:max_results]:
            try:
                date_tag = card.find('p', class_='fs13')
                if date_tag:
                    date_str = date_tag.get_text(strip=True)
                    job_date = parse_date(date_str, 'computrabajo')

                    if job_date >= start_date:
                        title_tag = card.find('h2', class_='fs18')
                        if title_tag and title_tag.a:
                            job_url = title_tag.a.get('href')
                            if job_url:
                                full_url = f"{base_url}{job_url}" if not job_url.startswith('http') else job_url
                                urls.append((full_url, job_date.strftime('%Y-%m-%d')))

            except Exception as e:
                print(f"Error procesando oferta en Computrabajo: {e}")
                continue

        time.sleep(random.uniform(2, 5))

    except Exception as e:
        print(f"Error scraping Computrabajo: {e}")
        print("Intentando con Selenium...")
        soup = scrape_with_selenium(search_url)
        if soup:
            pass

    return urls

def scrape_unmejorempleo(keyword, max_results=50):
    base_url = "https://www.unmejorempleo.com.ve"
    urls = []
    start_date, _ = get_current_week_dates()
    search_url = f"{base_url}/trabajo-{keyword.replace(' ', '-')}.html"

    try:
        session = requests.Session()

        response = session.get(search_url, headers=get_random_headers())
        response.raise_for_status()

        soup = BeautifulSoup(response.text, 'html.parser')
        job_cards = soup.find_all('div', {'class': 'item-normal'})

        for card in job_cards[:max_results]:
            try:
                date_tag = card.find('span', class_='date')
                if date_tag:
                    date_str = date_tag.get_text(strip=True)
                    job_date = parse_date(date_str, 'unmejorempleo')

                    if job_date >= start_date:
                        title_tag = card.find('h3', class_='no-margin-top')
                        if title_tag and title_tag.a:
                            job_url = title_tag.a.get('href')
                            if job_url:
                                full_url = f"{base_url}{job_url}" if not job_url.startswith('http') else job_url
                                urls.append((full_url, job_date.strftime('%Y-%m-%d')))

            except Exception as e:
                print(f"Error procesando oferta en UnMejorEmpleo: {e}")
                continue

        time.sleep(random.uniform(2, 5))

    except Exception as e:
        print(f"Error scraping UnMejorEmpleo: {e}")
        print("Intentando con Selenium...")
        soup = scrape_with_selenium(search_url)
        if soup:
            pass

    return urls

def scrape_multiple_sites(keywords):
    all_urls = set()
    for keyword in keywords:
        print(f"\nBuscando trabajos con la palabra clave: {keyword}")

        print("Buscando en Computrabajo.ve...")
        ct_urls = scrape_computrabajo(keyword)
        all_urls.update(ct_urls)
        print(f"Encontradas {len(ct_urls)} URLs válidas en Computrabajo.ve")

        print("Buscando en UnMejorEmpleo.ve...")
        ume_urls = scrape_unmejorempleo(keyword)
        all_urls.update(ume_urls)
        print(f"Encontradas {len(ume_urls)} URLs válidas en UnMejorEmpleo.ve")

        time.sleep(random.uniform(5, 10))

    sorted_urls = sorted(all_urls, key=lambda x: x[1], reverse=True)
    return sorted_urls

def save_urls_to_file(urls, filename='job_urls.txt'):
    start_date, end_date = get_current_week_dates()
    date_range = f"{start_date.strftime('%Y-%m-%d')} al {end_date.strftime('%Y-%m-%d')}"

    with open(filename, 'w', encoding='utf-8') as f:
        f.write(f"Ofertas de trabajo encontradas ({date_range})\n")
        f.write("="*50 + "\n\n")

        for url, date in urls:
            f.write(f"[{date}] {url}\n")

    print(f"\nSe han guardado {len(urls)} URLs en {filename}")

if __name__ == "__main__":
    print("Iniciando scraping avanzado de ofertas de trabajo...")
    start_time = time.time()

    job_urls = scrape_multiple_sites(KEYWORDS)

    print("\nResumen:")
    print(f"Total de URLs encontradas: {len(job_urls)}")
    start_date, end_date = get_current_week_dates()
    print(f"Rango de fechas: {start_date.strftime('%Y-%m-%d')} a {end_date.strftime('%Y-%m-%d')}")

    print("\nAlgunas URLs encontradas (más recientes primero):")
    for url, date in job_urls[:5]:
        print(f"- [{date}] {url}")

    save_urls_to_file(job_urls)
    elapsed_time = time.time() - start_time
    print(f"\nTiempo total de ejecución: {elapsed_time:.2f} segundos")
