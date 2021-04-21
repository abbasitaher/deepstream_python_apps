import sys
sys.path.append('../')
import platform
import configparser
import math
import gi
gi.require_version('Gst', '1.0')
from gi.repository import GObject, Gst
from common.is_aarch_64 import is_aarch64
from common.bus_call import bus_call

import pyds
import numpy as np
import copy
import cv2
import time
import tkinter
from tkinter import ttk

import pyautogui
import PIL.Image, PIL.ImageTk
from PIL import ImageTk
from PIL import Image

PGIE_CLASS_ID_VEHICLE = 0
PGIE_CLASS_ID_BICYCLE = 1
PGIE_CLASS_ID_PERSON = 2
PGIE_CLASS_ID_ROADSIGN = 3
past_tracking_meta=[0]
widthScreen, heightScreen = pyautogui.size()
ScreenType = 1
WScale = widthScreen / 1920
HScale = heightScreen / 1080
window = tkinter.Tk()
window.geometry(str(widthScreen) + "x" + str(heightScreen))
canvas1 = tkinter.Canvas(window, width=round(1700 * WScale), height=round(1150 * WScale), bg=None, bd=0,
                         highlightthickness=0)
canvas1.pack()
pgie_classes_str = ["Vehicle", "TwoWheeler", "Person", "RoadSign"]

# image = '/home/proxeye/dev/proxeye/proxeye/resources/gui_images/Base.png'
# imgBase = ImageTk.PhotoImage(Image.open(image).resize((round(1010 * WScale), round(1010 * WScale))))
# canvas1.create_image(round(240 * WScale), round(35 * HScale), image=imgBase, anchor=tkinter.NW, tags="ImBaseLarge")
# window.update()
# image = '/home/proxeye/dev/proxeye/proxeye/resources/gui_images/BaseN.png'
# imgBase = ImageTk.PhotoImage(Image.open(image).resize((round(1010 * WScale), round(1010 * WScale))))
# canvas1.create_image(round(240 * WScale), round(35 * HScale), image=imgBase, anchor=tkinter.NW, tags="ImBaseLarge")
# window.update()

# time.sleep(100)

global image1copy, frameSync
frameSync = None
image = '/home/proxeye/dev/proxeye/proxeye/resources/gui_images/BaseN.png'
image1copy = cv2.imread(image)

def tiler_src_pad_buffer_probe(pad, info, u_data):
    global image1copy, frameSync
    frame_number = 0
    frameNumber = 0
    BufferNumber = 0
    num_rects = 0
    gst_buffer = info.get_buffer()
    if not gst_buffer:
        print("Unable to get GstBuffer ")
        return
    batch_meta = pyds.gst_buffer_get_nvds_batch_meta(hash(gst_buffer))
    l_frame = batch_meta.frame_meta_list
    while l_frame is not None:
        frameNumber = frameNumber + 1
        BufferNumber = BufferNumber + 1

        try:
            frame_meta = pyds.NvDsFrameMeta.cast(l_frame.data)
            # print(hash(gst_buffer))
        except StopIteration:
            break
        frame_number = frame_meta.frame_num
        l_obj = frame_meta.obj_meta_list
        n_frame = pyds.get_nvds_buf_surface(hash(gst_buffer), frame_meta.batch_id)
        frame_image = np.array(n_frame, copy=True, order='C')
        frameSync = copy.copy(frame_image[:, :, 0:3])
        image1 = np.uint8(frameSync)
        image1copy = cv2.cvtColor(image1, cv2.COLOR_RGB2BGR)

        # SyncImRect = np.where(RectDetect == 0, frameSync, RectDetect)
        # color_image = cv2.resize(image1copy, (round(480 * WScale), round(320 * HScale)))
        # photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(np.uint8(image1copy)).convert('RGB'))

        
        # cv2.waitKey()
        # if GeneralSetting.start_record is True:
        #     VideoRecorded.write(DetectResult.image1copy)
        Capturing = True
        ObjAvailable = l_obj

        counter = 0
        obj_counter = {
            PGIE_CLASS_ID_VEHICLE: 0,
            PGIE_CLASS_ID_PERSON: 0,
            PGIE_CLASS_ID_BICYCLE: 0,
            PGIE_CLASS_ID_ROADSIGN: 0
        }

        while l_obj is not None:
            try:
                obj_meta = pyds.NvDsObjectMeta.cast(l_obj.data)
                rect_params = obj_meta.rect_params
                top = int(rect_params.top)
                left = int(rect_params.left)
                width = int(rect_params.width)
                height = int(rect_params.height)
                confidence = obj_meta.confidence
                obj_counter[obj_meta.class_id] += 1
            except StopIteration:
                break
            try:
                l_obj = l_obj.next
            except StopIteration:
                break
        image1copy = cv2.rectangle(image1copy, (left, top), (left+width, top+height), (25,0,0), 2)
        cv2.imshow('test', image1copy)
       
        try:
            l_frame = l_frame.next
        except StopIteration:
            break
    return Gst.PadProbeReturn.OK

