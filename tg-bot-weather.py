import json
import os
import requests


FUNC_RESPONSE = {'statusCode': 200, 'body': ''}
TELEGRAM_BOT_TOKEN = os.environ.get('TG_BOT_TOKEN')
TELEGRAM_API_URL = f'https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}'
YS_API_KEY = os.environ.get('YS_API_KEY')
OW_API_KEY = os.environ.get('OW_API_KEY')
DD_API_KEY = os.environ.get('DD_API_KEY')
DD_SEC_KEY = os.environ.get('DD_SEC_KEY')


def send_message(text, message):
    message_id = message['message_id']
    chat_id = message['chat']['id']
    reply_message = {'chat_id': chat_id,
                     'text': text,
                     'reply_to_message_id': message_id}
    requests.post(url=f'{TELEGRAM_API_URL}/sendMessage', json=reply_message)


def handler(event, context):
    if TELEGRAM_BOT_TOKEN is None:
        return FUNC_RESPONSE
    if OW_API_KEY is None:
        return FUNC_RESPONSE
    update = json.loads(event['body'])
    if 'message' not in update:
        return FUNC_RESPONSE
    message_in = update['message']
    if 'location' in message_in:
        echo_text = get_weather_info(message_in['location']["latitude"], message_in['location']["longitude"])
        send_message(echo_text, message_in)
    elif 'text' in message_in:
        if DD_API_KEY is None:
            return FUNC_RESPONSE
        if DD_SEC_KEY is None:
            return FUNC_RESPONSE
        address = message_in["text"].encode('utf-8').decode('utf-8')
        lat, lon = get_coords_from_address(address)
        if lat and lon:
            echo_text = get_weather_info(lat, lon)
            send_message(echo_text, message_in)
        else:
            send_message(f'Недостаточно информации для адреса {address}.', message_in)
    elif 'voice' in message_in:
        # ищем путь аудио файла
        r_file = requests.get(url=f'{TELEGRAM_API_URL}/getFile', params={'file_id': message_in['voice']['file_id']})
        if r_file.ok:
            file_path = r_file.json()['result']['file_path']
        # скачиваем файл из телеграмма
        r_file_download = requests.get(url=f'https://api.telegram.org/file/bot{TELEGRAM_BOT_TOKEN}/{file_path}')
        if r_file_download.ok:
            audio_file = r_file_download.content
        # отправляем запрос YC SpeechKit
            r_stt = requests.post(url='https://stt.api.cloud.yandex.net/speech/v1/stt:recognize',
                                  headers={"Authorization": f"Api-Key {YS_API_KEY}"},
                                  data=audio_file)
            if r_stt.ok:
                address = r_stt.json()['result']
                lat, lon = get_coords_from_address(address)
                if lat and lon:
                    echo_text = get_weather_info(lat, lon)
                    send_message(echo_text, message_in)
                else:
                    send_message(f'Недостаточно информации для адреса {address}.', message_in)
    else:
        send_message('Могу обработать только текстовое сообщение, голосовое сообщение и сообщение с координатами.',
                     message_in)
    return FUNC_RESPONSE


def get_coords_from_address(address):
    r_address = requests.post(url="https://cleaner.dadata.ru/api/v1/clean/address",
                              headers={"Authorization": f"Token {DD_API_KEY}", "X-Secret": DD_SEC_KEY},
                              json=[address])
    if r_address.ok:
        result = r_address.json()[0]
        if result['qc'] == 0:
            return result['geo_lat'], result['geo_lon']
    return None, None


def get_weather_info(lat, lon):
    r = requests.get(url="https://api.openweathermap.org/data/2.5/weather",
                     params={'lat': lat, "lon": lon, 'appid': OW_API_KEY, 'units': 'metric', "lang": 'ru'})
    info_weather = r.json()
    echo_text = f"Сейчас {info_weather['main']['temp']} градусов/градуса."
    return echo_text
