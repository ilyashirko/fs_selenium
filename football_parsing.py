import sqlite3
import time
from datetime import datetime

from bs4 import BeautifulSoup as bs
from environs import Env
from selenium import webdriver
from selenium.common.exceptions import NoSuchElementException, TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from tqdm import tqdm

CHROMEDRIVER_PATH = 'driver/chromedriver'

BASE_FS_URL = 'https://www.flashscore.ru.com/match/'

BASE_FOOTBALL_URL = 'https://www.flashscore.ru.com/football/'

FOOTBALL_TAG = 'id="g_1'


class SkipThis(Exception):
    pass


def start_webdriver_chrome():
    chrome_options = webdriver.ChromeOptions()
    chrome_options.add_argument('--headless')
    chrome_options.add_argument('--disable-gpu')
    driver = webdriver.Chrome(CHROMEDRIVER_PATH, options=chrome_options)
    driver.maximize_window()
    wait = WebDriverWait(driver, 5)
    return driver, wait


# На случай если страница с первого раза не прогрузилась
def wait_by_cn(url, class_name, driver, wait):
    chk_err = 0
    response = None
    while response is None and chk_err != 10:
        try:
            response = wait.until(EC.presence_of_element_located((
                By.CLASS_NAME,
                class_name
            )))
        except NoSuchElementException:
            print(f'Перезапускаю driver: {class_name}')
            driver.quit()
            driver, wait = start_webdriver_chrome()
            driver.get(url)
            chk_err += 1
    return response


def find_all_matches(driver, url=BASE_FOOTBALL_URL):
    matches_id = []

    driver.get(url)
    time.sleep(5)

    # скролл до подвала для подгруза всего содержимого страницы
    driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

    closed_containers = driver.find_elements(
        By.CLASS_NAME,
        'event__expander--close'
    )

    if closed_containers:
        print('Есть закрытые контейнеры. Открываю...')
        for container in tqdm(closed_containers):
            driver.execute_script(
                "arguments[0].scrollIntoView(true)",
                container
            )
            # Иногда всплывают окна с рекламой / cookies
            # Чтобы они не заслоняли целевой фрагмент страницы,
            # скролл ближе к центру экрана
            driver.execute_script(f'window.scrollBy(0, {-200});')
            container.click()

    page_source = driver.page_source
    urls_number = page_source.count(FOOTBALL_TAG)
    searching_step = 0
    for id in range(urls_number):
        searching_index = page_source.find(FOOTBALL_TAG, searching_step)
        searching_step = searching_index + 16
        matches_id.append(
            page_source[searching_index + 8:searching_index + 16]
        )
    return matches_id


def clearData(data):
    data = ''.join(data.split('\n'))
    data = ''.join(data.split('\t'))
    data = data.strip()
    return data


def convert_results(final_result, base_result):
    try:
        final_result = [int(x.text) for x in final_result.findChildren('span')]
    except ValueError:
        final_result = [None, None]
    try:
        base_result = [int(x.text) for x in base_result.findChildren('span')]
        final_result = [final_result[x] - base_result[x] for x in range(2)]
        return base_result + final_result
    except (ValueError, AttributeError):
        base_result = [None, None]

    return final_result + base_result


def get_base_and_h2h_info(driver, wait, match_id):
    h2h_url = f'{BASE_FS_URL}{match_id}/#/h2h/overall'

    driver.get(h2h_url)

    source = wait_by_cn(h2h_url, 'container__detail', driver, wait)
    h2h_info = bs(source.get_attribute('innerHTML'), 'html.parser')

    try:
        geo = h2h_info.find(
            'span', 'tournamentHeader__country').text.split(':')
        country = clearData(geo[0])
        championship = clearData(geo[1])
        if championship.find(' Тур ') > 0:
            championship = championship.split(" - Тур")[0]
    except AttributeError:
        country = championship = None
        print(f'BULLSHIT with {match_id}: not found geo!')

    try:
        start_time = h2h_info.find(
            'div', class_='duelParticipant__startTime').text
        timestamp = datetime.timestamp(
            datetime.strptime(clearData(start_time), '%d.%m.%Y %H:%M')
        )
    except AttributeError:
        timestamp = None
        print(f'BULLSHIT with {match_id}: not found start time!')

    games_info = []
    h2h_main = wait_by_cn(h2h_url, 'h2h', driver, wait)
    h2h_source = bs(h2h_main.get_attribute('innerHTML'), 'html.parser')
    result_groups = h2h_source.find_all('div', class_='h2h__section section')
    teams = []
    for group in result_groups:
        group_title = group.find('div', class_='section__title').text
        if group_title.find('Последние игры') >= 0:
            group_title = clearData(group_title).split(': ')[1]
            teams.append(group_title)
        else:
            group_title = clearData(group_title)

        group_games = group.find_all('div', class_='h2h__row')
        queue = 1
        for game in group_games:
            date = game.find('span', class_='h2h__date').text
            participants = game.find_all('span', class_='h2h__participant')
            results = convert_results(
                game.find('span', class_='h2h__result'),
                game.find('span', class_='h2h__result__fulltime')
            )
            games_info.append(
                (
                    match_id,
                    group_title,
                    queue,
                    int(datetime.timestamp(
                        datetime.strptime(date, '%d.%m.%y')
                    )),
                    participants[0].text,
                    participants[1].text,
                    results[0],
                    results[1],
                    results[2],
                    results[3]
                )
            )
            queue += 1
    if len(teams) != 2 or teams[0] == teams[1]:
        raise SkipThis

    match_info = (
        match_id,
        country,
        championship,
        int(timestamp),
        teams[0],
        teams[1],
        None,
        None,
        None,
        None,
        f'{BASE_FS_URL}{match_id}'
    )
    return match_info, games_info


