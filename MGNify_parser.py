import time
from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
import csv
from selenium.common.exceptions import WebDriverException

start_time = time.time()


#Путь к драйверу (chromedriver.exe)
PATH_TO_DRIVER = ""

options = Options()
options.add_argument('--headless')
options.add_argument('--disable-gpu')
driver = webdriver.Chrome(executable_path = PATH_TO_DRIVER, chrome_options=options)

#парсинг всех страниц бд
studies = []

pages = (i for i in range(1,13))#всего их было 13 штук когда я это писал
for pageNum in pages:
    if pageNum != 1:
        url = 'https://www.ebi.ac.uk/metagenomics/browse/studies?page=' + str(pageNum) + '&biome=root%3AEnvironmental%3ATerrestrial%3ASoil&page_size=50'
    else:
        url = 'https://www.ebi.ac.uk/metagenomics/browse/studies?biome=root%3AEnvironmental%3ATerrestrial%3ASoil&page_size=50'
    #бд использует динамическую загрузку из json файла в html страницу, 
    #так что необходимо подгружать страницу с помощью виртуального браузера
    driver.get(url)
    time.sleep(10)
    page = driver.page_source
    driver.quit()

    soup = BeautifulSoup(page, 'lxml')
    links = soup.find_all('a', href = True)
    for link in links:
        if link['href'].find('MGYS') != -1:
            url = "https://www.ebi.ac.uk" + link['href']
            print(url)
            studies.append(url)
#общее число исследований
count = len(studies)

with open('MG_id.tsv', 'w') as file:
    tsv_writer = csv.writer(file, delimiter='\t')
    tsv_writer.writerow(['File structure is as follows: String_number   MGnify_ID'])
    for i in range(count):
        tsv_writer.writerow([i, studies[i]])

urls = []

error = 45

with open('MG_id.tsv', 'r') as file:
    tsv_reader = csv.reader(file, delimiter='\t')
    next(tsv_reader)
    for row in tsv_reader:
        if row:
            if int(row[0]) >= error:
                urls.append(row[-1])

#общее получившееся число

sample = 'https://www.ebi.ac.uk/metagenomics/samples/'
analisys = 'https://www.ebi.ac.uk/metagenomics/analyses/'

with open('samples.tsv', 'a') as file:
    tsv_writer = csv.writer(file, delimiter='\t')
    for line in urls:
        flag = 0
        samples = []
        analyzes = []
        links = []
        links.append(line)
        for url in links:
            try:
                driver.get(url)
                time.sleep(3)
                page = driver.page_source
                driver.quit()
            except WebDriverException:
                samples.append("page down" + url)
                analyzes.append("page down" + url)

            soup = BeautifulSoup(page, 'lxml')
            #добавляет в urls все страницы, доступные по этому MGnify_id
            if flag == 0:
                buttons = soup.find_all('button', class_="vf-button vf-button--link vf-pagination__link")
                if buttons:
                    page = buttons[-2].text
                    for c in page:#есть ли другие страницы
                        if c.isdigit():
                            flag = 1
                            break
                    if flag == 1:
                        MaxPage = int(page[5:])
                        n_pages = (i for i in range(2, MaxPage + 1))
                        for i in n_pages:
                            links.append(url + '?analyses-page=' + str(i) + '#overview')

            rows = soup.find_all('tr', class_="vf-table__row")
            for row in rows[1:]:#1: т.к. заголовок таблицы также попадает под параметры find_all
                array = row.get_text(' ').split()
                samples.append(sample + array[0])
                analyzes.append(analisys + array[-1])

        for i in range(len(samples)):
                print(count, '\t', samples[i], '\t', analyzes[i], '\t', line)
                tsv_writer.writerow([count, samples[i], analyzes[i]])
                count += 1

print("write number of input and output file")
fio = input()

print("write starting line")
start = int(input())

print("write ending line")
end = int(input())

metadata_url = []
OTU_url = []

file_urls = []
info = []
count = 0

input_file = "samples_true_" + fio + ".tsv"
output_file = "output\output_file" + fio + ".tsv"

