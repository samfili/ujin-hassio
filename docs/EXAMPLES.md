# Примеры использования Ujin Smart Home

## Автоматизации

### 1. Выключить всё при уходе

```yaml
automation:
  - alias: "Ujin: Выключить всё при уходе"
    description: "Выключить все устройства Ujin когда никого нет дома"
    trigger:
      - platform: state
        entity_id: zone.home
        to: "0"
        for:
          minutes: 5
    action:
      - service: switch.turn_off
        target:
          entity_id:
            - switch.osveshchenie
            - switch.rozetki_po_vsey_kvartire
            - switch.osveshchenie_kanal_1
            - switch.osveshchenie_kanal_2
```

### 2. Включить освещение при движении

```yaml
automation:
  - alias: "Ujin: Свет в прихожей по движению"
    description: "Включить свет в прихожей при обнаружении движения"
    trigger:
      - platform: state
        entity_id: binary_sensor.motion_hallway
        to: "on"
    condition:
      - condition: numeric_state
        entity_id: sensor.hallway_illuminance
        below: 100
    action:
      - service: switch.turn_on
        target:
          entity_id: switch.osveshchenie
      - delay:
          minutes: 5
      - service: switch.turn_off
        target:
          entity_id: switch.osveshchenie
```

### 3. Защита от протечки

```yaml
automation:
  - alias: "Ujin: Экстренное закрытие крана"
    description: "Закрыть кран при обнаружении протечки"
    trigger:
      - platform: state
        entity_id: binary_sensor.water_leak_bathroom
        to: "on"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.kontroller_protechki_ujin_aqua
      - service: notify.mobile_app
        data:
          title: "⚠️ ПРОТЕЧКА!"
          message: "Обнаружена протечка в ванной. Кран автоматически закрыт."
          data:
            priority: high
            ttl: 0
```

### 4. Утренний сценарий

```yaml
automation:
  - alias: "Ujin: Утренний сценарий"
    description: "Включить свет и розетки утром в будни"
    trigger:
      - platform: time
        at: "07:00:00"
    condition:
      - condition: time
        weekday:
          - mon
          - tue
          - wed
          - thu
          - fri
    action:
      - service: switch.turn_on
        target:
          entity_id:
            - switch.osveshchenie_kanal_1
            - switch.rozetki_po_vsey_kvartire
```

### 5. Контроль потребления энергии

```yaml
automation:
  - alias: "Ujin: Выключить розетки ночью"
    description: "Автоматически отключать розетки ночью для экономии"
    trigger:
      - platform: time
        at: "23:30:00"
    action:
      - service: switch.turn_off
        target:
          entity_id: switch.rozetki_po_vsey_kvartire
      - service: notify.persistent_notification
        data:
          message: "Розетки выключены для экономии энергии"
```

## Скрипты

### Сценарий "Ушли из дома"

```yaml
script:
  ujin_leaving_home:
    alias: "Ujin: Уходим из дома"
    sequence:
      - service: switch.turn_off
        target:
          entity_id:
            - switch.osveshchenie
            - switch.osveshchenie_kanal_1
            - switch.osveshchenie_kanal_2
      - service: switch.turn_off
        target:
          entity_id: switch.rozetki_po_vsey_kvartire
      - service: switch.turn_off
        target:
          entity_id: switch.kontroller_protechki_ujin_aqua
      - service: notify.mobile_app
        data:
          message: "Все устройства Ujin выключены"
```

### Сценарий "Пришли домой"

```yaml
script:
  ujin_arriving_home:
    alias: "Ujin: Возвращаемся домой"
    sequence:
      - service: switch.turn_on
        target:
          entity_id: switch.kontroller_protechki_ujin_aqua
      - service: switch.turn_on
        target:
          entity_id: switch.osveshchenie
      - service: switch.turn_on
        target:
          entity_id: switch.rozetki_po_vsey_kvartire
```

## Карточки Lovelace

### Карточка управления освещением

```yaml
type: entities
title: Ujin - Освещение
entities:
  - entity: switch.osveshchenie
    name: Прихожая
  - entity: switch.osveshchenie_kanal_1
    name: Комната - Канал 1
  - entity: switch.osveshchenie_kanal_2
    name: Комната - Канал 2
show_header_toggle: true
```

### Карточка контроля воды

```yaml
type: glance
title: Ujin - Контроль воды
entities:
  - entity: switch.kontroller_protechki_ujin_aqua
    name: Кран
show_name: true
show_icon: true
show_state: true
```

### Карточка всех устройств

```yaml
type: custom:auto-entities
card:
  type: entities
  title: Все устройства Ujin
  show_header_toggle: true
filter:
  include:
    - integration: ujin
  exclude: []
sort:
  method: name
```

## Шаблоны

### Датчик общего статуса

```yaml
template:
  - sensor:
      - name: "Ujin Статус"
        state: >
          {% set lights = [
            states('switch.osveshchenie'),
            states('switch.osveshchenie_kanal_1'),
            states('switch.osveshchenie_kanal_2')
          ] %}
          {% set on_count = lights | select('eq', 'on') | list | count %}
          {% if on_count == 0 %}
            Всё выключено
          {% elif on_count == lights | count %}
            Всё включено
          {% else %}
            {{ on_count }} из {{ lights | count }} включено
          {% endif %}
```

### Бинарный датчик "Дома кто-то есть"

```yaml
binary_sensor:
  - platform: template
    sensors:
      ujin_activity:
        friendly_name: "Активность Ujin"
        value_template: >
          {{ is_state('switch.osveshchenie', 'on') or
             is_state('switch.rozetki_po_vsey_kvartire', 'on') }}
        icon_template: >
          {% if is_state('binary_sensor.ujin_activity', 'on') %}
            mdi:home-account
          {% else %}
            mdi:home-outline
          {% endif %}
```

## Уведомления

### Уведомление о статусе

```yaml
automation:
  - alias: "Ujin: Уведомление о статусе крана"
    description: "Отправить уведомление при изменении статуса крана"
    trigger:
      - platform: state
        entity_id: switch.kontroller_protechki_ujin_aqua
    action:
      - service: notify.mobile_app
        data:
          title: "Ujin Aqua"
          message: >
            Кран {{ 'открыт' if trigger.to_state.state == 'on' else 'закрыт' }}
```

## Дополнительные возможности

### Группы устройств

```yaml
switch:
  - platform: group
    name: "Всё освещение Ujin"
    entities:
      - switch.osveshchenie
      - switch.osveshchenie_kanal_1
      - switch.osveshchenie_kanal_2
```

### Использование в сценах

```yaml
scene:
  - name: "Вечер"
    entities:
      switch.osveshchenie: on
      switch.osveshchenie_kanal_1: on
      switch.osveshchenie_kanal_2: off
      switch.rozetki_po_vsey_kvartire: on

  - name: "Сон"
    entities:
      switch.osveshchenie: off
      switch.osveshchenie_kanal_1: off
      switch.osveshchenie_kanal_2: off
      switch.rozetki_po_vsey_kvartire: off
```