def refreshApp():
    global frameSync, image1copy

    if frameSync:
        SyncImRect = frameSync
        color_image = cv2.resize(SyncImRect, (round(480 * WScale), round(320 * HScale)))
    else:
        color_image = image1copy
    
        
    cv2.imshow('test', image1copy)
    cv2.waitKey(30)
    # photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(np.uint8(color_image)).convert('RGB'))
    # canvas1.create_image(round(1180 * WScale), round(100 * HScale), image=photo, anchor=tkinter.NW,
    #                         tags="ImgIdent")
    # # photo = PIL.ImageTk.PhotoImage(image=PIL.Image.fromarray(np.uint8(image1copy)).convert('RGB'))
    # # canvas1.create_image(round(1280 * WScale), round(100 * HScale), image=photo, anchor=tkinter.NW,
    # #                     tags="ImgIdent")
    # canvas1.delete('all')
    # window.update()


def cb_newpad(decodebin, decoder_src_pad, data):
    print("In cb_newpad\n")
    caps = decoder_src_pad.get_current_caps()
    gststruct = caps.get_structure(0)
    gstname = gststruct.get_name()
    source_bin = data
    features = caps.get_features(0)
    print("gstname=", gstname)
    if (gstname.find("video") != -1):
        print("features=", features)
        if features.contains("memory:NVMM"):
            bin_ghost_pad = source_bin.get_static_pad("src")
            if not bin_ghost_pad.set_target(decoder_src_pad):
                sys.stderr.write("Failed to link decoder src pad to source bin ghost pad\n")
        else:
            sys.stderr.write(" Error: Decodebin did not pick nvidia decoder plugin.\n")


def decodebin_child_added(child_proxy, Object, name, user_data):
    print("Decodebin child added:", name, "\n")
    if (name.find("decodebin") != -1):
        Object.connect("child-added", decodebin_child_added, user_data)
    if (is_aarch64() and name.find("nvv4l2decoder") != -1):
        print("Seting bufapi_version\n")
        Object.set_property("bufapi-version", True)


def create_source_bin(index, uri):
    print("Creating source bin")
    bin_name = "source-bin-%02d" % index
    print(bin_name)
    nbin = Gst.Bin.new(bin_name)
    if not nbin:
        sys.stderr.write(" Unable to create source bin \n")
    uri_decode_bin = Gst.ElementFactory.make("uridecodebin", "uri-decode-bin")
    if not uri_decode_bin:
        sys.stderr.write(" Unable to create uri decode bin \n")
    uri_decode_bin.set_property("uri", uri)
    uri_decode_bin.connect("pad-added", cb_newpad, nbin)
    uri_decode_bin.connect("child-added", decodebin_child_added, nbin)
    Gst.Bin.add(nbin, uri_decode_bin)
    bin_pad = nbin.add_pad(Gst.GhostPad.new_no_target("src", Gst.PadDirection.SRC))
    if not bin_pad:
        sys.stderr.write(" Failed to add ghost pad in source bin \n")
        return None
    return nbin


