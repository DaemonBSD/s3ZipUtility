import boto3
import json
import zipfile
import os
import unicodedata
from io import BytesIO
from datetime import datetime


def generate_unique_zip_name(cnpj_ou_nome):
    # Formata o nome do arquivo zip usando o CNPJ ou nome e o timestamp
    timestamp = datetime.now().strftime("%Y%m%d%H%M%S")
    zip_file_key = f"{cnpj_ou_nome}-{timestamp}.zip"
    return zip_file_key


def zip_s3_files(bucket_source, folder_name, bucket_destination, cnpj_ou_nome):
    s3 = boto3.client('s3')
    zip_buffer = BytesIO()

    # Gerar o nome do arquivo zip
    zip_file_key = generate_unique_zip_name(cnpj_ou_nome)

    # Compacta os arquivos da pasta origem
    with zipfile.ZipFile(zip_buffer, 'w') as zip_file:
        response = s3.list_objects_v2(Bucket=bucket_source, Prefix=folder_name)
        for obj in response.get('Contents', []):
            file_key = obj['Key']
            if file_key.endswith('/'):
                continue

            # Baixar o arquivo do S3
            file_obj = s3.get_object(Bucket=bucket_source, Key=file_key)
            # Adiciona o arquivo ao zip, preservando sua estrutura
            zip_file.writestr(file_key[len(folder_name):].lstrip(
                '/'), file_obj['Body'].read())

    # Posiciona o ponteiro do buffer no início
    zip_buffer.seek(0)

    # Salva o arquivo zip no bucket de destino
    s3.put_object(Bucket=bucket_destination, Key=zip_file_key,
                  Body=zip_buffer.getvalue())

    # Gerar o link de download temporário para o arquivo zip
    expiration_time = 3600  # Expira em 1 hora (3600 segundos)
    download_link = s3.generate_presigned_url(
        'get_object',
        Params={'Bucket': bucket_destination, 'Key': zip_file_key},
        ExpiresIn=expiration_time
    )

    return download_link


def lambda_handler(event, context):
    # Extrair os dados da requisição
    bucket_source = event['bucket_origem']
    folder_name = event['pasta_origem'].lstrip(
        '/')  # Remove a barra inicial, se houver
    bucket_destination = event['bucket_destino']
    cnpj_ou_nome = event['cnpj_ou_nome']

    # Chama a função que realiza a compactação e gera o link de download
    download_link = zip_s3_files(
        bucket_source, folder_name, bucket_destination, cnpj_ou_nome)

    # Retorna o link de download
    return {
        'statusCode': 200,
        'body': {
            'message': 'Arquivos compactados com sucesso!',
            'download_link': download_link
        }
    }
