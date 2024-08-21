import asyncio
import csv
import time
import traceback
import logging

import numpy as np
from lxml import html
from playwright.async_api import async_playwright, Error

# Lista de classes a buscar
temp_class = "xpath=.//a[contains(@class, 'flex items-center justify-center h-8 px-3 bg-gray-medium cursor-pointer')]"
ms_class = "xpath=.//div[contains(@class, 'bg-gray-dark text-white-main mb-3 mt-2 flex min-h-[60px] items-center gap-2 p-2 text-sm')]"
pagination_class = "xpath=.//a[contains(@class, 'pagination-link')]"
event_class = ".//div[contains(@class, 'eventRow flex w-full flex-col text-xs')]"
act_jv_class = "xpath=.//div[contains(@class, 'bg-gray-light mb-3 mt-2 flex h-auto min-h-[30px] items-center gap-2 py-1 pl-3')]"
act_java_class = '.bg-gray-light.mb-3.mt-2.flex.h-auto.min-h-\\[30px\\].items-center.gap-2.py-1.pl-3'
local_t_class = ".//a[contains(@class, 'min-mt:!justify-end flex min-w-0 basis-[50%] cursor-pointer items-start justify-start gap-1 overflow-hidden')]"
visit_t_class = ".//a[contains(@class, 'justify-content min-mt:!gap-2 flex basis-[50%] cursor-pointer items-center gap-1 overflow-hidden')]"
score_class = ".//div[contains(@class, 'min-mt:!flex hidden')]"
one_two_class = ".//div[contains(@class, 'flex-center border-black-main min-w-[60px] max-w-[60px] flex-col gap-1 border-l border-opacity-10')]"
momios_class = ".//a[contains(@class, 'next-m:flex next-m:!mt-0 ml-2 mt-2 min-h-[32px] w-full hover:cursor-pointer')]"

extra_class = '//div[@class="relative flex flex-col"]'
handicap_class = './/p[@class="breadcrumbs-m:!hidden"]'
momios_extra_class = './/div[@class="flex-center border-black-main min-w-[60px] max-w-[60px] flex-col gap-1 border-l border-opacity-10"]'

async def scroll(cs_page, num_scrolls):
    await cs_page.wait_for_load_state("networkidle")

    for i in range(num_scrolls):
        await cs_page.mouse.wheel(0, 1000)
        await asyncio.sleep(0.1)

    await cs_page.wait_for_load_state("networkidle")

async def write_to_csv(file_path, data):
    with open(file_path, mode='a', newline='', encoding='utf-8') as file:
        writer = csv.DictWriter(file, fieldnames=[
            'Temporada', 'Pagina', 'Numer event','Local', 'Visitante', 'Goles Local', 'Goles Visitante', 
            'Momio 1', 'Momio X', 'Momio 2', 'AH', 'Over/Under'
        ])
        if file.tell() == 0:
            writer.writeheader()  # Escribir encabezado solo si el archivo está vacío
        writer.writerows(data)
        
async def asian_mm(browser, temp_url):
    
    #Navegar a la página
    ah_page = await browser.new_page()
    
    
    while True:
        try:
            await ah_page.goto(temp_url)
            await scroll(ah_page, 8)
            break  # Salir del bucle si la página se carga correctamente
        except Error as e:
            await ah_page.close()
            logging.info(f"Error al navegar a la URL: {e}")
            logging.info("Reintentando...")
            time.sleep(5)
            ah_page = await browser.new_page()

    #Obtener el contenido de la página
    conten_ah = await ah_page.content()
    tree_asian = html.fromstring(conten_ah)
    
    # Cerar la pagina
    await ah_page.close()
    
    # Crear una matriz de -5 a 5 con un intervalo de 0.25
    handicap_range = np.arange(-5, 5.25, 0.25)
    handicap_matrix = {f"{handicap:+.2f}": {"1": '0', "2": '0'} for handicap in handicap_range}

    # Encuentra todos los Handicap asiaticos
    hd_asiatico = tree_asian.xpath(extra_class)

    for i, hd_asiatico in enumerate(hd_asiatico):
        
        # Handicap asiatico
        ah_txt = hd_asiatico.xpath(handicap_class)

        if ah_txt:
            # Handicap asiatico
            ah_div = ah_txt[0].text_content()
            ah_div = ah_div[3:].strip()

            # Ajustar formato para que coincida con el formato esperado
            if ah_div == '0':
                formatted_handicap = '+0.00'
            elif ah_div.startswith('+') or ah_div.startswith('-'):
                # Convertir a float y luego a string con formato
                try:
                    formatted_handicap = f"{float(ah_div):+.2f}"
                except ValueError:
                    formatted_handicap = ah_div  # Si no se puede convertir, usar el valor original
            else:
                formatted_handicap = ah_div

            # Momios 1 2
            elements_txt = hd_asiatico.xpath(momios_extra_class)
            if not elements_txt:
                ah_1 = '0'
                ah_2 = '0'
            else:
                ah_1 = elements_txt[0].text_content() if len(elements_txt) > 0 and elements_txt[0] is not None else '0'
                ah_2 = elements_txt[1].text_content() if len(elements_txt) > 1 and elements_txt[1] is not None else '0'
            
            ah_1 = '0' if ah_1 == '-' else ah_1
            ah_2 = '0' if ah_2 == '-' else ah_2
            
            # Llenar la matriz con los valores encontrados
            if formatted_handicap in handicap_matrix:
                handicap_matrix[formatted_handicap]["1"] = ah_1
                handicap_matrix[formatted_handicap]["2"] = ah_2
    return handicap_matrix
    
