from json.decoder import JSONDecodeError
from django.conf import settings
from django.db.models import (Q, )

import locale
locale.setlocale(locale.LC_ALL, 'ru_RU')

import requests as req
import json
import re

from loguru import logger
logger.add(
    str(settings.BASE_DIR) + "/logs/parser.log",
    format="{time} - [{level}] -> {message}",
    rotation="1 days",
    compression="zip"
)

from rest_framework.generics import (ListAPIView, )
from rest_framework.response import Response
from rest_framework.status import (HTTP_403_FORBIDDEN, )

from .models import (UpdatedService, ServiceList, ModxSystemSettings, )
from .serializers import (ServiceListSerializer, )


class ResetCacheListAPIView():

    def __init__(self):
        self.limit = 1000
        self.offset = 0
        self.to_json = []

    def format_service(self, line):
        string = re.sub(r"\([^\(\)]*\)", "", line)
        return string.split(',')

    def get_url(self, ):
        string = f"""
            https://klientiks.ru/clientix/Restapi/list/
                a/{settings.ACCOUNT_ID}/
                u/{settings.USER_ID}/
                t/{settings.ACCESS_TOKEN}/
                m/Services/?limit={self.limit}&offset={self.offset}
        """
        return re.sub(r"\s+", "", string)

    def reset(self, ):
        while True:
            response = req.get(self.get_url())
            result = response.json()

            if int(result['count']) == 0:
                break

            self.offset += self.limit
            self.to_json = self.to_json + result['items']

        service_groups = []

        for service in self.to_json:
            for string in self.format_service( str(service['service_groups']) ):
                string = string.strip()
                if string != 'None' and len(string) != 0:
                    if len(service_groups) == 0:
                        service_groups.append({
                            "name": string,
                            "data": [service]
                        })
                    else:
                        if string in list(map(lambda el: el['name'], service_groups)):
                            for item in service_groups:
                                if item['name'] == string:
                                    item['data'].append(service)
                        else:
                            service_groups.append({
                                "name": string,
                                "data": [service]
                            })

        with open(str(settings.BASE_DIR) + '/json/services.json', 'w') as f:
            f.write(json.dumps(service_groups))

        queryset = UpdatedService.objects.create(added=len(self.to_json))

        return {
            "added": len(self.to_json),
            "date_added": queryset.date_added
        }


class UpdateServiceListAPIView(ListAPIView):
    queryset = ServiceList.objects.filter()
    serializer_class = ServiceListSerializer


    def list(self, request, *args, **kwargs):
        request_token = request.headers.get('Authorization', False)

        logger.info('[ModX] Проверка api ключа')
        if not request_token:
            return Response({}, status=HTTP_403_FORBIDDEN)
        try:
            modx_token = ModxSystemSettings.objects.get(key="api_key").value
        except ModxSystemSettings.DoesNotExist:
            return Response({}, status=HTTP_403_FORBIDDEN)
        
        if request_token != modx_token:
            return Response({}, status=HTTP_403_FORBIDDEN)

        logger.info('[ModX] Авторизация прошла успешно')

        logger.info('[Klientiks] Обновление текущего кеша')
        cache = ResetCacheListAPIView().reset()
        
        with open(str(settings.BASE_DIR) + '/json/services.json', 'r') as file:
            klientiks_data = json.load(file)


        logger.info('[Klientiks] Начинаем переберать кешированные данные из файла services.json')
        for klientiks_category in klientiks_data:
            logger.info('[ModX] Ищем все возможные совпадения по названию категории: ' + klientiks_category['name'])
            modx_queryset = ServiceList.objects.filter( Q(value__icontains=klientiks_category['name']) | Q(value__icontains=json.dumps(klientiks_category['name'])) )
            
            if len(modx_queryset) == 0:
                logger.error('[ModX] Совпадений по названию "' + klientiks_category['name'] + '" не найдено')
                continue

            logger.info('[ModX] Совпадений по названию "' + klientiks_category['name'] + '" найдено -> Выполняем форматирование данных')
            modx_serializer = self.get_serializer(modx_queryset, many=True)
            
            for modx_content_list in modx_serializer.data:
                logger.info('[ModX] Получен список возможных категорий по названию "' + klientiks_category['name'] + '" получаем данные о них них')
                try:
                    modx_content_list_parse = json.loads(modx_content_list['value'])
                except JSONDecodeError:
                    logger.error('[ModX] Cписок возможных категорий пуст по названию "' + klientiks_category['name'] + '"')
                    continue


                logger.info('[ModX] Перебираем полученые данные')
                for modx_content in modx_content_list_parse:
                    logger.info('[ModX] Ищем раздел "' + klientiks_category['name'] + '"')
                    if str(modx_content['name']).strip() == klientiks_category['name'].strip():
                        logger.info('[ModX] Получаем список услуг')
                        modx_service_list = []
                        klientiks_service_list = klientiks_category['data'].copy()

                        modx_service_last_id = 0

                        modx_active_ro = json.dumps({
                            "MIGX_id": "1",
                            "name": "Активный",
                            "use_as_fallback": "1",
                            "value": "use_as_fallback",
                            "clickaction": "",
                            "handler": "",
                            "image": "assets/components/migx/style/images/tick.png",
                            "idx": 0,
                            "_renderer": "this.renderSwitchStatusOptions",
                            "selectorconfig": ""
                        })

                        logger.info('[Klientiks] Перебираем список услуг')
                        for klientiks_service in klientiks_service_list:
                            logger.info('[ModX] Добавляем услугу "' + klientiks_service['name'].strip() + '"')
                            modx_service_last_id += 1
                            modx_service_list.append({
                                "MIGX_id": str(modx_service_last_id),
                                "code": re.sub(r"\s+", "", klientiks_service['barcode']),
                                "desc": klientiks_service['name'].strip(),
                                "price": locale.format_string("%d", int(klientiks_service['price']), grouping=True),
                                "active": "1",
                                "active_ro": modx_active_ro,
                            })
                                

                        logger.info('[ModX] Формируем данные перед сохранением в БД')
                        modx_content['description'] = json.dumps(modx_service_list)
                    else:
                        continue
                logger.info('[ModX] Сохраняем результат в базу данных')
                ServiceList.objects.filter(
                    id=modx_content_list['id']
                ).update(
                    value=json.dumps(modx_content_list_parse)
                )
        
        return Response({
            "message": "Данные обновлены",
            "cache": cache
        })
        