def main():
    number_sources = 1
    GObject.threads_init()
    Gst.init(None)
    pipeline = Gst.Pipeline()
    is_live = False
    uri_name = "rtsp://192.168.1.10:554/user=admin_password=tlJwpbo6_channel=1_stream=0.sdp"
    ds_pgie_config = '/home/proxeye/dev/proxeye/proxeye/resources/ds_pgie_config.txt'
    
    streammux = Gst.ElementFactory.make("nvstreammux", "Stream-muxer")
    pipeline.add(streammux)
    
    source_bin = create_source_bin(1, uri_name)
    pipeline.add(source_bin)
    sinkpad = streammux.get_request_pad("sink_1")
    srcpad = source_bin.get_static_pad("src")
    srcpad.link(sinkpad)
    
    pgie = Gst.ElementFactory.make("nvinfer", "primary-inference")
    nvvidconv1 = Gst.ElementFactory.make("nvvideoconvert", "convertor1")
    caps1 = Gst.Caps.from_string("video/x-raw(memory:NVMM), format=RGBA")
    filter1 = Gst.ElementFactory.make("capsfilter", "filter1")
    filter1.set_property("caps", caps1)
    tiler = Gst.ElementFactory.make("nvmultistreamtiler", "nvtiler")
    nvvidconv = Gst.ElementFactory.make("nvvideoconvert", "convertor")
    nvosd = Gst.ElementFactory.make("nvdsosd", "onscreendisplay")


    if (is_aarch64()):
        transform = Gst.ElementFactory.make("queue", "queue")

    sink = Gst.ElementFactory.make("fakesink", "fakesink")
    if is_live:
        streammux.set_property('live-source', 1)
    streammux.set_property('width', 640)
    streammux.set_property('height', 480)
    streammux.set_property('batch-size', 1)
    streammux.set_property('batched-push-timeout', 4000000)
    pgie.set_property('config-file-path', ds_pgie_config)
    sink.set_property('sync', False)
    pgie_batch_size = pgie.get_property("batch-size")
 
    tiler_rows = 1
    tiler_columns = 1
    tiler.set_property("rows", tiler_rows)
    tiler.set_property("columns", tiler_columns)
    tiler.set_property("width", 640)
    tiler.set_property("height", 480)
    print("Adding elements to Pipeline \n")
    pipeline.add(pgie)
    pipeline.add(tiler)
    pipeline.add(nvvidconv)
    pipeline.add(filter1)
    pipeline.add(nvvidconv1)
    pipeline.add(nvosd)
    if is_aarch64():
        pipeline.add(transform)
    pipeline.add(sink)
    print("Linking elements in the Pipeline \n")
    streammux.link(pgie)
    pgie.link(nvvidconv1)
    nvvidconv1.link(filter1)
    filter1.link(tiler)
    tiler.link(nvvidconv)
    nvvidconv.link(nvosd)
    if is_aarch64():
        nvosd.link(transform)
        transform.link(sink)
    else:
        nvosd.link(sink)
    GObject.idle_add(refreshApp)
    loop = GObject.MainLoop()
    bus = pipeline.get_bus()
    bus.add_signal_watch()
    bus.connect("message", bus_call, loop)
    tiler_src_pad = tiler.get_static_pad("src")
    if not tiler_src_pad:
        sys.stderr.write(" Unable to get src pad \n")
    else:
        tiler_src_pad.add_probe(Gst.PadProbeType.BUFFER, tiler_src_pad_buffer_probe, 0)
    print("Now playing...")
    print("Starting pipeline \n")
    pipeline.set_state(Gst.State.PLAYING)
    try:
        loop.run()
    except:
        pass
    print("Exiting app\n")
    pipeline.set_state(Gst.State.NULL)


sys.exit(main())