async def over_under_mm(browser, temp_url):
    
    #Navegar a la página
    ov_page = await browser.new_page()
    
    while True:
        try:
            await ov_page.goto(temp_url)
            await scroll(ov_page, 8)
            break  # Salir del bucle si la página se carga correctamente
        except Error as e:
            await ov_page.close()
            logging.info(f"Error al navegar a la URL: {e}")
            logging.info("Reintentando...")
            time.sleep(5)
            ov_page = await browser.new_page()

    #Obtener el contenido de la página
    conten_ah = await ov_page.content()
    tree_ou = html.fromstring(conten_ah)
    
    # Cerar la pagina
    await ov_page.close()
    
    # Crear una matriz de -5 a 5 con un intervalo de 0.25
    over_under_range = np.arange(-10, 10.25, 0.25)
    over_under_matrix = {f"{over_under:+.2f}": {"1": "0", "2": "0"} for over_under in over_under_range}

    # Encuentra todos los Over Under
    ov_un = tree_ou.xpath(extra_class)
    
    for i, ov_un in enumerate(ov_un):
        # Over Under
        ov_txt = ov_un.xpath(handicap_class)

        if ov_txt:
            # Handicap asiatico
            ov_div = ov_txt[0].text_content()
            ov_div = ov_div[4:].strip()

            # Ajustar formato para que coincida con el formato esperado
            if ov_div == '0':
                formatted_handicap = '+0.00'
            elif ov_div.startswith('+') or ov_div.startswith('-'):
                # Convertir a float y luego a string con formato
                try:
                    formatted_handicap = f"{float(ov_div):+.2f}"
                except ValueError:
                    formatted_handicap = ov_div  # Si no se puede convertir, usar el valor original
            else:
                formatted_handicap = ov_div

            # Momios 1 2
            elements_txt = ov_un.xpath(momios_extra_class)
            if not elements_txt:
                ou_2 = '0'
                ou_2 = '0'
            else:
                ou_1 = elements_txt[0].text_content() if len(elements_txt) > 0 and elements_txt[0] is not None else '0'
                ou_2 = elements_txt[1].text_content() if len(elements_txt) > 1 and elements_txt[1] is not None else '0'
 
        
            ou_1 = '0' if ou_1 == '-' else ou_1
            ou_2 = '0' if ou_2 == '-' else ou_2
            
            # Llenar la matriz con los valores encontrados
            if formatted_handicap in over_under_matrix:
                over_under_matrix[formatted_handicap]["1"] = ou_1
                over_under_matrix[formatted_handicap]["2"] = ou_2

    return over_under_matrix