#получение url-ссылок на файлы с результатами исследований
with open(input_file, 'r') as fin:
    tsv_reader = csv.reader(fin, delimiter='\t')
    next(tsv_reader)
    with open(output_file, 'a') as fout:
        tsv_writer = csv.writer(fout, delimiter='\t')
        for row in tsv_reader:
            if row:
                count += 1
                if count >= end:
                    exit()
                if count >= start:
                    metadata_url.append(row[-2])
                    OTU_url.append(row[-1])
                    if (count % 1000) == 0 or (end - count) < 1000:
                        for i in range(len(metadata_url)):
                            print(i + 1, metadata_url[i], OTU_url[i])

                            meta_url = metadata_url[i]
                            try:
                                driver.get(meta_url)
                                time.sleep(3)
                                meta_page = driver.page_source
                            except WebDriverException:
                                info.append("page down" + meta_url)
                                continue
                                    
                            url = OTU_url[i] + '#download'#чтобы сразу перейти в нужный раздел
                            try:
                                driver.get(url)
                                time.sleep(3)
                                OTU_page = driver.page_source
                                        
                                driver.quit()
                            except WebDriverException:
                                file_urls.append("page down" + url)
                                continue

                            meta_soup = BeautifulSoup(meta_page, 'lxml')
                            OTU_soup = BeautifulSoup(OTU_page, 'lxml')

                            #получение url для файла OTU.tsv
                            rows = OTU_soup.find_all('tr', class_="vf-table__row")
                            for row in rows:
                                flag = 0
                                string = row.get_text('\t')
                                if string.find('OTUs and taxonomic assignments for SSU rRNA') != -1 and string.find('TSV') != -1:
                                    flag = 1
                                    s_row = str(row)
                                    index_1 = s_row.find('https')
                                    index_2 = s_row.find('tsv')
                                    new_url = ''
                                    for c in s_row[index_1:index_2 + 3]:
                                        new_url += c
                                    file_urls.append(new_url)
                                    break
                            if flag == 0:
                                file_urls.append("no tsv_file url???? " + url)

                            #получение metadata для sample
                            metadata = meta_soup.find('div', class_="vf-grid vf-grid__col-2")
                            try:
                                string = metadata.get_text('\t')
                            except AttributeError:
                                string = None
                            if string != None:
                                array = string.split('\t')
                                a = ((i*3 - 1) for i in range(1,len(array)//2))
                                for index in a:
                                    array.insert(index, "###")#разделяет в строчке разные параметры sample с помощью ###
                                info.append(str(array))
                            else:
                                info.append("no metadata???? " + meta_url)
                            if len(file_urls) == 10:#чтобы не перегружать переменную info

                                try:
                                    for i in range(len(info)):
                                        print(count, info[i], '\n', file_urls[i])
                                        tsv_writer.writerow([count, file_urls[i], info[i].encode('utf-8')])

                                except IndexError:#обработка ошибки, которой никогда не могло быть, но один раз она всё же появилась
                                    subtraction = len(info) - len(file_urls)

                                    if subtraction > 0:
                                        for i in range(len(file_urls)):
                                            print(count, info[i], '\n', file_urls[i])
                                            tsv_writer.writerow([count, file_urls[i], info[i]])
                                        for i in range(len(file_urls), subtraction + 1):
                                            print(count, info[i], '\n', "file is lost")
                                            tsv_writer.writerow([count, "file is lost", info[i]])

                                    if subtraction < 0:
                                        for i in range(len(info)):
                                            print(count, info[i], '\n', file_urls[i])
                                            tsv_writer.writerow([count, file_urls[i], info[i]])
                                        for i in range(len(info), (-1) * subtraction + 1):
                                            print(count, "info is lost", '\n', file_urls[i])
                                            tsv_writer.writerow([count, file_urls[i], "info is lost"])

                                    if subtraction == 0:
                                        for i in range(len(info)):
                                            print(count, info[i], '\n', file_urls[i])
                                            tsv_writer.writerow([count, file_urls[i], info[i]])
                                file_urls = []
                                info = []
                            else:
                                try:
                                    for i in range(len(info)):
                                        print(count, info[i], '\n', file_urls[i])
                                        tsv_writer.writerow([count, file_urls[i], info[i].encode('utf-8')])

                                except IndexError:#обработка ошибки, которой никогда не могло быть, но один раз она всё же появилась
                                    subtraction = len(info) - len(file_urls)

                                    if subtraction > 0:
                                        for i in range(len(file_urls)):
                                            print(count, info[i], '\n', file_urls[i])
                                            tsv_writer.writerow([count, file_urls[i], info[i]])
                                        for i in range(len(file_urls), subtraction + 1):
                                            print(count, info[i], '\n', "file is lost")
                                            tsv_writer.writerow([count, "file is lost", info[i]])

                                    if subtraction < 0:
                                        for i in range(len(info)):
                                            print(count, info[i], '\n', file_urls[i])
                                            tsv_writer.writerow([count, file_urls[i], info[i]])
                                        for i in range(len(info), (-1) * subtraction + 1):
                                            print(count, "info is lost", '\n', file_urls[i])
                                            tsv_writer.writerow([count, file_urls[i], "info is lost"])

                                    if subtraction == 0:
                                        for i in range(len(info)):
                                            print(count, info[i], '\n', file_urls[i])
                                            tsv_writer.writerow([count, file_urls[i], info[i]])
                                file_urls = []
                                info = []
                        metadata_url = []
                        OTU_url = []