def make_draw(won_title, lost_title, all_stat):
    all_stat.update(
        {'Ничьи': int(all_stat[won_title]) + int(all_stat[lost_title])}
    )
    all_stat.pop(won_title)
    all_stat.pop(lost_title)
    return all_stat


def get_statistics(driver, wait, match_id):
    stat_url = f'{BASE_FS_URL}{match_id}/#/standings/table/overall'
    driver.get(stat_url)

    try:
        stat_source = wait.until(EC.presence_of_element_located((
            By.CLASS_NAME, 'tableWrapper')))
    except TimeoutException:
        return None

    stat_info = bs(stat_source.get_attribute('innerHTML'), 'html.parser')

    temp = stat_info.find('div', class_='ui-table__header')
    temp.findChild('div', title='Последние 5 матчей').extract()
    temp = temp.findChildren('div')

    headers = []
    for head in temp:
        head = head.get('title')
        headers.append(head)

    stata_table = stat_info.find('div', class_='ui-table__body')
    items_to_delete = stata_table.findChildren(
        'div', class_='table__cell--form')
    for item in items_to_delete:
        item.extract()

    stata_table_rows = stata_table.findChildren('div', recursive=False)
    results = []
    for row in stata_table_rows:
        row_info = row.findChildren(recursive=False)
        all_stat = {}
        for num, item in enumerate(row_info):
            item = clearData(item.text)
            all_stat.update({headers[num]: item})

        if 'Ничьи' not in all_stat:

            if 'Побед по буллитам' in all_stat:
                all_stat = make_draw(
                    'Побед по буллитам', 'Поражений по буллитам', all_stat)

            elif 'Побед в овертайме' in all_stat:
                all_stat = make_draw(
                    'Побед в овертайме', 'Поражений в овертайме', all_stat)

            elif 'Wins Penalties':
                all_stat = make_draw(
                    'Wins Penalties', 'Losses Penalties', all_stat)

            else:
                all_stat.update({'Ничьи': None})

        goals_scored, goals_conceded = all_stat['Голы'].split(':')
        results.append(
            (
                match_id,
                all_stat['Место'],
                all_stat[list(all_stat.keys())[1]],
                all_stat['Игры'],
                all_stat['Выигрыши'],
                all_stat['Ничьи'],
                all_stat['Проигрыши'],
                goals_scored,
                goals_conceded,
                all_stat['Очки']
            )
        )
    return results


def check_status(driver, match_id):
    try:
        driver.get(f'{BASE_FS_URL}{match_id}')
        status = driver.find_element(
            By.CLASS_NAME, 'detailScore__status').text.strip()
        return status == '&nbsp;' or status == ' ' or status == ''
    except NoSuchElementException:
        raise SkipThis


def download_matches(driver: webdriver,
                     wait: WebDriverWait,
                     fs: sqlite3.Connection,
                     cursor: sqlite3.Cursor,
                     matches_id: list) -> int:
    uploaded = 0
    for match_id in tqdm(matches_id):
        try:
            # from edit_db import remove_today
            # remove_today(cursor, fs, match_id)
            status = check_status(driver, match_id)
            if not status:
                continue

            check_note = cursor.execute(
                "SELECT match_id FROM matches where match_id = '%s'"
                % match_id
            )
            if check_note.fetchone() is not None:
                continue
            match_info, games_info = get_base_and_h2h_info(
                driver, wait, match_id)
            statistics = get_statistics(driver, wait, match_id)
            cursor.execute(
                "INSERT INTO matches VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                match_info
            )
            for game in games_info:
                cursor.execute(
                    "INSERT INTO games VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                    game
                )
            if statistics is not None:
                for stata in statistics:
                    cursor.execute(
                        "INSERT INTO statistics VALUES(?, ?, ?, ?, ?, ?, ?, ?, ?, ?);",
                        stata
                    )
            fs.commit()
            uploaded += 1
        except SkipThis:
            continue
    return uploaded


if __name__ == '__main__':
    env = Env()
    env.read_env()

    fs = sqlite3.connect(env.str('DATABASE'))
    cursor = fs.cursor()

    driver, wait = start_webdriver_chrome()
    matches_id = find_all_matches(driver)

    download_matches(driver, wait, fs, cursor, matches_id)
