# telegram-dapnet-bot

Bot de Telegram que lee los calendarios CalDAV de cada usuario (cualquier instancia Nextcloud) y envía avisos a [DAPNET](https://hampager.de/) con la cuenta del operador.

Un administrador debe aprobar a cada usuario. El callsign tiene que existir en DAPNET y tener un subscriber (RIC).

## Qué hace

- `/register`: callsign DAPNET, núcleo EA/DL, URL/usuario/app password de Nextcloud
- Validación contra `GET /users/{callsign}` y `GET /callSigns/{callsign}`
- Confirmación de RIC vía RadioID (IDs DMR recortados al rango POCSAG, como en PagerBot)
- Aprobación admin (`/pending`, `/approve`, `/reject`, o botones)
- `/calendars`: activar o desactivar calendarios
- `/reminders`: anticipación (15m … 1 semana) y 1–3 avisos equiespaciados
- `/txgroup`: grupos de transmisores (spreads), varios a la vez como en PagerBot
- `/server`: núcleo España (`dapnet.es`) o Alemania (`hampager.de`)
- `/timezone`, `/status`, `/test`
- Sincronización periódica CalDAV y envío `POST /calls` (máx. 80 caracteres)

## Requisitos

- Python 3.12+
- Token de un bot creado con [@BotFather](https://t.me/BotFather)
- Cuenta DAPNET del operador (callsign + contraseña de hampager.de)
- Tu Telegram user id (por ejemplo con [@userinfobot](https://t.me/userinfobot))

Cada usuario necesita:

- Usuario DAPNET con subscriber/RIC
- App password de Nextcloud (Ajustes → Seguridad). No uses la contraseña principal si hay 2FA.

## Configuración

```bash
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

Genera una clave Fernet para cifrar los app passwords:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Rellena `.env`:

- `TELEGRAM_BOT_TOKEN`
- `ADMIN_TELEGRAM_IDS` (ids separados por coma)
- `DAPNET_CALLSIGN` / `DAPNET_PASSWORD`
- `ENCRYPTION_KEY`
- `DAPNET_DEFAULT_TX_GROUP` (por defecto `all`)

## Ejecución local

```bash
python -m telegram_dapnet_bot
```

## Docker

```bash
cp .env.example .env
# edita .env
docker compose up --build -d
```

Los datos (SQLite) quedan en `./data`.

## Comandos

Usuarios:

- `/start`, `/register`, `/status`, `/calendars`, `/reminders`, `/txgroup`, `/server`, `/timezone Europe/Madrid`, `/test`, `/cancel`

Administradores:

- `/pending`, `/users`, `/approve <telegram_id>`, `/reject <telegram_id>`

## Recordatorios

Con anticipación 60 min y 3 repeticiones se envían páginas en T-60, T-40 y T-20.

Los eventos de día completo se tratan como si empezaran a las 09:00 en la zona del usuario.

## DAPNET

El bot habla con la API 1.1 de producción (`https://hampager.de/api`), no con la API 2.0.

La API oculta el array `pagers` a usuarios normales. Si la cuenta operadora no es admin, la existencia del `callSign` se considera prueba de subscriber/RIC.

El texto se recorta a 80 caracteres: `CALLSIGN: resumen dd/mm HH:MM`.
Antes de enviar se quitan tildes y símbolos que los pagers no pintan (misma sanitización que PagerBot).

Cada usuario elige núcleo con `/server`. Las URLs se configuran en `DAPNET_API_URL` (Alemania) y `DAPNET_API_URL_ES` (España).

## Desarrollo

```bash
pip install -e ".[dev]"
pytest
```

## Licencia

GPL-3.0-or-later
