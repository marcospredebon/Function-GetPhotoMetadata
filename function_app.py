import azure.functions as func
import requests
from PIL import Image, ExifTags
from io import BytesIO
import json
import logging

# Logger padrão do módulo
logger = logging.getLogger(__name__)

# Instancia o app de funcoes
app = func.FunctionApp()

# Funcoes auxiliares para extrair EXIF
def get_exif_data(image: Image.Image) -> dict:
    """Extrai os dados EXIF de uma imagem PIL."""
    exif_data = {}
    try:
        info = image._getexif()
    except Exception:
        info = None
    if info:
        for tag, value in info.items():
            decoded = ExifTags.TAGS.get(tag, tag)
            if decoded == "GPSInfo":
                gps_data = {}
                for t in value:
                    sub_decoded = ExifTags.GPSTAGS.get(t, t)
                    gps_data[sub_decoded] = value[t]
                exif_data["GPSInfo"] = gps_data
            else:
                exif_data[decoded] = value
    return exif_data

def convert_to_degrees(value) -> float:
    """Converte o formato de coordenadas GPS (graus, minutos, segundos) para float."""
    try:
        d, m, s = value
        return d + (m / 60.0) + (s / 3600.0)
    except Exception:
        return None

# Define a funcao HTTP trigger
@app.function_name(name="GetPhotoMetadata")
@app.route(route="GetPhotoMetadata", methods=["GET", "POST"], auth_level=func.AuthLevel.FUNCTION)
def get_photo_metadata(req: func.HttpRequest) -> func.HttpResponse:
    """Recebe um parametro fileUrl, baixa a imagem, extrai EXIF e retorna JSON."""
    try:
        debug_info = {}
        debug_mode = str(req.params.get('debug', '')).lower() == 'true'
        if debug_mode:
            logger.info('Debug mode enabled for request')
        logger.info('GetPhotoMetadata called')
        # Obter parametro fileUrl de query ou do body
        file_url = req.params.get('fileUrl')
        if not file_url:
            try:
                req_body = req.get_json()
            except ValueError:
                req_body = {}
            file_url = req_body.get('fileUrl')
        if not file_url:
            logger.warning('Missing fileUrl parameter')
            return func.HttpResponse('Missing fileUrl parameter', status_code=400)

        logger.info('Fetching fileUrl: %s', file_url)

        # Baixar a imagem com timeout e validações
        try:
            response = requests.get(file_url, timeout=10)
            response.raise_for_status()
        except requests.exceptions.RequestException as ex:
            logger.error('Error fetching fileUrl: %s', ex)
            logger.debug('fileUrl attempted: %s', file_url)
            debug_info['fetch_error'] = str(ex)
            if debug_mode:
                return func.HttpResponse(json.dumps({'error': str(ex), 'debug': debug_info}), mimetype='application/json', status_code=502)
            return func.HttpResponse(f'Error fetching fileUrl: {ex}', status_code=502)

        # Verificar Content-Type antes de tentar abrir como imagem
        content_type = response.headers.get('Content-Type', '').split(';')[0].lower()
        content_length = response.headers.get('Content-Length')
        logger.info('Downloaded content-type=%s length=%s', content_type, content_length)
        debug_info['content_type'] = content_type
        debug_info['content_length'] = content_length
        if not content_type.startswith('image/'):
            logger.warning('URL did not return an image. Content-Type: %s', content_type)
            if debug_mode:
                return func.HttpResponse(json.dumps({'error': 'URL did not return an image', 'content_type': content_type, 'debug': debug_info}), mimetype='application/json', status_code=400)
            return func.HttpResponse(f'URL did not return an image. Content-Type: {content_type}', status_code=400)

        try:
            image = Image.open(BytesIO(response.content))
            logger.info('Image opened successfully: format=%s size=%s', image.format, image.size)
            debug_info['image_format'] = image.format
            debug_info['image_size'] = image.size
        except Exception as ex:
            logger.exception('Downloaded content is not a valid image')
            debug_info['open_error'] = str(ex)
            if debug_mode:
                return func.HttpResponse(json.dumps({'error': 'Downloaded content is not a valid image', 'open_error': str(ex), 'debug': debug_info}), mimetype='application/json', status_code=400)
            return func.HttpResponse(f'Downloaded content is not a valid image: {ex}', status_code=400)

        # Extração EXIF
        exif_data = get_exif_data(image)
        date_time = exif_data.get('DateTime', None)
        gps_info = exif_data.get('GPSInfo', {})
        lat = lon = None
        if gps_info:
            if 'GPSLatitude' in gps_info and 'GPSLongitude' in gps_info:
                lat = convert_to_degrees(gps_info.get('GPSLatitude'))
                lon = convert_to_degrees(gps_info.get('GPSLongitude'))
                if gps_info.get('GPSLatitudeRef') == 'S':
                    lat = -lat if lat is not None else None
                if gps_info.get('GPSLongitudeRef') == 'W':
                    lon = -lon if lon is not None else None

        result = {
            'date_time': date_time,
            'latitude': lat,
            'longitude': lon
        }
        if debug_mode:
            result['debug'] = debug_info
        return func.HttpResponse(json.dumps(result), mimetype='application/json', status_code=200)
    except Exception as e:
        logger.exception('Unhandled exception in GetPhotoMetadata')
        return func.HttpResponse(f'Error: {str(e)}', status_code=500)
