Tif Clipper
===========

_tl;dr_:

```bash
$ docker pull jisantuc/tifclipper
$ docker run --rm -v $HOME/.aws:/root/.aws src/transform_tif.py bucket key
```

This repository contains a Dockerfile and a basic script for trimming aerial
imagery tifs to the "good parts". The script solves an extremely specific problem
that is nonetheless worth having a version-controlled strategy for:

- you have a big tif
- mostly it's fine
- QGIS says it's fine
- gdalinfo and rasterio are mostly happy
- you think things are ok and there's no reason to be sad
- but pretty far into the tif, there's a bad row
- and there's actually a reason to be sad
- but you're fine throwing away everything below that bad row

The script runs a no-op translation to discover if there are any errors in the tif
as it stands, then:

- if there are no errors in the tif, it copies it as-is to `bucket/trimmed/fname.tif`
- if there are errors and they're more than 95% of the way into the tif, it compresses
  the tif and drops the rows below the bad row it found, writing to
  `bucket/trimmed/fnamed_trimmed_and_compressed.tif`

Assumptions
-----------

- you have imagery with smooth differences in values between pixels (necessary for
  `-co PREDICTOR=2` to be useful)
- you have enough imagery that throwing away up to 5% of it doesn't materially affect
  whether you want to keep it
- your imagery lives in s3

License
-------

Do truly whatever it is that you wish with it -- it just cuts rows off tifs