async def general_data(browser, temp_url, base_url, log_temp):
    # Variables
    prime_time = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
    event_data = []
    next_page = False
    
    # Navegar a la URL
    general_page = await browser.new_page()
    
    while True:
        try:
            await general_page.goto(temp_url)
            await scroll(general_page, 12)
            await general_page.query_selector_all(act_jv_class)
            await general_page.wait_for_load_state("networkidle")
            break  # Salir del bucle si la página se carga correctamente
        except Error as e:
            await general_page.close()
            logging.info(f"Error al navegar a la URL: {e}")
            logging.info("Reintentando...")
            time.sleep(5)
            general_page = await browser.new_page()



    # Paginación
        # Mensaje no hay datos
    ms_no_data = await general_page.query_selector_all(ms_class)
    if not ms_no_data:
        num_paginas = await general_page.query_selector_all(pagination_class)
        if num_paginas:
            for pagina in num_paginas:
                text = await pagina.text_content()
                next_page = True if text == "Next" else next_page 
    else:
        #print(ms_no_data)
        #print("No hay datos en la página")
        #print('No hay paginación en la página')
        return event_data, next_page

    
    # Obtener el contenido HTML de la página
    page_source = await general_page.content()
    tree = html.fromstring(page_source)
    
    # Cerrar página
    await general_page.close()
    events = tree.xpath(event_class)
    #print(f'Numero de eventos: {len(events)}')

    # Páginación
    for i, event in enumerate(events):

            
        # Log datos 
        #print(log_temp[0])
        #print(log_temp[1])
        log_event = f"Evento {i+1} de {len(events)}"
        #print(log_event)
        #print('Hora de extracion:')
        #print(prime_time)
        #print(time.strftime("%Y-%m-%d %H:%M:%S", time.localtime()))
        
        # Momios extra
        momios = event.xpath(momios_class)
        mm_url = momios[0].get('href')
        
        # AH
        url_ah = f'{base_url}{mm_url}#ah;2'
        asian_np = await asian_mm(browser, url_ah)
        
        # O/V
        url_ov = f'{base_url}{mm_url}#over-under;2'
        over_under_np = await over_under_mm(browser, url_ov)
                 
        # Equipo Local
        local_element = event.xpath(local_t_class)
        local_div = local_element[0].get('title')
        
        # Equipo Visitante
        visitante_element = event.xpath(visit_t_class)
        visitante_div = visitante_element[0].get('title')

        # Goles
        goles_element = event.xpath(score_class)
        if not goles_element:
            goles_local = '0'
            goles_visitante = '0'
        else:
                # Goles Local
            goles_local = goles_element[0].text_content()
                # Goles Visitante
            goles_visitante = goles_element[1].text_content()

        
        # Momios 1x2
        momios_element = event.xpath(one_two_class)
        if momios_element:
                # Momio 1
            momio_1 = momios_element[0].text_content()
                # Momio X
            momio_x = momios_element[1].text_content()
                # Momio 2
            momio_2 = momios_element[2].text_content()
        else:
            momio_1 = '0'
            momio_x = '0'
            momio_2 = '0'
        
        # Agregar información del partido a la lista
        event_data.append({
            'Temporada': (log_temp[0]),
            'Pagina': (log_temp[1]),
            'Numer event': (log_event),
            'Local': local_div,
            'Visitante': visitante_div,
            'Goles Local': goles_local,
            'Goles Visitante': goles_visitante,
            'Momio 1': momio_1,
            'Momio X': momio_x,
            'Momio 2': momio_2,
            'AH': asian_np,
            'Over/Under': over_under_np,
        })

        # Imprimir los datos del evento
        #print(f"Local: {local_div}")
        #print(f"Visitante: {visitante_div}")
        #print(f"Goles Local: {goles_local}")
        #print(f"Goles Visitante: {goles_visitante}")
        #print(f"Momio 1: {momio_1}")
        #print(f"Momio X: {momio_x}")
        #print(f"Momio 2: {momio_2}")
        #print("Momios asiáticos:")
        #for handicap, momios in asian_np.items():
        #    print(f"{handicap}: {momios['1']} - {momios['2']}")
        #print("-" * 80)
        #print("Over/Under:")
        #for over_under, momios in over_under_np.items():
        #    print(f"{over_under}: {momios['1']} - {momios['2']}")
        #print("-" * 80)
            
    return event_data, next_page
    


async def run(browser, url_now, base_url, temp_out):
    # Configuración básica del logging
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

    # Crear una nueva página y navegar a la URL
    page = await browser.new_page()
    
    while True:
        try:
            await page.goto(url_now)
            await page.wait_for_load_state("networkidle")
            break  # Salir del bucle si la página se carga correctamente
        except Error as e:
            await page.close()
            logging.info(f"Error al navegar a la URL: {e}")
            logging.info("Reintentando...")
            time.sleep(5)
            page = await browser.new_page()

    # Seleccionar todos los elementos usando XPath
    elementos = await page.query_selector_all(temp_class)
    
    # Extraer datos de la página actual
    temp_urls = []
    for elemento in elementos:
        temp_url = await elemento.get_attribute('href')
        temp_urls.append(temp_url)
        
    # Cerrar la página actual
    await page.close()
    #Log 
    logging.info(f"Numero de temporadas: {len(temp_urls)}")
    for i, temp_url in enumerate(temp_urls):
        page_index = 1

        # Comparar la URL actual con la URL del elemento
        # Verificar si tiene paginación
        while True:

            # Log
            temp_scrap = f"Temporada para extraer datos {i+1} de {len(temp_urls)}"
            #print(temp_scrap)
            page_scrap = f'Pagina actual {page_index}'
            #print(page_scrap)
            log_temp = [temp_scrap, page_scrap]
            
            #Cargar la pagina adecuada
            next_url = temp_url if page_index == 1 else f'{temp_url}#/page/{page_index}'
            
            # Contador de pagina
            page_index += 1
            
            #Extraer datos generales
            event_data, status_pagination = await general_data(browser, next_url, base_url, log_temp)
            logging.info(f'Temporada: {i+1}')
            logging.info(f'Pagina: {(page_index-1)}')
            logging.info(f"Eventos extraidos: {len(event_data)}")
            await write_to_csv(temp_out, event_data)
            if not status_pagination: break

async def main():
    async with async_playwright() as playwright:
        # Declarar variables
        base_url = "https://www.oddsportal.com"
        url_scrap = "/football/paraguay/primera-division/results/"
        temp_out = '/home/semarnat/soccer/data/paraguay_primera-division.csv'
        scrap_url = base_url + url_scrap
        
            # Configurar el navegador
        firefox = playwright.firefox
        browser = await firefox.launch(headless=True)
        
        # Ejecutar la función principal
        await run(browser, scrap_url, base_url, temp_out)


# Ejecutar la función principal
try:
    asyncio.run(main())
except Exception as e:
    print(f"Error al ejecutar el script: {e}")
    traceback.print_exc()