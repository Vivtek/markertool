# 2017-03-27 - The markertool is given an image directory and a database and allows the user to page back and forth in the images making selections to be used
#              e.g. as Haar cascade training data. A later step then extracts the segments and preprocesses them as needed for training.
#              The UI is based on wxWidgets.
#              Note that the name of the database and the name of the image directory are hardcoded in this file.
import wx
import base64
import StringIO
import socket
import threading
import sys
import os
from wxBufferedBitmap import *
from wxZoomingPILWindow import *

from PIL import Image
from PIL import ImageFont
from PIL import ImageDraw
#font = ImageFont.truetype("/usr/share/fonts/truetype/freefont/FreeMono.ttf", 8)

import sqlite3
conn = sqlite3.connect('markertool.sqld')
dbh = conn.cursor()

dbh.execute("create table if not exists targets (file text, x1 integer, y1 integer, x2 integer, y2 integer)")

iset = "2016-12-05 adjuntas"
files = sorted([f for f in os.listdir(iset) if f.endswith(".jpg")])
target_files = {}
for file in files:
   target_files[file] = 0
for file in dbh.execute("select distinct file from targets order by file"):
   target_files[file[0]] = 1


sizex = 320
sizey = 240




#---------------------------------------------------------------------------
class ImageFrame(wx.Frame):
    def __init__(self, parent, ID):
        wx.Frame.__init__(self, parent, ID, "Image marker")

        font = wx.Font(8, wx.MODERN, wx.NORMAL, wx.NORMAL, faceName="Lucida Console")
        h_sizer = wx.BoxSizer( wx.HORIZONTAL )

        self.image = BufferedBitmapWindow(self, size=wx.Size(sizex * 4, sizey * 4))
        self.bitmap = wx.Bitmap(sizex * 4, sizey * 4)
        h_sizer.Add (self.image, 0, wx.ALIGN_CENTER)

        self.refresh_bitmap = False

        self.box = False
        self.box_start = (0,0)
        self.box_end   = (0.0)
        
        self.current_image = None
        
        #self.zoom_image = BitmapWindow(self, size=wx.Size(20, 20))
        #self.zoom_bitmap = wx.Bitmap(20, 20)
        #h_sizer.Add (self.zoom_image, 0, wx.ALIGN_CENTER)
        
        self.SetSizer(h_sizer)
        h_sizer.SetSizeHints(self)
        h_sizer.Fit(self)
        
        self.Bind(wx.EVT_KEY_DOWN, self.onKeyPress)
        self.Bind(wx.EVT_CLOSE,    self.OnCloseWindow)

        self.image.Bind(wx.EVT_KEY_DOWN,  self.onKeyPress)
        self.image.Bind(wx.EVT_LEFT_DOWN, self.onMouse)
        self.image.Bind(wx.EVT_LEFT_UP,   self.onMouse)
        self.image.Bind(wx.EVT_MOTION,    self.onMouse)
        
        self.image_counter = 0
        self.GetImage(0)
        
        self.zoom_mode = False
        self.zoom_frame = None

 
 
    def onKeyPress(self, event):
        keycode = event.GetKeyCode()
        #print keycode

        if keycode == 314:
            self.OnArrowLeft(event.ShiftDown())
        if keycode == 315:
            self.OnArrowUp(event.ShiftDown())
        if keycode == 316:
            self.OnArrowRight(event.ShiftDown())
        if keycode == 317:
            self.OnArrowDown(event.ShiftDown())
        if keycode == 366:
            self.OnPageUp(event.ShiftDown())
        if keycode == 367:
            self.OnPageDown(event.ShiftDown())
        if keycode == 343:
            self.Close()
        if keycode == 127:
            self.DeleteCurrent()
        if keycode == 13:
            if self.zoom_mode:
               self.ZoomModeWrite()
            else:
               self.ZoomModeStart()
        if keycode == 27:
            if self.zoom_mode:
               self.ZoomModeCancel()
        #event.Skip()
        
    def onMouse(self, event):
        if event.ButtonDown():
            self.BoxStart(event.GetPosition())
        if event.ButtonUp():
            self.BoxDone(event.GetPosition())
        if event.Dragging():
            self.BoxDrag(event.GetPosition())
        event.Skip()
        
    def OnPageDown(self, shift):
        if self.image_pointer < len(files)-1:
           if not shift:
              self.image_pointer += 1
           else:
              cursor = self.image_pointer + 1
              while cursor < len(files) and not target_files[files[cursor]]:
                 cursor += 1
              if cursor < len(files):
                 self.image_pointer = cursor
           self.GetImage(self.image_pointer)
    
    def OnPageUp(self, shift):
        if self.image_pointer > 0:
           if not shift:
              self.image_pointer -= 1
           else:
              cursor = self.image_pointer - 1
              while cursor >= 0 and not target_files[files[cursor]]:
                 cursor -= 1
              if cursor >= 0:
                 self.image_pointer = cursor
           self.GetImage(self.image_pointer)
        
    def OnArrowLeft(self, shift):
        if self.zoom_mode:
           if shift:
              newval = self.box_true_start[0] + 1
              if newval >= self.box_true_end[0]:
                 newval = self.box_true_end[0] - 1
           else:
              newval = self.box_true_start[0] - 1
              if newval < 0:
                 newval = 0
           self.box_true_start = (newval, self.box_true_start[1])
           self.Redraw()
           self.SetCrop()
        elif len(self.targets):
           self.target_cursor -= 1
           if self.target_cursor < 0:
              self.target_cursor = len(self.targets) - 1
           self.Redraw()

    def OnArrowUp(self, shift):
        if self.zoom_mode:
           if shift:
              newval = self.box_true_start[1] + 1
              if newval >= self.box_true_end[1]:
                 newval = self.box_true_end[1] - 1
           else:
              newval = self.box_true_start[1] - 1
              if newval < 0:
                 newval = 0
           self.box_true_start = (self.box_true_start[0], newval)
           self.Redraw()
           self.SetCrop()           
        elif len(self.targets):
           self.target_cursor -= 1
           if self.target_cursor < 0:
              self.target_cursor = len(self.targets) - 1
           self.Redraw()

    def OnArrowRight(self, shift):
        if self.zoom_mode:
           if shift:
              newval = self.box_true_end[0] - 1
              if newval <= self.box_true_start[0]:
                 newval = self.box_true_start[0] + 1
           else:
              newval = self.box_true_end[0] + 1
              if newval > self.current_base_image_size[0]:
                 newval = self.current_base_image_size[0]
           self.box_true_end = (newval, self.box_true_end[1])
           self.Redraw()
           self.SetCrop()           
        elif len(self.targets):
           self.target_cursor += 1
           if self.target_cursor >= len(self.targets):
              self.target_cursor = 0
           self.Redraw()

    def OnArrowDown(self, shift):
        if self.zoom_mode:
           if shift:
              newval = self.box_true_end[1] - 1
              if newval <= self.box_true_start[1]:
                 newval = self.box_true_start[1] + 1
           else:
              newval = self.box_true_end[1] + 1
              if newval > self.current_base_image_size[1]:
                 newval = self.current_base_image_size[1]
           self.box_true_end = (self.box_true_end[0], newval)
           self.Redraw()
           self.SetCrop()           
        elif len(self.targets):
           self.target_cursor += 1
           if self.target_cursor >= len(self.targets):
              self.target_cursor = 0
           self.Redraw()


    def OnCloseWindow(self, event):
        """We're closing, so clean up."""
        if self.zoom_frame:
           self.zoom_frame.Destroy()
        self.Destroy()
        
    def OnCloseZoomWindow(self, event):
        self.zoom_frame = None
        pass
        
        
    def GetImage(self, which):
        if which < 0:
           which = 0
        if which > len(files) - 1:
           which = len(files) - 1;
        self.image_pointer = which
           
        im = Image.open("{}/{}".format(iset, files[which])).convert("RGB")
        self.current_base_image = im
        self.current_base_image_size = im.size
        self.current_image = im.resize((sizex * 4, sizey * 4), Image.NEAREST)
        self.SetTitle("Image marker - {}".format(files[which]))
        
        self.ReloadTargets()
        self.target_cursor = -1

        self.box = False
        self.Redraw()
        
    def ReloadTargets(self):
        self.targets = []
        for box in dbh.execute('select x1, y1, x2, y2 from targets where file=? order by x1, y1', (files[self.image_pointer],)):
           self.targets.append(box)
        
    def BoxStart(self, pos):
        self.ZoomModeEnd()
        self.box = True
        self.target_cursor = -1
        self.box_start = pos
        self.box_end   = pos
        self.box_true_start = (pos[0] / 4, pos[1] / 4)
        
    def BoxDrag(self, pos):
        self.box_end = pos
        self.box_true_end = (pos[0] / 4, pos[1] / 4)
        self.Redraw()
        
    def Redraw(self):
        im = self.current_image.copy()
        draw = ImageDraw.Draw(im)

        count = -1
        for box in self.targets:
           count += 1
           if count == self.target_cursor:
              if self.zoom_mode:
                 draw.rectangle(((self.box_true_start[0] * 4, self.box_true_start[1] * 4),
                                 (self.box_true_end[0] * 4,   self.box_true_end[1] * 4  )),
                                outline=(0,0,255))
              else:
                 draw.rectangle((box[0]*4, box[1]*4, box[2]*4, box[3]*4), outline=(0,0,255))
           else:
              draw.rectangle((box[0]*4, box[1]*4, box[2]*4, box[3]*4), outline=(0,255,255))
        
        if self.box:
           draw.rectangle(((self.box_true_start[0] * 4, self.box_true_start[1] * 4),
                           (self.box_true_end[0] * 4,   self.box_true_end[1] * 4  )),
                          outline=(0,0,255))
        self.DisplayImage(im)

    def DisplayImage(self, im):
        self.bitmap = wx.Bitmap.FromBuffer (im.size[0], im.size[1], im.tobytes());
        self.image.SetBitmap(self.bitmap)
        
        
    #def DrawBox(self, color):
    #    im = self.current_image.copy()
    #    draw = ImageDraw.Draw(im)
    #    self.box = True
    ##    draw.rectangle(((self.box_true_start[0] * 4, self.box_true_start[1] * 4),
    #                    (self.box_true_end[0] * 4,   self.box_true_end[1] * 4  )),
    #                   outline=(0,0,255))
    #    self.DisplayImage(im)
        
    def BoxDone(self, pos):
        self.BoxDrag(pos)
        if (self.box_start[0] != self.box_end[0] and self.box_end[1] != self.box_start[1]):
           self.ZoomModeStart()
        
    def ZoomModeStart(self):
        if self.box:
           if self.box_true_start[0] > self.box_true_end[0]:
              swap = self.box_true_start[0]
              self.box_true_start = (self.box_true_end[0], self.box_true_start[1])
              self.box_true_end   = (swap,                 self.box_true_end[1])
           if self.box_true_start[1] > self.box_true_end[1]:
              swap = self.box_true_start[1]
              self.box_true_start = (self.box_true_start[0], self.box_true_end[1])
              self.box_true_end   = (self.box_true_end[0],   swap)
           self.zoom_mode = True
           self.SetCrop()
        elif self.target_cursor > -1:
           self.box_true_start = (self.targets[self.target_cursor][0], self.targets[self.target_cursor][1])
           self.box_true_end =   (self.targets[self.target_cursor][2], self.targets[self.target_cursor][3])
           self.zoom_mode = True
           self.SetCrop()
        
    def SetCrop(self):
        self.cropped_image = self.current_base_image.crop((self.box_true_start[0], self.box_true_start[1],
                                                           self.box_true_end[0],   self.box_true_end[1]   ))
        
        if not self.zoom_frame:
           self.zoom_frame = ZoomingPILFrame(image = self.cropped_image, zoom=8)
           self.zoom_frame.Window.Bind(wx.EVT_KEY_DOWN,  self.onKeyPress)
           self.zoom_frame.Window.Bind(wx.EVT_CLOSE,     self.OnCloseZoomWindow)
        else:
           self.zoom_frame.SetImage(self.cropped_image)

        self.zoom_frame.Show(True)
        
    def ZoomModeWrite(self):
        if self.box:
           self.targets.append((self.box_true_start[0], self.box_true_start[1], self.box_true_end[0], self.box_true_end[1]))
           dbh.execute("insert into targets (file, x1, y1, x2, y2) values (?, ?, ?, ?, ?)",
                       (files[self.image_pointer],
                       self.box_true_start[0],
                       self.box_true_start[1],
                       self.box_true_end[0],
                       self.box_true_end[1]))
           conn.commit()
           target_files[files[self.image_pointer]] = 1
           self.box = False
        elif self.target_cursor > -1:
           dbh.execute("delete from targets where file=? and x1=? and y1=?", (files[self.image_pointer], self.targets[self.target_cursor][0], self.targets[self.target_cursor][1]))
           self.targets[self.target_cursor] = (self.box_true_start[0], self.box_true_start[1], self.box_true_end[0], self.box_true_end[1])
           dbh.execute("insert into targets (file, x1, y1, x2, y2) values (?, ?, ?, ?, ?)",
                       (files[self.image_pointer],
                       self.box_true_start[0],
                       self.box_true_start[1],
                       self.box_true_end[0],
                       self.box_true_end[1]))
           conn.commit()
        self.Redraw()
        self.ZoomModeEnd();
        
    def ZoomModeCancel(self):
        self.box = False
        if self.target_cursor > -1:
           self.box_true_start = (self.targets[self.target_cursor][0], self.targets[self.target_cursor][1])
           self.box_true_end =   (self.targets[self.target_cursor][2], self.targets[self.target_cursor][3])

        self.Redraw()
        self.ZoomModeEnd();
        
    def ZoomModeEnd(self):
        self.zoom_mode = False
        if self.zoom_frame:
           self.zoom_frame.Show(False)
           
    def DeleteCurrent(self):
        if self.box:
           return self.ZoomModeCancel()
        if self.target_cursor > -1:
           dlg = wx.MessageDialog(self, "Delete current target?", "Confirm deletion", wx.YES_NO | wx.ICON_QUESTION)
           really = dlg.ShowModal() == wx.ID_YES
           dlg.Destroy()
           if really:
              dbh.execute("delete from targets where file=? and x1=? and y1=?",
                          (files[self.image_pointer], self.targets[self.target_cursor][0], self.targets[self.target_cursor][1]))
              conn.commit()
              self.ReloadTargets()
              while self.target_cursor >= len(self.targets):
                 self.target_cursor -= 1
              self.Redraw()

#---------------------------------------------------------------------------

#if __name__ == '__main__':
import sys
app = wx.App()
frame = ImageFrame(None, -1)
frame.Show(True)
app.MainLoop()
