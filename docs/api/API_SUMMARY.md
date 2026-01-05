# Ujin API Documentation

Полное описание API Ujin Smart Home, полученное путем анализа iOS-приложения.

## Base URL

```
https://api-product.mysmartflat.ru
```

## Аутентификация

### 1. Отправка кода подтверждения

```http
POST /api/v1/auth/code/email/send/
Content-Type: application/json

{
  "email": "user@example.com",
  "app": "ujin",
  "platform": "ios"
}
```

**Ответ:**
```json
{
  "command": "email->send",
  "error": 0,
  "message": "",
  "data": {
    "success": true,
    "time": 299
  }
}
```

### 2. Проверка кода и получение токена

```http
POST /api/v1/auth/code/email/auth/
Content-Type: application/json

{
  "email": "user@example.com",
  "code": "6609",
  "app": "ujin",
  "platform": "ios"
}
```

**Ответ:**
```json
{
  "command": "email->auth",
  "error": 0,
  "message": "",
  "data": {
    "token": "ust-3574810-78fde9f954f68e661cbfc140c8a7515d"
  }
}
```

### 3. Получение профиля пользователя

```http
GET /api/v1/auth/user/?token=TOKEN&app=ujin&platform=ios
```

**Ответ:**
```json
{
  "command": "auth->user",
  "error": 0,
  "data": {
    "user": {
      "id": "3574810",
      "name": "Иван",
      "surname": "",
      "email": "user@example.com",
      "phone": "79260096939"
    }
  },
  "token": "ust-3574810-..."
}
```

## Устройства

### Получение списка всех устройств

```http
GET /api/devices/main/?token=TOKEN&app=ujin&platform=ios&co2=1&lang=ru-RU&area_guid=GUID
```

**Ответ** (31.6 KB):
```json
{
  "command": "devices->main",
  "error": 0,
  "data": {
    "devices": [
      {
        "type": "total_list",
        "data": [
          {
            "id": "5360142",
            "signal": "rele1",
            "device_name": "Коммутатор на дин-рейку Ujin Connect-din 5360142",
            "name": "Освещение",
            "channels": 2,
            "icon": "https://cndslctl.mysmartflat.ru/img/devices/new/lighting.png",
            "svg": "light",
            "model": "dinrelay_m4",
            "model_title": "Коммутатор на дин-рейку Ujin Connect-din",
            "category_name": "Управление",
            "room": {
              "title": "Прихожая",
              "id": 101806
            },
            "status": "ok",
            "status_title": "Онлайн",
            "controls": [
              {
                "type": "switch",
                "value": 1,
                "readonly": 0
              }
            ],
            "management": {
              "remote": {
                "ip": "203.0.113.1",
                "protocol": "sapfir"
              },
              "local": {
                "available": true,
                "protocol": "sapfir-unicast",
                "ip": "10.10.30.50",
                "token": "51f79f12",
                "port": 30300
              }
            }
          }
        ]
      }
    ]
  }
}
```

### Типы устройств

#### 1. Ujin Connect-din (dinrelay_m4)
- Коммутатор на DIN-рейку
- До 4 каналов (rele1, rele2, rele3, rele4)
- Управление: switch (on/off)

#### 2. Ujin Connect-dim (ujin-zdm-m2)
- Диммируемое освещение
- 2 канала
- Управление: switch + brightness

#### 3. Ujin Aqua (ujin-zld-m1)
- Контроллер протечки воды
- Управление краном
- Управление: switch (открыть/закрыть)

## Управление устройствами

### Отправка команды

```http
GET /api/apartment/send-signal/?serialnumber=636206328&signal=rele-w&state=1&token=TOKEN&app=ujin&platform=ios&area_guid=GUID&uniq_id=
```

**Параметры:**
- `serialnumber` - ID устройства
- `signal` - Сигнал (rele1, rele2, rele-w и т.д.)
- `state` - Состояние (0 = выкл, 1 = вкл)
- `token` - Токен аутентификации
- `area_guid` - GUID зоны (из запроса devices/main)
- `uniq_id` - Уникальный ID запроса (может быть пустым)

**Ответ:**
```json
{
  "command": "apartment->send-signal",
  "error": 0,
  "message": "",
  "data": {}
}
```

## WebSocket

### Получение WebSocket URL

```http
GET /api/devices/wss/?token=TOKEN&app=ujin&platform=ios&area_guid=GUID
```

**Ответ:**
```json
{
  "command": "devices->wss",
  "error": 0,
  "data": {
    "url": "wss://server.example.com:11019/"
  }
}
```

**WebSocket соединение:**
```
wss://server.example.com:11019/
Status: 101 Switching Protocols
```

## Дополнительные endpoints

### Инициализация приложения
```http
GET /api/v1/app/init/?app=ujin&platform=ios
```

### Доступные методы авторизации
```http
GET /api/v1/auth/available-methods/?app=ujin&platform=ios
```

### Комнаты
```http
GET /api/apartment/get-ro...?token=TOKEN
```

### Автоматизации
```http
GET /api/autoscripts/list...?token=TOKEN
```

### Новости/истории
```http
GET /api/v1/stories/list/?token=TOKEN
```

### Главный экран
```http
GET /api/v1/main-screen/f...?token=TOKEN
```

### Ключи доступа
```http
GET /api/acms/get-key/?type=universal&token=TOKEN
```

## Заголовки запросов

Все запросы должны содержать следующие заголовки:

```http
X-APP-TYPE: mobile
X-APP-PLATFORM: ios
X-APP-LANG: ru-RU
X-APP-VERSION: 2
X-APP-DETAILS: ujin_v2.29(20)
X-TIMEZONE: Europe/Moscow
Accept: application/json
Content-Type: application/json
```

## Коды ошибок

- `error: 0` - Успех
- `error: 1` - Ошибка (см. поле `message`)

Примеры ошибок:
```json
{
  "error": 1,
  "message": "Логин или пароль введены неверно",
  "error_code": "unknown"
}
```

## Примечания

1. Токен имеет формат: `ust-{user_id}-{hash}`
2. `area_guid` необходим для большинства запросов после аутентификации
3. Локальное управление доступно через `sapfir-unicast` протокол
4. WebSocket используется для real-time обновлений статуса устройств
