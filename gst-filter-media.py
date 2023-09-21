#!/usr/bin/env python3

# flake8: noqa

import pathlib
import sys
import traceback

import gi
gi.require_version('Gst', '1.0')
gi.require_version('GstPbutils', '1.0')
from gi.repository import Gst, GstPbutils, GLib  # noqa


def on_message(bus: Gst.Bus, message: Gst.Message, loop: GLib.MainLoop):
    mtype = message.type
    """
        Gstreamer Message Types and how to parse
        https://lazka.github.io/pgi-docs/Gst-1.0/flags.html#Gst.MessageType
    """
    if mtype == Gst.MessageType.EOS:
        print("End of stream")
        loop.quit()
    elif mtype == Gst.MessageType.ERROR:
        err, debug = message.parse_error()
        print('Error:', err, debug)
        loop.quit()
    elif mtype == Gst.MessageType.WARNING:
        err, debug = message.parse_warning()
        print('Warning:', err, debug)
    elif mtype == Gst.MessageType.INFO:
        info, debug = message.parse_info()
        print('Info:', info, debug)
    else:
        print("unknown message:", message.type, message)

    return True


def on_discovered(*args, **kw):
    print('on_discovered:', args, kw)


def main():
    if len(sys.argv) < 2:
        print("usage %s <input file> [<output file>]" % sys.argv[0])
        sys.exit(1)

    infile = pathlib.Path(sys.argv[1])
    assert infile.exists(), f"{infile} does not exist!"
    if len(sys.argv) > 2:
        outfile = pathlib.Path(sys.argv[2])
    else:
        outfile = infile.parent / (infile.stem + '.out' + infile.suffix)

    assert not outfile.exists(), f"{outfile} exists - not over writing!"

    infile_uri = 'file://'+str(infile.resolve())
    # outfile_uri = 'file://'+str(outfile.resolve())

    Gst.init(None)

    # Discover the encoding profile about the infile
    # ----------------------------------------------------------
    discoverer = GstPbutils.Discoverer()
    discoverer.connect('discovered', on_discovered)
    info = discoverer.discover_uri(infile_uri)

    # video info
    print('\nvideo', '-'*70)
    for vinfo in info.get_video_streams():
        print(vinfo.get_caps().to_string().replace(', ', '\n\t'))
    print('-'*75, '\n', flush=True)

    # audio info
    print()
    print('\naudio', '-'*70)
    for ainfo in info.get_audio_streams():
        print(ainfo.get_caps().to_string().replace(', ', '\n\t'))
    print('-'*75, '\n', flush=True)

    profile = GstPbutils.EncodingProfile.from_discoverer(info)
    print('profile', profile)
    profile_caps = profile.get_input_caps()
    print('caps:', repr(profile_caps), repr(str(profile_caps)))
    # ----------------------------------------------------------

    #                          /-> videoconvert -> filter -> videoconvert -\
    #                         /                                             \
    # filesrc --> decodebin -+                                               +-> encodebin -> filesink
    #                         \                                             /
    #                          \-------------------------------------------/
    pipeline_str = f"""\
filesrc location={str(infile.resolve())}
! decodebin name=d

encodebin2 name=e
! filesink location={str(outfile.resolve())}

videoconvert name=vc_i ! timeoverlay ! videoconvert name=vc_o
"""
    print("\npipeline", "-"*50)
    print(pipeline_str)
    pipeline = Gst.parse_launch(pipeline_str)
    print('-'*75, '\n', flush=True)

    encodebin = pipeline.get_child_by_name('e')
    encodebin.set_property('profile', profile)

    decodebin = pipeline.get_child_by_name('d')

    vc_i = pipeline.get_child_by_name('vc_i')
    vc_o = pipeline.get_child_by_name('vc_o')

    def connect_pad(obj, dc_pad):
        name = dc_pad.get_name()
        dc_caps = dc_pad.get_current_caps()
        dc_caps_str = dc_caps.to_string()

        print("new decodebin pad", dc_pad, "with caps", dc_caps, dc_caps_str)
        eb_pad = encodebin.emit("request-pad", dc_caps)
        if not dc_caps_str.startswith('video/x-raw'):
            dc_pad.link(eb_pad)
            return

        vc_i_snk = vc_i.get_static_pad('sink')
        dc_pad.link(vc_i_snk)

        vc_o_src = vc_o.get_static_pad('src')
        vc_o_src.link(eb_pad)

    decodebin.connect("pad-added", connect_pad)

    bus = pipeline.get_bus()

    # allow bus to emit messages to main thread
    bus.add_signal_watch()

    # Init GObject loop to handle Gstreamer Bus Events
    loop = GLib.MainLoop()

    # Add handler to specific signal
    # https://lazka.github.io/pgi-docs/GObject-2.0/classes/Object.html#GObject.Object.connect
    bus.connect("message", on_message, loop)

    # Start pipeline
    pipeline.set_state(Gst.State.PLAYING)

    try:
        loop.run()
    except Exception:
        traceback.print_exc()
        loop.quit()

    # Stop Pipeline
    pipeline.set_state(Gst.State.NULL)

    return


if __name__ == "__main__":
    main()
