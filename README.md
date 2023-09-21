# `gst-filter-media` - Run gstreamer plugin over a media file

Tool for creating a media file by filtering it through a gstreamer plugin.

`gst-filter-media` tries to produce an output file which is identical format as
the given input file.

The tool uses;
 * `GstPbutils.Discoverer` to discover the media format and create a `GstPbutils.EncodingProfile`.
 * `decodebin` to decode the input media file.
 * `encodebin2` to encode the output media file.

```
gst-filter-media.py \
    --plugin timeoverlay \
    input-media.mp4

gst-filter-media.py \
    --output output-file.mp4 \
    --plugin 'timeoverlay draw-outline,color=#ff0000' \
    input-media.mp4
```
