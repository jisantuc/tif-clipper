import argparse
import os
import re
import subprocess

import boto3
import rasterio


def row_from_output(err_output):
    print('Trying to find the correct row from:\n%s' % err_output)
    pattern = re.compile(r'(?:X offset \d+, Y offset )(?P<line>\d+)')
    match = pattern.search(err_output)
    if match:
        return int(match.group('line'))


def get_tif_cols_and_rows(path_to_tif):
    with rasterio.open(path_to_tif) as src:
        return (src.width, src.height)


def attempt_translate(path_to_tif):
    """Try to translate a tif with no transformation

    The purpose of trying to translate it is to traverse the entire tif
    and ensure that data are good in every row and column. In the event
    of failure, return the y offset of the failing row
    """

    print('Attempting to no-op translate %s' % path_to_tif)
    prefix, fname = os.path.split(path_to_tif)
    fbase = fname[:fname.index('.tif')]
    new_fname = os.path.join(prefix, fbase + '_forthelulz.tif')

    try:
        subprocess.check_output(
            ' '.join(['gdal_translate', path_to_tif, new_fname]),
            shell=True,
            stderr=subprocess.STDOUT)
        return None
    except subprocess.CalledProcessError as e:
        print('Translation failed - this is good news')
        out = {'error': e, 'failing_row': row_from_output(e.output)}
        print(out)
        return out


def copy_tif(bucket, old_key, new_key):
    print('Copying tif, since nothing was wrong')
    client = boto3.client('s3')
    client.copy_object(
        CopySource='s3://{}'.format(old_key), Bucket=bucket, Key=new_key)


def trim_and_compress(path_to_tif, until, width):
    """Compress a tif, optionally trimming after a certain row

    Args:
        path_to_tif (str): filesystem location of a geotiff
        until (int): row number to stop the srcwin at
        width (int): number of columns in the tif
    """

    print('Trimming and compressing %s' % path_to_tif)
    prefix, fname = os.path.split(path_to_tif)
    fbase = fname[:fname.index('.tif')]
    new_fname = os.path.join(prefix, fbase + '_compressed_and_trimmed.tif')
    print('Attempting to create %s' % new_fname)
    subprocess.check_output([
        'gdal_translate', '-co', 'COMPRESS=DEFLATE', '-co', 'PREDICTOR=2',
        '-srcwin', '0', '0',
        str(width),
        str(until - 1), path_to_tif, new_fname
    ])
    print('Trim and compress was successful')
    return new_fname


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('s3bucket')
    parser.add_argument('s3key')
    args = parser.parse_args()

    client = boto3.client('s3')
    resp = client.get_object(Bucket=args.s3bucket, Key=args.s3key)
    _, fname = os.path.split(args.s3key)
    local_path = '/tmp/{}'.format(fname)
    print('Writing s3 tif to local file: %s' % local_path)
    with open(local_path, 'w') as outf:
        outf.write(resp['Body'].read())

    width, height = get_tif_cols_and_rows(local_path)
    translate_result = attempt_translate(local_path)
    if translate_result is not None:
        err_row = translate_result['failing_row']
        if err_row < height * 0.95:
            raise Exception(
                'This tif was too messed up -- read error was only '
                '%.2f percent of the way through the file :(') % (
                    err_row / float(height) * 100)
        new_tif = trim_and_compress(local_path,
                                    translate_result['failing_row'], width)
        print('Uploading trimmed and compressed tif to s3: %s' % new_tif)
        with open(new_tif, 'r') as tos3:
            client.put_object(
                Bucket=args.s3bucket, Key='trimmed' + os.path.split(new_tif)[1],
                Body=tos3)
    else:
        copy_tif(
            Bucket=args.s3bucket,
            Key='trimmed/' + fname,
            CopySource={
                'Bucket': args.s3bucket,
                'Key': args.s3key
            })


if __name__ == '__main__':
    main()
