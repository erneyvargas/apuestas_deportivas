
class EstadisticaEquipo():
    name = 'estadistica_equipo'
    # Definicion de las configuraciones, 1=> para no ser baneado, 2=> salida de la data en formato legible
    custom_settings = {
        'USER_AGENT': 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Ubuntu Chromium/71.0.3578.80 Chrome/71.0.3578.80 Safari/537.36',
        'FEED_EXPORT_ENCODING': 'utf-8'
    }

    download_delay = 2

    # URL semilla
    start_urls = ['https://fbref.com/es/equipos/cff3d9bb/Estadisticas-de-Chelsea']

